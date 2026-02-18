"""HTTP request tool for Lapka agent."""

from __future__ import annotations

from typing import Any

import httpx

from . import tool


def _compress_body(text: str, max_chars: int = 2000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text)} chars total)"


@tool(
    name="http_request",
    description="Make an HTTP request. Returns status code and response body (truncated if long).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to request."},
            "method": {"type": "string", "description": "HTTP method. Default: GET.", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
            "body": {"type": "string", "description": "Request body (for POST/PUT/PATCH). Optional."},
            "headers": {"type": "object", "description": "Extra headers. Optional."},
        },
        "required": ["url"],
    },
)
async def http_request(
    url: str,
    method: str = "GET",
    body: str | None = None,
    headers: dict[str, str] | None = None,
    **_: Any,
) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.request(
                method=method.upper(),
                url=url,
                content=body,
                headers=headers,
            )

        status = f"HTTP {resp.status_code}"
        content_type = resp.headers.get("content-type", "")

        if "json" in content_type:
            text = resp.text
        elif "html" in content_type:
            # Strip HTML tags for brevity
            import re
            text = re.sub(r"<[^>]+>", "", resp.text)
            text = re.sub(r"\s+", " ", text).strip()
        else:
            text = resp.text

        return f"{status}\n{_compress_body(text)}"

    except httpx.TimeoutException:
        return f"⏰ TIMEOUT requesting {url}"
    except Exception as e:
        return f"❌ HTTP Error: {e}"
