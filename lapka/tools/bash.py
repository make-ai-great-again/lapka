"""Bash tool — execute shell commands with safety and output compression."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from . import tool

log = logging.getLogger("lapka.tools.bash")

# Default blocked patterns
_BLOCKED = [
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev",
    ":(){:|:&};:", "chmod -R 777 /", "shutdown", "reboot",
    "init 0", "init 6",
]


def _is_blocked(command: str, blocklist: list[str]) -> bool:
    cmd_lower = command.lower().strip()
    for pat in blocklist:
        if pat.lower() in cmd_lower:
            return True
    return False


def _compress_output(text: str, max_chars: int = 2000) -> str:
    """Compress long output: head + ... + tail."""
    if len(text) <= max_chars:
        return text

    lines = text.split("\n")
    if len(lines) <= 30:
        return text[:max_chars] + f"\n... (truncated, {len(text)} chars total)"

    head = "\n".join(lines[:10])
    tail = "\n".join(lines[-20:])
    return (
        f"{head}\n"
        f"... ({len(lines)} lines total, showing head 10 + tail 20) ...\n"
        f"{tail}"
    )


@tool(
    name="bash",
    description="Execute a shell command. Returns stdout/stderr.",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute.",
            },
        },
        "required": ["command"],
    },
)
async def bash_exec(
    command: str,
    working_directory: str = ".",
    timeout: int = 30,
    blocked_commands: list[str] | None = None,
    **_: Any,
) -> str:
    blocklist = blocked_commands or _BLOCKED

    if _is_blocked(command, blocklist):
        return f"⛔ BLOCKED: '{command}' matches safety blocklist."

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.expanduser(working_directory),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        return f"⏰ TIMEOUT after {timeout}s: '{command}'"
    except Exception as e:
        return f"❌ ERROR: {e}"

    exit_code = proc.returncode
    out = stdout.decode(errors="replace").strip() if stdout else ""
    err = stderr.decode(errors="replace").strip() if stderr else ""

    parts = []
    if exit_code != 0:
        parts.append(f"exit code: {exit_code}")
    if out:
        parts.append(_compress_output(out))
    if err:
        parts.append(f"stderr: {_compress_output(err, 500)}")
    if not parts:
        parts.append("✓ (no output)")

    return "\n".join(parts)
