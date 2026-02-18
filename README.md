# Lapka 🐾

> Ultra-lightweight AI agent. AK-47 of the AI world.

10-100× less context than OpenClaw/Claude Code/Codex. Python. No heavy deps. Any OpenAI-compatible API.

## Quick Start

```bash
# Install
pip install -e .

# Set API key (OpenRouter example)
export LAPKA_API_KEY="sk-or-..."

# Run in CLI mode
lapka --cli

# Or with a specific model
lapka --cli --model "anthropic/claude-3.5-haiku"

# Or with Ollama (local)
lapka --cli --api-base "http://localhost:11434/v1" --model "qwen2.5:14b"
```

## Telegram Bot

```bash
export LAPKA_TELEGRAM_TOKEN="123456:ABC..."
lapka --telegram
```

## Configuration

Create `~/.lapka/config.json`:

```json
{
    "api_base": "https://openrouter.ai/api/v1",
    "api_key": "sk-or-...",
    "model": "google/gemini-2.0-flash-001",
    
    "compact_model": "google/gemini-2.0-flash-001",
    
    "telegram_bot_token": "123456:ABC...",
    "telegram_allowed_users": [],
    "max_context_tokens": 4000,
    "working_directory": "."
}
```

### Two Model Profiles

| Setting | Purpose | Example |
|---|---|---|
| `model` | Main agent (smart) | `anthropic/claude-3.5-haiku` |
| `compact_model` | Context compaction (cheap) | `google/gemini-2.0-flash-001` |

Compaction model can use a different API base and key (`compact_api_base`, `compact_api_key`).

## Tools

| Tool | Description |
|---|---|
| `bash` | Execute shell commands |
| `read_file` | Read files with optional line range |
| `write_file` | Write files |
| `patch_file` | Search/replace edit (saves context!) |
| `list_dir` | List directory contents |
| `http_request` | HTTP GET/POST/PUT/DELETE |

## Context Compaction

Inspired by [OpenAI Codex CLI](https://github.com/openai/codex). When context exceeds threshold:

1. Full history → cheap model with compaction prompt
2. Gets structured summary (progress, decisions, next steps)
3. Rebuilds: `[system_prompt, summary, last_3_messages]`
4. No "summaries of summaries" — always from full history

CLI commands: `/compact` (force), `/stats` (view), `/reset` (clear).

## Dependencies

Only 2 packages: `httpx` + `python-telegram-bot`. That's it.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full development plan.
