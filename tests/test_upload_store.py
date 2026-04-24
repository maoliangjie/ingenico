from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.services.upload_store import UploadStore


def build_store(tmp_path) -> UploadStore:
    return UploadStore(tmp_path / "uploads", tmp_path / "uploads.json")


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


def test_upload_store_create_replace_delete(tmp_path):
    store = build_store(tmp_path)

    created = store.create_upload("note.txt", b"hello")
    assert len(store.list_uploads()) == 1

    replaced = store.replace_upload(created.file_id, "note.txt", b"world")
    assert replaced.file_id == created.file_id

    store.delete_upload(created.file_id)
    assert store.list_uploads() == []


def test_upload_store_accepts_text_pdf(tmp_path):
    store = build_store(tmp_path)

    created = store.create_upload("sample.pdf", build_text_pdf_bytes("Policy PDF"))

    assert created.file_name == "sample.pdf"
    assert created.stored_name.endswith(".pdf")


def test_upload_store_rejects_unextractable_pdf(tmp_path):
    store = build_store(tmp_path)

    with pytest.raises(ValueError):
        store.create_upload("empty.pdf", build_blank_pdf_bytes())


def test_upload_store_rejects_unsupported_suffix(tmp_path):
    store = build_store(tmp_path)

    with pytest.raises(ValueError):
        store.create_upload("malware.exe", b"boom")
