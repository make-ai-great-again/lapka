"""Lapka entry point — run as `python -m lapka` or `lapka`."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from .config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="🐾 Lapka — Ultra-lightweight AI Agent",
    )
    parser.add_argument(
        "--telegram", action="store_true",
        help="Run as a Telegram bot",
    )
    parser.add_argument(
        "--cli", action="store_true", default=True,
        help="Run in interactive CLI mode (default)",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to config JSON file (default: ~/.lapka/config.json)",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Override main model",
    )
    parser.add_argument(
        "--api-base", type=str, default=None,
        help="Override API base URL",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load config
    config = load_config(args.config)

    # Apply CLI overrides
    if args.model:
        config.main.model = args.model
    if args.api_base:
        config.main.api_base = args.api_base

    # Validate
    if not config.main.api_key:
        print("❌ No API key configured!")
        print("   Set LAPKA_API_KEY env var, or add api_key to ~/.lapka/config.json")
        sys.exit(1)

    # Run
    if args.telegram:
        from .connectors.telegram import run_telegram
        asyncio.run(run_telegram(config))
    else:
        from .connectors.cli import run_cli
        asyncio.run(run_cli(config))


if __name__ == "__main__":
    main()
