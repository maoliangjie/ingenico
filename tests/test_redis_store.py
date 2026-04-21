import fakeredis

from app.services.redis_store import MemoryMessage, RedisChatStore


def build_store() -> RedisChatStore:
    return RedisChatStore(fakeredis.FakeRedis(decode_responses=True), "ingenico-test", 120)


def test_redis_store_round_trips_messages():
    store = build_store()

    store.save_message("session-1", "user", "hello")
    store.save_message("session-1", "assistant", "world")

    messages = store.load_messages("session-1", 10)

    assert messages == [
        MemoryMessage(role="user", content="hello"),
        MemoryMessage(role="assistant", content="world"),
    ]


def test_redis_store_caches_answers():
    store = build_store()
    cache_key = store.build_cache_key(
        model="demo-model",
        question="hello",
        history=[MemoryMessage(role="user", content="earlier")],
        sources=[{"file_name": "faq.txt", "content": "answer"}],
        top_k=4,
    )

    assert store.get_cached_answer(cache_key) is None

    store.set_cached_answer(cache_key, "cached answer")

    assert store.get_cached_answer(cache_key) == "cached answer"
