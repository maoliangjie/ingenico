from __future__ import annotations

import argparse
import json
import os

import httpx


API_BASE = os.getenv("INGENICO_API_BASE_URL", "http://localhost:8000")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", required=True)
    args = parser.parse_args()

    with httpx.Client(timeout=60.0, trust_env=False) as client:
        first = client.post(f"{API_BASE}/chat", json={"message": args.message})
        first.raise_for_status()
        second = client.post(f"{API_BASE}/chat", json={"message": args.message})
        second.raise_for_status()

    print(
        json.dumps(
            {
                "first_cache_hit": first.json()["cache_hit"],
                "second_cache_hit": second.json()["cache_hit"],
                "first_session_id": first.json()["session_id"],
                "second_session_id": second.json()["session_id"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
