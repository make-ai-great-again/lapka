"""Context manager with Codex-style compaction for Lapka."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .llm import LLMClient

from .prompts import SYSTEM_PROMPT, COMPACTION_PROMPT

log = logging.getLogger("lapka.context")


def estimate_tokens(text: str) -> int:
    """Rough token estimate. ~3.5 chars per token for mixed en/ru."""
    return max(1, int(len(text) / 3.5))


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        # Tool calls add overhead
        if msg.get("tool_calls"):
            total += estimate_tokens(json.dumps(msg["tool_calls"]))
    return total


@dataclass
class ContextManager:
    """Manages conversation context with Codex-style compaction."""

    max_tokens: int = 4000
    compact_threshold: float = 0.8
    session_dir: Path | None = None

    # Internal state
    _full_history: list[dict[str, Any]] = field(default_factory=list)
    _compaction_summary: str | None = None
    _compaction_count: int = 0
    _total_tokens_used: int = 0

    def reset(self) -> None:
        """Clear all history."""
        self._full_history.clear()
        self._compaction_summary = None
        self._compaction_count = 0
        self._total_tokens_used = 0

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the full history."""
        msg: dict[str, Any] = {"role": role, "content": content}
        msg.update(kwargs)
        self._full_history.append(msg)

    def add_raw(self, message: dict[str, Any]) -> None:
        """Add a raw message dict (for assistant messages with tool_calls)."""
        self._full_history.append(message)

    def get_messages(self) -> list[dict[str, Any]]:
        """Return compact message list for LLM: system + compaction + recent."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        if self._compaction_summary:
            messages.append({
                "role": "user",
                "content": (
                    f"[CONTEXT CHECKPOINT — previous conversation summary]\n"
                    f"{self._compaction_summary}\n"
                    f"[END CHECKPOINT — continue from here]"
                ),
            })

        # Add recent history (after last compaction point or all if no compaction)
        messages.extend(self._full_history)
        return messages

    def needs_compaction(self) -> bool:
        """Check if context exceeds threshold."""
        messages = self.get_messages()
        current = estimate_messages_tokens(messages)
        threshold = int(self.max_tokens * self.compact_threshold)
        return current > threshold

    async def compact(self, llm_client: "LLMClient") -> None:
        """Perform Codex-style compaction: summarize full history, rebuild."""
        if not self._full_history:
            return

        log.info(
            "Compacting context (count=%d, messages=%d)",
            self._compaction_count + 1,
            len(self._full_history),
        )

        # Build the full conversation for summarization
        summary_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # If we have a previous compaction summary, include it
        if self._compaction_summary:
            summary_messages.append({
                "role": "user",
                "content": f"[Previous checkpoint]\n{self._compaction_summary}",
            })

        # Add ALL history since last compaction
        summary_messages.extend(self._full_history)

        # Ask cheap model to summarize
        summary_messages.append({
            "role": "user",
            "content": COMPACTION_PROMPT,
        })

        response = await llm_client.chat(summary_messages, temperature=0.1)
        self._compaction_summary = response.content or "No summary generated."

        if response.usage:
            self._total_tokens_used += response.usage.total_tokens

        # Keep only last 3 messages (preserving tool call pairs)
        keep_count = min(6, len(self._full_history))
        self._full_history = self._full_history[-keep_count:]
        self._compaction_count += 1

        log.info(
            "Compaction done. Summary: %d chars, kept %d messages",
            len(self._compaction_summary),
            len(self._full_history),
        )

    def save_checkpoint(self, session_id: str) -> Path | None:
        """Save current state to disk."""
        if not self.session_dir:
            return None

        self.session_dir.mkdir(parents=True, exist_ok=True)
        path = self.session_dir / f"{session_id}.json"
        data = {
            "session_id": session_id,
            "timestamp": time.time(),
            "compaction_summary": self._compaction_summary,
            "compaction_count": self._compaction_count,
            "total_tokens_used": self._total_tokens_used,
            "history": self._full_history,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        log.info("Checkpoint saved: %s", path)
        return path

    def load_checkpoint(self, session_id: str) -> bool:
        """Restore state from disk."""
        if not self.session_dir:
            return False

        path = self.session_dir / f"{session_id}.json"
        if not path.exists():
            return False

        data = json.loads(path.read_text())
        self._compaction_summary = data.get("compaction_summary")
        self._compaction_count = data.get("compaction_count", 0)
        self._total_tokens_used = data.get("total_tokens_used", 0)
        self._full_history = data.get("history", [])
        log.info("Checkpoint loaded: %s (%d messages)", session_id, len(self._full_history))
        return True

    @property
    def stats(self) -> dict[str, Any]:
        messages = self.get_messages()
        return {
            "history_messages": len(self._full_history),
            "estimated_tokens": estimate_messages_tokens(messages),
            "compaction_count": self._compaction_count,
            "total_tokens_used": self._total_tokens_used,
            "has_checkpoint": self._compaction_summary is not None,
        }
