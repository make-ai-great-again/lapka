"""File tools — read, write, patch, list for Lapka agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from . import tool


def _safe_path(path_str: str) -> Path:
    """Expand ~ and resolve path."""
    return Path(os.path.expanduser(path_str)).resolve()


@tool(
    name="read_file",
    description="Read a file content. Optionally specify line range.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read."},
            "start_line": {"type": "integer", "description": "Start line (1-indexed). Optional."},
            "end_line": {"type": "integer", "description": "End line (1-indexed, inclusive). Optional."},
        },
        "required": ["path"],
    },
)
async def read_file(path: str, start_line: int | None = None, end_line: int | None = None, **_: Any) -> str:
    p = _safe_path(path)
    if not p.exists():
        return f"❌ File not found: {path}"
    if not p.is_file():
        return f"❌ Not a file: {path}"

    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"❌ Error reading file: {e}"

    lines = text.split("\n")
    total = len(lines)

    if start_line is not None or end_line is not None:
        s = max(1, start_line or 1) - 1
        e = min(total, end_line or total)
        selected = lines[s:e]
        numbered = [f"{s + i + 1}: {line}" for i, line in enumerate(selected)]
        header = f"[{p.name} lines {s+1}-{e} of {total}]"
        return f"{header}\n" + "\n".join(numbered)

    # Full file — but compress if too long
    if total > 100:
        head = "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines[:50]))
        tail = "\n".join(f"{total-19+i}: {l}" for i, l in enumerate(lines[-20:]))
        return (
            f"[{p.name} — {total} lines, showing head 50 + tail 20]\n"
            f"{head}\n...\n{tail}"
        )

    numbered = [f"{i+1}: {line}" for i, line in enumerate(lines)]
    return f"[{p.name} — {total} lines]\n" + "\n".join(numbered)


@tool(
    name="write_file",
    description="Write content to a file. Creates parent dirs if needed.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write."},
            "content": {"type": "string", "description": "Content to write."},
        },
        "required": ["path", "content"],
    },
)
async def write_file(path: str, content: str, **_: Any) -> str:
    p = _safe_path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"✓ Written {len(content)} chars to {p.name}"
    except Exception as e:
        return f"❌ Error writing file: {e}"


@tool(
    name="patch_file",
    description="Edit a file by replacing a search string with replacement. More token-efficient than rewriting the whole file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to edit."},
            "search": {"type": "string", "description": "Exact string to find."},
            "replace": {"type": "string", "description": "Replacement string."},
        },
        "required": ["path", "search", "replace"],
    },
)
async def patch_file(path: str, search: str, replace: str, **_: Any) -> str:
    p = _safe_path(path)
    if not p.exists():
        return f"❌ File not found: {path}"

    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        return f"❌ Error reading file: {e}"

    count = text.count(search)
    if count == 0:
        return f"❌ Search string not found in {p.name}. Check exact whitespace/content."
    if count > 1:
        return f"⚠️ Found {count} occurrences. Replacing all."

    new_text = text.replace(search, replace)
    p.write_text(new_text, encoding="utf-8")
    return f"✓ Patched {p.name} ({count} replacement{'s' if count > 1 else ''})"


@tool(
    name="list_dir",
    description="List contents of a directory.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path."},
        },
        "required": ["path"],
    },
)
async def list_dir(path: str, **_: Any) -> str:
    p = _safe_path(path)
    if not p.exists():
        return f"❌ Path not found: {path}"
    if not p.is_dir():
        return f"❌ Not a directory: {path}"

    try:
        entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return f"❌ Permission denied: {path}"

    if not entries:
        return f"[{p.name}/] (empty)"

    lines = []
    for entry in entries[:100]:  # Limit to 100 entries
        if entry.is_dir():
            lines.append(f"  📁 {entry.name}/")
        else:
            size = entry.stat().st_size
            if size > 1_000_000:
                sz = f"{size / 1_000_000:.1f}M"
            elif size > 1000:
                sz = f"{size / 1000:.1f}K"
            else:
                sz = f"{size}B"
            lines.append(f"  📄 {entry.name} ({sz})")

    header = f"[{p.name}/] {len(entries)} items"
    if len(entries) > 100:
        header += " (showing first 100)"
    return header + "\n" + "\n".join(lines)
