from __future__ import annotations

import io
import json
import os

import httpx


API_BASE = os.getenv("INGENICO_API_BASE_URL", "http://localhost:8000")


def main() -> None:
    with httpx.Client(timeout=60.0, trust_env=False) as client:
        create = client.post(
            f"{API_BASE}/upload",
            files={"file": ("verify-note.txt", io.BytesIO(b"stage2 upload create"), "text/plain")},
        )
        create.raise_for_status()
        created = create.json()

        list_response = client.get(f"{API_BASE}/uploads")
        list_response.raise_for_status()

        replace = client.put(
            f"{API_BASE}/uploads/{created['file_id']}",
            files={"file": ("verify-note.txt", io.BytesIO(b"stage2 upload replace"), "text/plain")},
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
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
