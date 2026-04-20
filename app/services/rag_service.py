from __future__ import annotations

import shutil
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
    compute_data_fingerprint,
    load_documents,
    load_manifest,
    write_manifest,
)
from app.services.memory_store import SQLiteMemoryStore


class RagService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.memory_store = SQLiteMemoryStore(settings.memory_db_path)
        self.embeddings: HuggingFaceEmbeddings | OpenAIEmbeddings | None = None
        self.llm: ChatOpenAI | None = None
        self.vector_store: Chroma | None = None
        self.index_stats: dict[str, Any] = {
            "ready": False,
            "document_count": 0,
            "chunk_count": 0,
            "fingerprint": None,
        }

    def initialize(self) -> None:
        self.settings.storage_dir.mkdir(parents=True, exist_ok=True)
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_chat_credentials()

        self.embeddings = self._build_embeddings()
        self.llm = ChatOpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_api_base,
            model=self.settings.chat_model,
            temperature=0,
        )

        current_manifest = compute_data_fingerprint(self.settings.data_dir)
        previous_manifest = load_manifest(self.settings.manifest_path)
        embedding_signature = self._embedding_signature()
        should_rebuild = (
            previous_manifest is None
            or previous_manifest.get("fingerprint") != current_manifest["fingerprint"]
            or previous_manifest.get("embedding_signature") != embedding_signature
            or not self.settings.vector_dir.exists()
        )

        if should_rebuild:
            documents = load_documents(self.settings.data_dir)
            if not documents:
                raise RuntimeError(
                    "No supported knowledge files were found under the data directory."
                )
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
            )
            split_documents = splitter.split_documents(documents)
            self._reset_vector_dir(self.settings.vector_dir)
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
        }

    def chat(self, message: str, session_id: str | None = None, top_k: int | None = None) -> dict[str, Any]:
        if not self.vector_store or not self.llm:
            raise RuntimeError("RAG service is not initialized.")

        active_session_id = session_id or str(uuid4())
        message = message.strip()
        effective_top_k = top_k or self.settings.default_top_k
        history = self.memory_store.load_messages(active_session_id, self.settings.history_window)
        retrieved = self.vector_store.similarity_search_with_score(message, k=effective_top_k)
        sources = [self._build_source(document, score) for document, score in retrieved]

        answer = self._generate_answer(message, history, sources)

        self.memory_store.save_message(active_session_id, "user", message)
        self.memory_store.save_message(active_session_id, "assistant", answer)

        return {
            "session_id": active_session_id,
            "answer": answer,
            "sources": [source.model_dump() for source in sources],
        }

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.index_stats["ready"] else "starting",
            **self.index_stats,
            "startup_error": None,
        }

    def _generate_answer(self, question: str, history: list[Any], sources: list[SourceSnippet]) -> str:
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

    @staticmethod
    def _build_source(document: Any, score: float | None) -> SourceSnippet:
        return SourceSnippet(
            source=document.metadata.get("source", ""),
            file_name=document.metadata.get("file_name", ""),
            content=document.page_content[:400],
            score=score,
        )

    @staticmethod
    def _reset_vector_dir(vector_dir: Path) -> None:
        if vector_dir.exists():
            shutil.rmtree(vector_dir)
        vector_dir.mkdir(parents=True, exist_ok=True)

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

        raise RuntimeError(
            "Unsupported EMBEDDING_PROVIDER. Use 'local' or 'openai'."
        )

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
