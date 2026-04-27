from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path

import httpx


API_BASE = os.getenv("INGENICO_API_BASE_URL", "http://localhost:8000")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        help="Optional local file path to upload. Useful for testing text-based PDF uploads.",
    )
    args = parser.parse_args()

    upload_name = "verify-note.txt"
    upload_bytes = b"stage3 upload create"
    upload_type = "text/plain"
    if args.file:
        file_path = Path(args.file)
        upload_name = file_path.name
        upload_bytes = file_path.read_bytes()
        upload_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "application/octet-stream"

    with httpx.Client(timeout=60.0, trust_env=False) as client:
        create = client.post(
            f"{API_BASE}/upload",
            files={"file": (upload_name, io.BytesIO(upload_bytes), upload_type)},
        )
        create.raise_for_status()
        created = create.json()

        list_response = client.get(f"{API_BASE}/uploads")
        list_response.raise_for_status()

        replace = client.put(
            f"{API_BASE}/uploads/{created['file_id']}",
            files={"file": (upload_name, io.BytesIO(upload_bytes), upload_type)},
        )
        replace.raise_for_status()

        delete = client.delete(f"{API_BASE}/uploads/{created['file_id']}")
        delete.raise_for_status()

    print(
        json.dumps(
            {
                "created": created,
                "listed_count_after_create": len(list_response.json()["files"]),
                "replaced": replace.json(),
                "deleted_status": delete.status_code,
                "uploaded_name": upload_name,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
