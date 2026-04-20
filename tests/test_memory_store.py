from app.services.memory_store import SQLiteMemoryStore


def test_sqlite_memory_store_persists_messages(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite3")

    store.save_message("session-1", "user", "hello")
    store.save_message("session-1", "assistant", "hi there")

    messages = store.load_messages("session-1", limit=10)

    assert [message.role for message in messages] == ["user", "assistant"]
    assert [message.content for message in messages] == ["hello", "hi there"]


def test_sqlite_memory_store_limits_results(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite3")
    for index in range(5):
        store.save_message("session-2", "user", f"msg-{index}")

    messages = store.load_messages("session-2", limit=3)

    assert [message.content for message in messages] == ["msg-2", "msg-3", "msg-4"]
