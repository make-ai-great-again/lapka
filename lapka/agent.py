"""Agent loop — the heart of Lapka."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Callable, Awaitable

from .config import Config
from .context import ContextManager
from .llm import LLMClient, LLMResponse
from .tools import get_tool, tools_for_llm

# Import tools so they register themselves
from .tools import bash, files, http  # noqa: F401

log = logging.getLogger("lapka.agent")

# Callback type for streaming output to connectors
OnOutput = Callable[[str], Awaitable[None]]


class Agent:
    """Lapka agent: message → LLM → tool calls → result → repeat."""

    def __init__(self, config: Config):
        self.config = config
        self.ctx = ContextManager(
            max_tokens=config.max_context_tokens,
            compact_threshold=config.compact_threshold,
            session_dir=config.config_dir / "sessions",
        )
        self.main_llm = LLMClient(config.main)
        self.compact_llm = LLMClient(config.compact_profile)
        self._tools_json = tools_for_llm()

    async def close(self) -> None:
        await self.main_llm.close()
        if self.compact_llm is not self.main_llm:
            await self.compact_llm.close()

    def reset(self) -> None:
        """Reset conversation context."""
        self.ctx.reset()

    async def run(
        self,
        user_message: str,
        on_output: OnOutput | None = None,
        image_b64: str | None = None,
    ) -> str:
        """Process a user message through the agent loop.
        
        Returns the final text response.
        """
        if image_b64:
            # Multi-part content for vision
            content: list[dict[str, Any]] = [
                {"type": "text", "text": user_message or "What's in this image?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ]
            self.ctx.add_raw({"role": "user", "content": content})
        else:
            self.ctx.add_message("user", user_message)

        iteration = 0
        while iteration < self.config.max_tool_iterations:
            iteration += 1

            # Check if compaction needed before sending
            if self.ctx.needs_compaction():
                if on_output:
                    await on_output("🗜️ Compacting context...")
                await self.ctx.compact(self.compact_llm)

            # Send to LLM
            messages = self.ctx.get_messages()
            response = await self.main_llm.chat(messages, tools=self._tools_json)

            # Track usage
            if response.usage:
                log.debug(
                    "Tokens: prompt=%d, completion=%d",
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )
                self.ctx.update_actual_tokens(response.usage.prompt_tokens)

            # If the model returns text without tool calls — we're done
            if not response.tool_calls:
                answer = response.content or ""
                self.ctx.add_message("assistant", answer)
                return answer

            # Process tool calls
            # Store assistant message with tool_calls
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.content or ""}
            assistant_msg["tool_calls"] = response.tool_calls
            self.ctx.add_raw(assistant_msg)

            for tc in response.tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {"command": tc["function"]["arguments"]}

                tool_call_id = tc.get("id", f"call_{tool_name}")

                if on_output:
                    await on_output(f"🔧 {tool_name}: {_summarize_args(args)}")

                # Execute tool
                result = await self._execute_tool(tool_name, args)

                # Nudge model to retry on failure
                if result.startswith(("❌", "⏰")):
                    result += "\n[Hint: try an alternative approach — different tool, command, or source.]"

                if on_output:
                    preview = result[:200] + "..." if len(result) > 200 else result
                    await on_output(f"   → {preview}")

                # Add tool result to context
                self.ctx.add_raw({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result,
                })

        # Max iterations reached
        answer = "⚠️ Max tool iterations reached. Stopping."
        self.ctx.add_message("assistant", answer)
        return answer

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> str:
        """Execute a registered tool by name."""
        tool_def = get_tool(name)
        if not tool_def:
            return f"❌ Unknown tool: {name}"

        try:
            # Inject config-based defaults
            if name == "bash":
                args.setdefault("working_directory", self.config.working_directory)
                args.setdefault("timeout", self.config.command_timeout)
                args.setdefault("blocked_commands", self.config.blocked_commands)

            return await tool_def.fn(**args)
        except Exception as e:
            log.exception("Tool %s failed", name)
            return f"❌ Tool error: {e}"

    @property
    def stats(self) -> dict[str, Any]:
        return self.ctx.stats


def _summarize_args(args: dict[str, Any]) -> str:
    """Short summary of tool args for display."""
    if "command" in args:
        cmd = args["command"]
        return cmd[:80] + "..." if len(cmd) > 80 else cmd
    if "path" in args:
        return args["path"]
    if "url" in args:
        return args["url"]
    return json.dumps(args)[:80]
