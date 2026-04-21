from __future__ import annotations

import argparse
import os

import httpx


API_BASE = os.getenv("INGENICO_API_BASE_URL", "http://localhost:8000")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", required=True)
    parser.add_argument("--session-id")
    args = parser.parse_args()

    payload = {"message": args.message}
    if args.session_id:
        payload["session_id"] = args.session_id

    with httpx.stream("POST", f"{API_BASE}/chat/stream", json=payload, timeout=60.0, trust_env=False) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                print(line)


if __name__ == "__main__":
    main()
