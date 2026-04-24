from fastapi.testclient import TestClient
import httpx
from openai import RateLimitError

from app.main import create_app


class FakeRagService:
    def health(self):
        return {
            "status": "ok",
            "ready": True,
            "document_count": 3,
            "chunk_count": 5,
            "fingerprint": "abc123",
            "redis_ready": True,
            "upload_count": 1,
        }

    def chat(self, message: str, session_id: str | None = None, top_k: int | None = None):
        return {
            "session_id": session_id or "generated-session",
            "answer": f"echo: {message}",
            "cache_hit": False,
            "sources": [
                {
                    "source": "faq.txt",
                    "file_name": "faq.txt",
                    "content": "Stage 2 supports uploads and SSE.",
                    "score": 0.12,
                }
            ],
        }

    def list_uploads(self):
        return [
            {
                "file_id": "file-1",
                "file_name": "note.txt",
                "stored_name": "uuid-note.txt",
                "status": "ready",
                "source_path": "/tmp/uploads/uuid-note.txt",
                "updated_at": "2026-04-21T00:00:00+00:00",
            }
        ]

    def create_upload(self, file_name: str, content: bytes):
        return {
            "file_id": "file-1",
            "file_name": file_name,
            "stored_name": "uuid-note.txt",
            "status": "ready",
            "source_path": "/tmp/uploads/uuid-note.txt",
            "updated_at": "2026-04-21T00:00:00+00:00",
        }

    def replace_upload(self, file_id: str, file_name: str, content: bytes):
        return {
            "file_id": file_id,
            "file_name": file_name,
            "stored_name": "uuid-note.txt",
            "status": "ready",
            "source_path": "/tmp/uploads/uuid-note.txt",
            "updated_at": "2026-04-21T00:00:00+00:00",
        }

    def delete_upload(self, file_id: str):
        return None


def test_health_endpoint_returns_stage2_stats():
    app = create_app(FakeRagService(), initialize_service=False)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["redis_ready"] is True
    assert response.json()["upload_count"] == 1


def test_chat_endpoint_generates_session_id_when_missing():
    app = create_app(FakeRagService(), initialize_service=False)

    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "How do I start?"})

    body = response.json()
    assert response.status_code == 200
    assert body["session_id"] == "generated-session"
    assert body["sources"][0]["file_name"] == "faq.txt"


def test_stream_chat_endpoint_emits_sse_events():
    app = create_app(FakeRagService(), initialize_service=False)

    with TestClient(app) as client:
        response = client.post("/chat/stream", json={"message": "stream please"})

    assert response.status_code == 200
    assert "event: start" in response.text
    assert "event: token" in response.text
    assert "event: sources" in response.text
    assert "event: done" in response.text


def test_upload_endpoints_round_trip_records():
    app = create_app(FakeRagService(), initialize_service=False)

    with TestClient(app) as client:
        list_response = client.get("/uploads")
        create_response = client.post(
            "/upload",
            files={"file": ("note.txt", b"hello", "text/plain")},
        )
        replace_response = client.put(
            "/uploads/file-1",
            files={"file": ("note.txt", b"world", "text/plain")},
        )
        delete_response = client.delete("/uploads/file-1")

    assert list_response.status_code == 200
    assert list_response.json()["files"][0]["file_name"] == "note.txt"
    assert create_response.status_code == 200
    assert replace_response.status_code == 200
    assert delete_response.status_code == 204


def test_upload_endpoint_maps_pdf_validation_error_to_400():
    class InvalidPdfService(FakeRagService):
        def create_upload(self, file_name: str, content: bytes):
            raise ValueError("PDF 'broken.pdf' does not contain extractable text.")

    app = create_app(InvalidPdfService(), initialize_service=False)

    with TestClient(app) as client:
        response = client.post(
            "/upload",
            files={"file": ("broken.pdf", b"%PDF-1.4", "application/pdf")},
        )

    assert response.status_code == 400
    assert "extractable text" in response.json()["detail"]


def test_chat_endpoint_maps_upstream_rate_limit_to_429():
    class RateLimitedService(FakeRagService):
        def chat(self, message: str, session_id: str | None = None, top_k: int | None = None):
            request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            response = httpx.Response(429, request=request)
            raise RateLimitError(
                "Provider returned error",
                response=response,
                body={"error": {"message": "free model is temporarily rate-limited upstream"}},
            )

    app = create_app(RateLimitedService(), initialize_service=False)

    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 429
    assert "rate limited" in response.json()["detail"]
