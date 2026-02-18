"""CLI connector — interactive terminal interface for Lapka."""

from __future__ import annotations

import asyncio
import sys

from ..agent import Agent
from ..config import Config


# ANSI colors
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_MAGENTA = "\033[35m"


async def _on_output(text: str) -> None:
    """Print tool activity in dim text."""
    print(f"{_DIM}{text}{_RESET}")


async def run_cli(config: Config) -> None:
    """Run interactive CLI loop."""
    agent = Agent(config)

    print(f"{_BOLD}{_CYAN}")
    print("  🐾 Lapka — Ultra-lightweight AI Agent")
    print(f"  Model: {config.main.model}")
    print(f"  Compact: {config.compact_profile.model}")
    print(f"  API: {config.main.api_base}")
    print(f"{_RESET}")
    print(f"  {_DIM}Type your message. /reset to clear, /stats to see context, /quit to exit.{_RESET}")
    print()

    try:
        while True:
            try:
                user_input = input(f"{_GREEN}{_BOLD}You ▸ {_RESET}")
            except EOFError:
                break

            if not user_input.strip():
                continue

            cmd = user_input.strip().lower()
            if cmd in ("/quit", "/exit", "/q"):
                print(f"\n{_DIM}Bye! 🐾{_RESET}")
                break
            elif cmd == "/reset":
                agent.reset()
                print(f"{_YELLOW}↺ Context reset.{_RESET}")
                continue
            elif cmd == "/stats":
                stats = agent.stats
                print(f"{_DIM}Context: {stats}{_RESET}")
                continue
            elif cmd == "/compact":
                print(f"{_YELLOW}🗜️ Forcing compaction...{_RESET}")
                await agent.ctx.compact(agent.compact_llm)
                print(f"{_YELLOW}✓ Done. Stats: {agent.stats}{_RESET}")
                continue

            # Process message
            print(f"\n{_DIM}Thinking...{_RESET}")
            try:
                response = await agent.run(user_input, on_output=_on_output)
                print(f"\n{_MAGENTA}{_BOLD}Lapka ▸{_RESET} {response}\n")
            except Exception as e:
                print(f"\n{_YELLOW}❌ Error: {e}{_RESET}\n")

    finally:
        await agent.close()
