import fakeredis

from app.config import Settings
from app.services.rag_service import RagService
from app.services.redis_store import RedisChatStore
from app.services.upload_store import UploadStore


def build_settings(tmp_path, embedding_provider: str) -> Settings:
    return Settings(
        openai_api_key="test-key",
        openai_api_base="https://openrouter.ai/api/v1",
        chat_model="google/gemma-4-26b-a4b-it:free",
        embedding_provider=embedding_provider,
        openai_embedding_model="text-embedding-3-small",
        local_embedding_model="BAAI/bge-small-zh-v1.5",
        local_embedding_device="cpu",
        data_dir=tmp_path / "data",
        storage_dir=tmp_path / "storage",
        uploads_dir=tmp_path / "storage" / "uploads",
        upload_manifest_path=tmp_path / "storage" / "uploads.json",
        vector_dir=tmp_path / "storage" / "chroma",
        manifest_path=tmp_path / "storage" / "index_manifest.json",
        redis_url="redis://unused:6379/0",
        redis_prefix="ingenico-test",
        redis_cache_ttl_seconds=120,
        collection_name="knowledge_base",
        default_top_k=4,
        history_window=6,
        chunk_size=900,
        chunk_overlap=180,
        frontend_dist_dir=tmp_path / "frontend" / "dist",
    )


def build_service(tmp_path, embedding_provider: str = "local") -> RagService:
    fake_client = fakeredis.FakeRedis(decode_responses=True)
    redis_store = RedisChatStore(fake_client, "ingenico-test", 120)
    upload_store = UploadStore(tmp_path / "storage" / "uploads", tmp_path / "storage" / "uploads.json")
    return RagService(
        build_settings(tmp_path, embedding_provider),
        redis_store=redis_store,
        upload_store=upload_store,
    )


def test_build_embeddings_uses_local_provider_by_default(tmp_path, monkeypatch):
    captured = {}

    class FakeHFEmbeddings:
        def __init__(self, model_name, model_kwargs, encode_kwargs):
            captured["model_name"] = model_name
            captured["model_kwargs"] = model_kwargs
            captured["encode_kwargs"] = encode_kwargs

    monkeypatch.setattr("app.services.rag_service.HuggingFaceEmbeddings", FakeHFEmbeddings)

    service = build_service(tmp_path, "local")
    embeddings = service._build_embeddings()

    assert isinstance(embeddings, FakeHFEmbeddings)
    assert captured["model_name"] == "BAAI/bge-small-zh-v1.5"
    assert captured["model_kwargs"] == {"device": "cpu"}
    assert captured["encode_kwargs"] == {"normalize_embeddings": True}


def test_build_embeddings_uses_openai_provider_when_requested(tmp_path, monkeypatch):
    captured = {}

    class FakeOpenAIEmbeddings:
        def __init__(self, api_key, base_url, model):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            captured["model"] = model

    monkeypatch.setattr("app.services.rag_service.OpenAIEmbeddings", FakeOpenAIEmbeddings)

    service = build_service(tmp_path, "openai")
    embeddings = service._build_embeddings()

    assert isinstance(embeddings, FakeOpenAIEmbeddings)
    assert captured["api_key"] == "test-key"
    assert captured["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["model"] == "text-embedding-3-small"


def test_embedding_signature_tracks_local_model_settings(tmp_path):
    service = build_service(tmp_path, "local")

    assert service._embedding_signature() == {
        "provider": "local",
        "model": "BAAI/bge-small-zh-v1.5",
        "device": "cpu",
    }


def test_embedding_signature_tracks_openai_embedding_settings(tmp_path):
    service = build_service(tmp_path, "openai")

    assert service._embedding_signature() == {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "base_url": "https://openrouter.ai/api/v1",
    }


def test_strip_reasoning_blocks_removes_think_and_logs(tmp_path, caplog):
    service = build_service(tmp_path, "local")
    answer = (
        "<think>reasoning line 1\nreasoning line 2</think>\n\n"
        "Final answer to the user."
    )

    with caplog.at_level("INFO"):
        cleaned = service._strip_reasoning_blocks(answer, "session-123")

    assert cleaned == "Final answer to the user."
    assert "Filtered reasoning block for session session-123" in caplog.text
    assert "reasoning line 1" in caplog.text


def test_chat_uses_redis_cache_for_repeat_calls(tmp_path, monkeypatch):
    service = build_service(tmp_path, "local")
    service.vector_store = type(
        "FakeVectorStore",
        (),
        {
            "similarity_search_with_score": staticmethod(
                lambda message, k: [
                    (
                        type(
                            "FakeDocument",
                            (),
                            {
                                "metadata": {"source": "faq.txt", "file_name": "faq.txt"},
                                "page_content": "Answer from source",
                            },
                        )(),
                        0.2,
                    )
                ]
            )
        },
    )()
    service.llm = object()
    calls = {"count": 0}
    monkeypatch.setattr(service.redis_store, "load_messages", lambda session_id, limit: [])
    monkeypatch.setattr(service.redis_store, "save_message", lambda session_id, role, content: None)

    def fake_generate_answer(question, history, sources):
        calls["count"] += 1
        return "cached answer"

    monkeypatch.setattr(service, "_generate_answer", fake_generate_answer)

    first = service.chat("hello")
    second = service.chat("hello", session_id=first["session_id"])

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert calls["count"] == 1


def test_upload_operations_refresh_index(tmp_path, monkeypatch):
    service = build_service(tmp_path, "local")
    service.embeddings = object()
    refresh_calls = {"count": 0}

    def fake_refresh_index():
        refresh_calls["count"] += 1

    monkeypatch.setattr(service, "refresh_index", fake_refresh_index)

    created = service.create_upload("note.txt", b"hello")
    replaced = service.replace_upload(created["file_id"], "note.txt", b"world")
    service.delete_upload(created["file_id"])

    assert created["file_name"] == "note.txt"
    assert replaced["file_name"] == "note.txt"
    assert refresh_calls["count"] == 3
