from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import redis


@dataclass(slots=True)
class MemoryMessage:
    role: str
    content: str


class RedisChatStore:
    def __init__(
        self,
        redis_client: redis.Redis,
        prefix: str,
        cache_ttl_seconds: int,
    ) -> None:
        self.redis = redis_client
        self.prefix = prefix
        self.cache_ttl_seconds = cache_ttl_seconds

    @classmethod
    def from_url(cls, redis_url: str, prefix: str, cache_ttl_seconds: int) -> "RedisChatStore":
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        return cls(client, prefix, cache_ttl_seconds)

    def ping(self) -> bool:
        return bool(self.redis.ping())

    def save_message(self, session_id: str, role: str, content: str) -> None:
        self.redis.rpush(
            self._session_key(session_id),
            json.dumps({"role": role, "content": content}, ensure_ascii=False),
        )

    def load_messages(self, session_id: str, limit: int) -> list[MemoryMessage]:
        raw_messages = self.redis.lrange(self._session_key(session_id), -limit, -1)
        messages: list[MemoryMessage] = []
        for entry in raw_messages:
            payload = json.loads(entry)
            messages.append(MemoryMessage(role=payload["role"], content=payload["content"]))
        return messages

    def get_cached_answer(self, cache_key: str) -> str | None:
        return self.redis.get(self._cache_key(cache_key))

    def set_cached_answer(self, cache_key: str, answer: str) -> None:
        self.redis.setex(self._cache_key(cache_key), self.cache_ttl_seconds, answer)

    def build_cache_key(
        self,
        *,
        model: str,
        question: str,
        history: list[MemoryMessage],
        sources: list[dict[str, Any]],
        top_k: int,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> str:
        payload = {
            "model": model,
            "question": question,
            "history": [{"role": item.role, "content": item.content} for item in history],
            "sources": sources,
            "top_k": top_k,
            "tool_results": tool_results or [],
        }
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def clear_namespace(self) -> None:
        cursor = 0
        pattern = f"{self.prefix}:*"
        while True:
            cursor, keys = self.redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                self.redis.delete(*keys)
            if cursor == 0:
                break

    def _session_key(self, session_id: str) -> str:
        return f"{self.prefix}:session:{session_id}"

    def _cache_key(self, cache_key: str) -> str:
        return f"{self.prefix}:cache:{cache_key}"
