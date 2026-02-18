"""
System prompt templates for Lapka agent.

⚠️ CONTEXT BUDGET GUARD ⚠️
System prompt MUST stay under 200 tokens (~700 chars).
Every word costs tokens × every LLM call. Think thrice before adding anything.
Current: ~185 tokens. Budget: 200 max.
"""

from datetime import datetime

import platform

_SYSTEM_TEMPLATE = """\
You are Lapka 🐾, a task-execution AI. Use tools, be concise.
Context: {date} | OS: {os}

Rules:
- Prefer bash for system ops. patch_file for edits.
- Web scraping: prefer http_request over curl (cleaner output).
- On failure: ALWAYS try 2-3 alternatives.
- Brief summary after task completion.

Tools: bash, read_file, write_file, patch_file, list_dir, http_request.
"""


def get_system_prompt() -> str:
    system = platform.system()
    os_name = "macOS" if system == "Darwin" else system
    return _SYSTEM_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M %Z"),
        os=os_name
    )


COMPACTION_PROMPT = """\
CONTEXT CHECKPOINT. Summarize conversation for another LLM to continue.
Include: progress, decisions, constraints, next steps, critical paths/data.
Bullet points. Max 400 tokens.\
"""
