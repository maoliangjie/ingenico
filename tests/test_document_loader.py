import json
from io import BytesIO

from pypdf import PdfWriter

from app.services.document_loader import (
    SourceDirectory,
    compute_sources_fingerprint,
    extract_pdf_text,
    flatten_json,
    load_documents_from_sources,
)


def build_text_pdf_bytes(text: str = "Hello PDF") -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT\n/F1 18 Tf\n72 72 Td\n({escaped}) Tj\nET".encode("utf-8")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    chunks = [header]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{index} 0 obj\n".encode("ascii"))
        chunks.append(obj)
        chunks.append(b"\nendobj\n")

    xref_offset = sum(len(chunk) for chunk in chunks)
    xref = [f"xref\n0 {len(objects) + 1}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer\n<< /Root 1 0 R /Size {len(objects) + 1} >>\nstartxref\n{xref_offset}\n%%EOF".encode(
            "ascii"
        )
    )
    return b"".join(chunks + xref + [trailer])


def build_blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_flatten_json_preserves_nested_paths():
    payload = {"project": {"name": "Ingenico", "capabilities": ["rag", "memory"]}}

    lines = flatten_json(payload)

    assert "project.name: Ingenico" in lines
    assert "project.capabilities[0]: rag" in lines
    assert "project.capabilities[1]: memory" in lines


def test_extract_pdf_text_reads_text_based_pdf():
    text = extract_pdf_text(build_text_pdf_bytes("PDF knowledge"))

    assert "PDF knowledge" in text


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
    (upload_dir / "manual.pdf").write_bytes(build_text_pdf_bytes("PDF handbook"))

    docs = load_documents_from_sources(
        [
            SourceDirectory(name="static", root=static_dir, scope="static"),
            SourceDirectory(name="uploads", root=upload_dir, scope="upload"),
        ]
    )

    assert len(docs) == 4
    assert {doc.metadata["file_name"] for doc in docs} == {"note.txt", "guide.md", "facts.json", "manual.pdf"}
    assert {doc.metadata["scope"] for doc in docs} == {"static", "upload"}
    assert any(doc.metadata["file_type"] == "pdf" for doc in docs)


def test_load_documents_skips_unreadable_or_empty_static_pdfs(tmp_path, caplog):
    static_dir = tmp_path / "data"
    static_dir.mkdir()
    (static_dir / "ok.txt").write_text("fallback", encoding="utf-8")
    (static_dir / "empty.pdf").write_bytes(build_blank_pdf_bytes())
    sources = [SourceDirectory(name="static", root=static_dir, scope="static")]

    with caplog.at_level("WARNING"):
        docs = load_documents_from_sources(sources)

    assert len(docs) == 1
    assert docs[0].metadata["file_name"] == "ok.txt"
    assert "Skipping PDF source 'empty.pdf'" in caplog.text


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
