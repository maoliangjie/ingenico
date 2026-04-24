from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import Settings
from app.schemas import SourceSnippet
from app.services.document_loader import (
    SourceDirectory,
    compute_sources_fingerprint,
    load_documents_from_sources,
    load_manifest,
    write_manifest,
)
from app.services.redis_store import MemoryMessage, RedisChatStore
from app.services.upload_store import UploadRecord, UploadStore


LOGGER = logging.getLogger(__name__)
THINK_BLOCK_PATTERN = re.compile(r"<think>(.*?)</think>", re.IGNORECASE | re.DOTALL)


class RagService:
    def __init__(
        self,
        settings: Settings,
        redis_store: RedisChatStore | None = None,
        upload_store: UploadStore | None = None,
    ) -> None:
        self.settings = settings
        self.redis_store = redis_store or RedisChatStore.from_url(
            settings.redis_url,
            settings.redis_prefix,
            settings.redis_cache_ttl_seconds,
        )
        self.upload_store = upload_store or UploadStore(
            settings.uploads_dir,
            settings.upload_manifest_path,
        )
        self.embeddings: HuggingFaceEmbeddings | OpenAIEmbeddings | None = None
        self.llm: ChatOpenAI | None = None
        self.vector_store: Chroma | None = None
        self.index_stats: dict[str, Any] = {
            "ready": False,
            "document_count": 0,
            "chunk_count": 0,
            "fingerprint": None,
            "redis_ready": False,
            "upload_count": 0,
        }

    def initialize(self) -> None:
        self.settings.storage_dir.mkdir(parents=True, exist_ok=True)
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.uploads_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_chat_credentials()

        self.index_stats["redis_ready"] = self.redis_store.ping()
        self.embeddings = self._build_embeddings()
        self.llm = ChatOpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_api_base,
            model=self.settings.chat_model,
            temperature=0,
        )
        self.refresh_index()

    def refresh_index(self) -> None:
        if not self.embeddings:
            raise RuntimeError("Embeddings are not initialized.")

        sources = self._source_directories()
        current_manifest = compute_sources_fingerprint(sources)
        previous_manifest = load_manifest(self.settings.manifest_path)
        embedding_signature = self._embedding_signature()
        should_rebuild = (
            previous_manifest is None
            or previous_manifest.get("fingerprint") != current_manifest["fingerprint"]
            or previous_manifest.get("embedding_signature") != embedding_signature
            or not self.settings.vector_dir.exists()
        )

        if should_rebuild:
            documents = load_documents_from_sources(sources)
            if not documents:
                raise RuntimeError(
                    "No supported knowledge files were found under the static or uploaded data directories."
                )
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
            )
            split_documents = splitter.split_documents(documents)
            self._reset_collection()
            self.vector_store = Chroma.from_documents(
                documents=split_documents,
                embedding=self.embeddings,
                persist_directory=str(self.settings.vector_dir),
                collection_name=self.settings.collection_name,
            )
            manifest = {
                **current_manifest,
                "chunk_count": len(split_documents),
                "embedding_signature": embedding_signature,
            }
            write_manifest(self.settings.manifest_path, manifest)
            self.index_stats = {
                "ready": True,
                "document_count": int(current_manifest["document_count"]),
                "chunk_count": len(split_documents),
                "fingerprint": str(current_manifest["fingerprint"]),
                "redis_ready": self.redis_store.ping(),
                "upload_count": len(self.upload_store.list_uploads()),
            }
            return

        self.vector_store = Chroma(
            collection_name=self.settings.collection_name,
            persist_directory=str(self.settings.vector_dir),
            embedding_function=self.embeddings,
        )
        self.index_stats = {
            "ready": True,
            "document_count": int(previous_manifest.get("document_count", 0)),
            "chunk_count": int(previous_manifest.get("chunk_count", 0)),
            "fingerprint": previous_manifest.get("fingerprint"),
            "redis_ready": self.redis_store.ping(),
            "upload_count": len(self.upload_store.list_uploads()),
        }

    def chat(
        self,
        message: str,
        session_id: str | None = None,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        if not self.vector_store or not self.llm:
            raise RuntimeError("RAG service is not initialized.")

        active_session_id = session_id or str(uuid4())
        cleaned_message = message.strip()
        effective_top_k = top_k or self.settings.default_top_k
        history = self.redis_store.load_messages(active_session_id, self.settings.history_window)
        retrieved = self.vector_store.similarity_search_with_score(cleaned_message, k=effective_top_k)
        sources = [self._build_source(document, score) for document, score in retrieved]
        cache_key = self.redis_store.build_cache_key(
            model=self.settings.chat_model,
            question=cleaned_message,
            history=history,
            sources=[source.model_dump() for source in sources],
            top_k=effective_top_k,
        )
        cached_answer = self.redis_store.get_cached_answer(cache_key)
        cache_hit = cached_answer is not None
        answer = cached_answer or self._strip_reasoning_blocks(
            self._generate_answer(cleaned_message, history, sources),
            active_session_id,
        )
        if not cache_hit:
            self.redis_store.set_cached_answer(cache_key, answer)

        self.redis_store.save_message(active_session_id, "user", cleaned_message)
        self.redis_store.save_message(active_session_id, "assistant", answer)

        return {
            "session_id": active_session_id,
            "answer": answer,
            "sources": [source.model_dump() for source in sources],
            "cache_hit": cache_hit,
        }

    def list_uploads(self) -> list[dict[str, Any]]:
        return [self._upload_record_payload(item) for item in self.upload_store.list_uploads()]

    def create_upload(self, file_name: str, content: bytes) -> dict[str, Any]:
        record = self.upload_store.create_upload(file_name, content)
        self.refresh_index()
        return self._upload_record_payload(record)

    def replace_upload(self, file_id: str, file_name: str, content: bytes) -> dict[str, Any]:
        record = self.upload_store.replace_upload(file_id, file_name, content)
        self.refresh_index()
        return self._upload_record_payload(record)

    def delete_upload(self, file_id: str) -> None:
        self.upload_store.delete_upload(file_id)
        self.refresh_index()

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.index_stats["ready"] and self.index_stats["redis_ready"] else "starting",
            **self.index_stats,
            "startup_error": None,
        }

    def _generate_answer(
        self,
        question: str,
        history: list[MemoryMessage],
        sources: list[SourceSnippet],
    ) -> str:
        if not sources:
            return "I do not have enough information in the current knowledge base to answer that."

        history_text = "\n".join(
            f"{item.role.title()}: {item.content}" for item in history
        ) or "No prior conversation."
        context_text = "\n\n".join(
            f"[{index}] {source.file_name}\n{source.content}"
            for index, source in enumerate(sources, start=1)
        )
        response = self.llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a retrieval-grounded assistant. Answer only with support from the provided "
                        "context. If the context is missing or insufficient, say you do not have enough "
                        "information in the current knowledge base."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Conversation history:\n{history_text}\n\n"
                        f"Retrieved context:\n{context_text}\n\n"
                        f"Question:\n{question}"
                    )
                ),
            ]
        )
        return str(response.content).strip()

    def _strip_reasoning_blocks(self, answer: str, session_id: str) -> str:
        reasoning_blocks = [
            match.strip()
            for match in THINK_BLOCK_PATTERN.findall(answer)
            if match.strip()
        ]
        for index, block in enumerate(reasoning_blocks, start=1):
            LOGGER.info(
                "Filtered reasoning block for session %s (block %s):\n%s",
                session_id,
                index,
                block,
            )

        cleaned_answer = THINK_BLOCK_PATTERN.sub("", answer)
        cleaned_answer = re.sub(r"\n{3,}", "\n\n", cleaned_answer).strip()
        return cleaned_answer or answer.strip()

    @staticmethod
    def _build_source(document: Any, score: float | None) -> SourceSnippet:
        return SourceSnippet(
            source=document.metadata.get("source", ""),
            file_name=document.metadata.get("file_name", ""),
            content=document.page_content[:400],
            score=score,
        )

    @staticmethod
    def _upload_record_payload(record: UploadRecord) -> dict[str, str]:
        return {
            "file_id": record.file_id,
            "file_name": record.file_name,
            "stored_name": record.stored_name,
            "status": record.status,
            "source_path": record.source_path,
            "updated_at": record.updated_at,
        }

    def _reset_collection(self) -> None:
        self.settings.vector_dir.mkdir(parents=True, exist_ok=True)
        if self.vector_store is not None:
            try:
                self.vector_store.delete_collection()
            except Exception as exc:  # pragma: no cover - defensive cleanup path
                LOGGER.warning("Unable to delete existing Chroma collection cleanly: %s", exc)
            finally:
                self.vector_store = None
            return

        if not self.settings.vector_dir.exists():
            return

        existing_store = Chroma(
            collection_name=self.settings.collection_name,
            persist_directory=str(self.settings.vector_dir),
            embedding_function=self.embeddings,
        )
        try:
            existing_store.delete_collection()
        except Exception as exc:  # pragma: no cover - best-effort cleanup on cold start
            LOGGER.warning("Unable to delete existing persisted Chroma collection cleanly: %s", exc)

    def _source_directories(self) -> list[SourceDirectory]:
        return [
            SourceDirectory(name="static", root=self.settings.data_dir, scope="static"),
            SourceDirectory(name="uploads", root=self.settings.uploads_dir, scope="upload"),
        ]

    def _build_embeddings(self) -> HuggingFaceEmbeddings | OpenAIEmbeddings:
        if self.settings.embedding_provider == "local":
            return HuggingFaceEmbeddings(
                model_name=self.settings.local_embedding_model,
                model_kwargs={"device": self.settings.local_embedding_device},
                encode_kwargs={"normalize_embeddings": True},
            )

        if self.settings.embedding_provider == "openai":
            return OpenAIEmbeddings(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_api_base,
                model=self.settings.openai_embedding_model,
            )

        raise RuntimeError("Unsupported EMBEDDING_PROVIDER. Use 'local' or 'openai'.")

    def _embedding_signature(self) -> dict[str, str]:
        if self.settings.embedding_provider == "local":
            return {
                "provider": "local",
                "model": self.settings.local_embedding_model,
                "device": self.settings.local_embedding_device,
            }

        return {
            "provider": "openai",
            "model": self.settings.openai_embedding_model,
            "base_url": self.settings.openai_api_base or "",
        }

    def _ensure_chat_credentials(self) -> None:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required to start the chat service.")
