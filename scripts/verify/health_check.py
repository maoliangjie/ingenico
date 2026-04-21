from __future__ import annotations

import json
import os

import httpx


API_BASE = os.getenv("INGENICO_API_BASE_URL", "http://localhost:8000")


def main() -> None:
    response = httpx.get(f"{API_BASE}/health", timeout=30.0, trust_env=False)
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
