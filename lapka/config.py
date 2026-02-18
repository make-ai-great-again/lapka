"""Configuration for Lapka agent."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_CONFIG_DIR = Path.home() / ".lapka"
_DEFAULT_CONFIG_FILE = _DEFAULT_CONFIG_DIR / "config.json"


@dataclass
class LLMProfile:
    """Connection profile for an LLM endpoint."""
    api_base: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    model: str = "google/gemini-2.0-flash-001"


@dataclass
class Config:
    # Main LLM (smart model for the agent)
    main: LLMProfile = field(default_factory=LLMProfile)

    # Compaction LLM (cheap model for context compression)
    compact: LLMProfile = field(default_factory=lambda: LLMProfile(
        model="qwen/qwen3-235b-a22b-2507",
    ))

    # Telegram
    telegram_bot_token: str = ""
    telegram_allowed_users: list[int] = field(default_factory=list)

    # Context
    max_context_tokens: int = 4000
    compact_threshold: float = 0.8  # compact when at 80% of max

    # Execution
    working_directory: str = "."
    max_tool_iterations: int = 25
    command_timeout: int = 30

    # Safety
    blocked_commands: list[str] = field(default_factory=lambda: [
        "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){:|:&};:",
        "chmod -R 777 /", "shutdown", "reboot", "init 0", "init 6",
    ])

    @property
    def compact_profile(self) -> LLMProfile:
        """Return compact profile with main's API key/base as fallback."""
        p = self.compact
        if not p.api_key:
            p.api_key = self.main.api_key
        if p.api_base == "https://openrouter.ai/api/v1" and self.main.api_base != p.api_base:
            p.api_base = self.main.api_base
        return p

    @property
    def config_dir(self) -> Path:
        return _DEFAULT_CONFIG_DIR

    def ensure_dirs(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        (self.config_dir / "sessions").mkdir(exist_ok=True)


def load_config(path: str | None = None) -> Config:
    """Load config from JSON file + env vars. Env vars take priority."""
    cfg = Config()
    config_path = Path(path) if path else _DEFAULT_CONFIG_FILE

    # Load from file
    if config_path.exists():
        with open(config_path) as f:
            data = json.load(f)

        # Main profile
        cfg.main.api_base = data.get("api_base", cfg.main.api_base)
        cfg.main.api_key = data.get("api_key", cfg.main.api_key)
        cfg.main.model = data.get("model", cfg.main.model)

        # Compact profile
        compact_model = data.get("compact_model")
        compact_base = data.get("compact_api_base")
        compact_key = data.get("compact_api_key")
        if compact_model or compact_base:
            cfg.compact = LLMProfile(
                api_base=compact_base or cfg.main.api_base,
                api_key=compact_key or cfg.main.api_key,
                model=compact_model or cfg.main.model,
            )

        # Other settings
        cfg.telegram_bot_token = data.get("telegram_bot_token", cfg.telegram_bot_token)
        cfg.telegram_allowed_users = data.get("telegram_allowed_users", cfg.telegram_allowed_users)
        cfg.max_context_tokens = data.get("max_context_tokens", cfg.max_context_tokens)
        cfg.compact_threshold = data.get("compact_threshold", cfg.compact_threshold)
        cfg.working_directory = data.get("working_directory", cfg.working_directory)
        cfg.max_tool_iterations = data.get("max_tool_iterations", cfg.max_tool_iterations)
        cfg.command_timeout = data.get("command_timeout", cfg.command_timeout)

        blocked = data.get("blocked_commands")
        if blocked is not None:
            cfg.blocked_commands = blocked

    # Env var overrides (highest priority)
    cfg.main.api_key = os.environ.get("LAPKA_API_KEY", cfg.main.api_key)
    cfg.main.api_base = os.environ.get("LAPKA_API_BASE", cfg.main.api_base)
    cfg.main.model = os.environ.get("LAPKA_MODEL", cfg.main.model)
    cfg.compact.model = os.environ.get("LAPKA_COMPACT_MODEL", cfg.compact.model)
    cfg.telegram_bot_token = os.environ.get("LAPKA_TELEGRAM_TOKEN", cfg.telegram_bot_token)

    if not cfg.main.api_key:
        # Try OPENROUTER_API_KEY as fallback
        cfg.main.api_key = os.environ.get("OPENROUTER_API_KEY", "")

    cfg.ensure_dirs()
    return cfg
