import json

from app.services.document_loader import (
    compute_data_fingerprint,
    flatten_json,
    load_documents,
)


def test_flatten_json_preserves_nested_paths():
    payload = {"project": {"name": "Ingenico", "capabilities": ["rag", "memory"]}}

    lines = flatten_json(payload)

    assert "project.name: Ingenico" in lines
    assert "project.capabilities[0]: rag" in lines
    assert "project.capabilities[1]: memory" in lines


def test_load_documents_reads_supported_types(tmp_path):
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "guide.md").write_text("# title", encoding="utf-8")
    (tmp_path / "facts.json").write_text(
        json.dumps({"product": {"name": "Desk 5000"}}),
        encoding="utf-8",
    )

    docs = load_documents(tmp_path)

    assert len(docs) == 3
    assert {doc.metadata["file_name"] for doc in docs} == {
        "note.txt",
        "guide.md",
        "facts.json",
    }


def test_fingerprint_changes_when_source_changes(tmp_path):
    file_path = tmp_path / "faq.txt"
    file_path.write_text("first", encoding="utf-8")

    before = compute_data_fingerprint(tmp_path)
    file_path.write_text("second", encoding="utf-8")
    after = compute_data_fingerprint(tmp_path)

    assert before["fingerprint"] != after["fingerprint"]
