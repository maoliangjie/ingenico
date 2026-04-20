from app.config import Settings
from app.services.rag_service import RagService


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
        vector_dir=tmp_path / "storage" / "chroma",
        memory_db_path=tmp_path / "storage" / "memory.sqlite3",
        manifest_path=tmp_path / "storage" / "index_manifest.json",
        collection_name="knowledge_base",
        default_top_k=4,
        history_window=6,
        chunk_size=900,
        chunk_overlap=180,
    )


def test_build_embeddings_uses_local_provider_by_default(tmp_path, monkeypatch):
    captured = {}

    class FakeHFEmbeddings:
        def __init__(self, model_name, model_kwargs, encode_kwargs):
            captured["model_name"] = model_name
            captured["model_kwargs"] = model_kwargs
            captured["encode_kwargs"] = encode_kwargs

    monkeypatch.setattr("app.services.rag_service.HuggingFaceEmbeddings", FakeHFEmbeddings)

    service = RagService(build_settings(tmp_path, "local"))
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

    service = RagService(build_settings(tmp_path, "openai"))
    embeddings = service._build_embeddings()

    assert isinstance(embeddings, FakeOpenAIEmbeddings)
    assert captured["api_key"] == "test-key"
    assert captured["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["model"] == "text-embedding-3-small"


def test_embedding_signature_tracks_local_model_settings(tmp_path):
    service = RagService(build_settings(tmp_path, "local"))

    assert service._embedding_signature() == {
        "provider": "local",
        "model": "BAAI/bge-small-zh-v1.5",
        "device": "cpu",
    }


def test_embedding_signature_tracks_openai_embedding_settings(tmp_path):
    service = RagService(build_settings(tmp_path, "openai"))

    assert service._embedding_signature() == {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "base_url": "https://openrouter.ai/api/v1",
    }
