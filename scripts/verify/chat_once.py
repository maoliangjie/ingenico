from __future__ import annotations

import argparse
import json
import os

import httpx


API_BASE = os.getenv("INGENICO_API_BASE_URL", "http://localhost:8000")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", required=True)
    parser.add_argument("--session-id")
    parser.add_argument("--top-k", type=int)
    args = parser.parse_args()

    payload = {"message": args.message}
    if args.session_id:
        payload["session_id"] = args.session_id
    if args.top_k:
        payload["top_k"] = args.top_k

    response = httpx.post(f"{API_BASE}/chat", json=payload, timeout=60.0, trust_env=False)
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
