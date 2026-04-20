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
        }

    def chat(self, message: str, session_id: str | None = None, top_k: int | None = None):
        return {
            "session_id": session_id or "generated-session",
            "answer": f"echo: {message}",
            "sources": [
                {
                    "source": "faq.txt",
                    "file_name": "faq.txt",
                    "content": "Stage 1 only reads local files from the data directory.",
                    "score": 0.12,
                }
            ],
        }


def test_health_endpoint_returns_index_stats():
    app = create_app(FakeRagService(), initialize_service=False)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["document_count"] == 3


def test_chat_endpoint_generates_session_id_when_missing():
    app = create_app(FakeRagService(), initialize_service=False)

    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "How do I start?"})

    body = response.json()
    assert response.status_code == 200
    assert body["session_id"] == "generated-session"
    assert body["sources"][0]["file_name"] == "faq.txt"


def test_chat_endpoint_preserves_supplied_session_id():
    app = create_app(FakeRagService(), initialize_service=False)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "Follow up", "session_id": "session-42", "top_k": 2},
        )

    assert response.status_code == 200
    assert response.json()["session_id"] == "session-42"


def test_chat_endpoint_maps_upstream_rate_limit_to_429():
    class RateLimitedService:
        def health(self):
            return {
                "status": "ok",
                "ready": True,
                "document_count": 1,
                "chunk_count": 1,
                "fingerprint": "abc123",
                "startup_error": None,
            }

        def chat(self, message: str, session_id: str | None = None, top_k: int | None = None):
            request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            response = httpx.Response(429, request=request)
            raise RateLimitError(
                "Provider returned error",
                response=response,
                body={
                    "error": {
                        "message": "free model is temporarily rate-limited upstream",
                    }
                },
            )

    app = create_app(RateLimitedService(), initialize_service=False)

    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 429
    assert "rate limited" in response.json()["detail"]
