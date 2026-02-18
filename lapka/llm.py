"""Minimal OpenAI-compatible LLM client for Lapka."""

from __future__ import annotations

import json
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx

from .config import LLMProfile

log = logging.getLogger("lapka.llm")

_RETRY_DELAYS = [1.0, 3.0, 8.0]


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    usage: Usage | None = None
    finish_reason: str | None = None


class LLMClient:
    """Async client for any OpenAI-compatible chat completions API."""

    def __init__(self, profile: LLMProfile):
        self.profile = profile
        self._client = httpx.AsyncClient(timeout=120.0)

    async def close(self) -> None:
        await self._client.aclose()

    def _url(self) -> str:
        base = self.profile.api_base.rstrip("/")
        return f"{base}/chat/completions"

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.profile.api_key:
            h["Authorization"] = f"Bearer {self.profile.api_key}"
        # OpenRouter optional headers
        if "openrouter.ai" in self.profile.api_base:
            h["HTTP-Referer"] = "https://github.com/make-ai-great-again/lapka"
            h["X-Title"] = "Lapka"
        return h

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send chat completion request with retries."""
        body: dict[str, Any] = {
            "model": self.profile.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        last_err: Exception | None = None
        for delay in _RETRY_DELAYS:
            try:
                resp = await self._client.post(
                    self._url(), json=body, headers=self._headers()
                )
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("retry-after", delay))
                    log.warning("Rate limited, waiting %.1fs", retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return self._parse_response(resp.json())
            except (httpx.HTTPStatusError, httpx.TransportError) as e:
                last_err = e
                log.warning("LLM request failed: %s, retrying in %.1fs", e, delay)
                await asyncio.sleep(delay)

        raise RuntimeError(f"LLM request failed after retries: {last_err}")

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """Stream chat completion, yielding text chunks."""
        body: dict[str, Any] = {
            "model": self.profile.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        async with self._client.stream(
            "POST", self._url(), json=body, headers=self._headers()
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text
                except json.JSONDecodeError:
                    continue

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        usage_data = data.get("usage")

        usage = None
        if usage_data:
            usage = Usage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

        tool_calls = msg.get("tool_calls")
        return LLMResponse(
            content=msg.get("content"),
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=choice.get("finish_reason"),
        )
