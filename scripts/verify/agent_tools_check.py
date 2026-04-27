from __future__ import annotations

import json
import os

import httpx


API_BASE = os.getenv("INGENICO_API_BASE_URL", "http://localhost:8000")


def main() -> None:
    with httpx.Client(timeout=30.0, trust_env=False) as client:
        catalog_response = client.get(f"{API_BASE}/mcp/tools")
        catalog_response.raise_for_status()
        catalog = catalog_response.json()

        invoke_response = client.post(
            f"{API_BASE}/mcp/tools/get_system_health",
            json={"arguments": {}},
        )
        invoke_response.raise_for_status()

    print(
        json.dumps(
            {
                "tool_count": len(catalog["tools"]),
                "tools": [tool["name"] for tool in catalog["tools"]],
                "health_tool": invoke_response.json()["tool"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
