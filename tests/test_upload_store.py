import pytest

from app.services.upload_store import UploadStore


def build_store(tmp_path) -> UploadStore:
    return UploadStore(tmp_path / "uploads", tmp_path / "uploads.json")


def test_upload_store_create_replace_delete(tmp_path):
    store = build_store(tmp_path)

    created = store.create_upload("note.txt", b"hello")
    assert len(store.list_uploads()) == 1

    replaced = store.replace_upload(created.file_id, "note.txt", b"world")
    assert replaced.file_id == created.file_id

    store.delete_upload(created.file_id)
    assert store.list_uploads() == []


def test_upload_store_rejects_unsupported_suffix(tmp_path):
    store = build_store(tmp_path)

    with pytest.raises(ValueError):
        store.create_upload("malware.exe", b"boom")
