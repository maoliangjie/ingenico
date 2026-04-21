import json

from app.services.document_loader import (
    SourceDirectory,
    compute_sources_fingerprint,
    flatten_json,
    load_documents_from_sources,
)


def test_flatten_json_preserves_nested_paths():
    payload = {"project": {"name": "Ingenico", "capabilities": ["rag", "memory"]}}

    lines = flatten_json(payload)

    assert "project.name: Ingenico" in lines
    assert "project.capabilities[0]: rag" in lines
    assert "project.capabilities[1]: memory" in lines


def test_load_documents_reads_supported_types_from_multiple_sources(tmp_path):
    static_dir = tmp_path / "data"
    upload_dir = tmp_path / "uploads"
    static_dir.mkdir()
    upload_dir.mkdir()
    (static_dir / "note.txt").write_text("hello", encoding="utf-8")
    (upload_dir / "guide.md").write_text("# title", encoding="utf-8")
    (upload_dir / "facts.json").write_text(
        json.dumps({"product": {"name": "Desk 5000"}}),
        encoding="utf-8",
    )

    docs = load_documents_from_sources(
        [
            SourceDirectory(name="static", root=static_dir, scope="static"),
            SourceDirectory(name="uploads", root=upload_dir, scope="upload"),
        ]
    )

    assert len(docs) == 3
    assert {doc.metadata["file_name"] for doc in docs} == {"note.txt", "guide.md", "facts.json"}
    assert {doc.metadata["scope"] for doc in docs} == {"static", "upload"}


def test_fingerprint_changes_when_source_changes(tmp_path):
    static_dir = tmp_path / "data"
    static_dir.mkdir()
    file_path = static_dir / "faq.txt"
    file_path.write_text("first", encoding="utf-8")
    sources = [SourceDirectory(name="static", root=static_dir, scope="static")]

    before = compute_sources_fingerprint(sources)
    file_path.write_text("second", encoding="utf-8")
    after = compute_sources_fingerprint(sources)

    assert before["fingerprint"] != after["fingerprint"]
