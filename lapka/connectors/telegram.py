"""Telegram connector — bot interface for Lapka."""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ..agent import Agent
from ..config import Config

log = logging.getLogger("lapka.telegram")

# Per-user agents (each user gets their own context)
_agents: dict[int, Agent] = {}
_config: Config | None = None


def _get_agent(user_id: int) -> Agent:
    if user_id not in _agents:
        _agents[user_id] = Agent(_config)
    return _agents[user_id]


def _is_allowed(user_id: int) -> bool:
    if not _config.telegram_allowed_users:
        return True  # No allowlist = allow all
    return user_id in _config.telegram_allowed_users


async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        await update.message.reply_text("⛔ Access denied.")
        return

    await update.message.reply_text(
        "🐾 *Lapka* — Ultra-lightweight AI Agent\n\n"
        "Commands:\n"
        "/reset — Clear conversation\n"
        "/stats — Context stats\n"
        "/compact — Force compaction\n"
        "/model — Current models\n"
        "/setmodel NAME — Switch main model\n"
        "/setmodel compact NAME — Switch compact model",
        parse_mode="Markdown",
    )


async def _cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        return

    agent = _get_agent(user_id)
    agent.reset()
    await update.message.reply_text("↺ Context reset.")


async def _cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        return

    agent = _get_agent(user_id)
    stats = agent.stats
    text = (
        f"📊 Context stats:\n"
        f"Messages: {stats['history_messages']}\n"
        f"Tokens (actual): {stats['actual_prompt_tokens']}\n"
        f"Compactions: {stats['compaction_count']}\n"
        f"Total tokens used: {stats['total_tokens_used']}"
    )
    await update.message.reply_text(text)


async def _cmd_compact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        return

    agent = _get_agent(user_id)
    await update.message.reply_text("🗜️ Compacting context...")
    await agent.ctx.compact(agent.compact_llm)
    await update.message.reply_text(f"✓ Done. Messages: {agent.stats['history_messages']}")


async def _cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        return

    text = (
        f"🤖 Main: `{_config.main.model}`\n"
        f"🗜️ Compact: `{_config.compact_profile.model}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def _cmd_setmodel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage:\n`/setmodel MODEL` — set main\n`/setmodel compact MODEL` — set compact",
            parse_mode="Markdown",
        )
        return

    if args[0] == "compact" and len(args) > 1:
        new_model = args[1]
        _config.compact.model = new_model
        # Recreate compact LLM for existing agents
        from ..llm import LLMClient
        for agent in _agents.values():
            agent.compact_llm = LLMClient(_config.compact_profile)
        await update.message.reply_text(f"🗜️ Compact → `{new_model}`", parse_mode="Markdown")
    else:
        new_model = args[0]
        _config.main.model = new_model
        # Recreate main LLM for existing agents
        from ..llm import LLMClient
        for agent in _agents.values():
            agent.main_llm = LLMClient(_config.main)
        await update.message.reply_text(f"🤖 Main → `{new_model}`", parse_mode="Markdown")


async def _safe_reply(message, text: str) -> None:
    """Send with Markdown, fallback to plain text on parse errors."""
    try:
        await message.reply_text(text, parse_mode="Markdown")
    except Exception:
        await message.reply_text(text)


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        await update.message.reply_text("⛔ Access denied.")
        return

    text = update.message.text
    if not text:
        return

    agent = _get_agent(user_id)

    # Show typing indicator
    await update.message.chat.send_action("typing")

    # Accumulate tool outputs for a status message
    tool_lines: list[str] = []

    async def on_output(msg: str) -> None:
        tool_lines.append(msg)
        # Re-send typing to keep indicator alive
        try:
            await update.message.chat.send_action("typing")
        except Exception:
            pass

    try:
        response = await agent.run(text, on_output=on_output)

        # Build response text
        parts = []
        if tool_lines:
            tools_summary = "\n".join(tool_lines[-5:])  # Last 5 tool actions
            parts.append(f"```\n{tools_summary}\n```")
        parts.append(response)

        full_response = "\n\n".join(parts)

        # Telegram has a 4096 char limit
        if len(full_response) > 4000:
            full_response = full_response[:4000] + "\n... (truncated)"

        await _safe_reply(update.message, full_response)

    except Exception as e:
        log.exception("Error processing message from user %d", user_id)
        await update.message.reply_text(f"❌ Error: {e}")


async def _handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages — download and send to vision model."""
    user_id = update.effective_user.id
    if not _is_allowed(user_id):
        await update.message.reply_text("⛔ Access denied.")
        return

    agent = _get_agent(user_id)
    await update.message.chat.send_action("typing")

    # Get largest photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    data = await file.download_as_bytearray()
    img_b64 = base64.b64encode(data).decode()

    caption = update.message.caption or ""
    tool_lines: list[str] = []

    async def on_output(msg: str) -> None:
        tool_lines.append(msg)
        try:
            await update.message.chat.send_action("typing")
        except Exception:
            pass

    try:
        response = await agent.run(caption, on_output=on_output, image_b64=img_b64)

        parts = []
        if tool_lines:
            summary = "\n".join(tool_lines[-5:])
            parts.append(f"```\n{summary}\n```")
        parts.append(response)
        full_response = "\n\n".join(parts)
        if len(full_response) > 4000:
            full_response = full_response[:4000] + "\n... (truncated)"
        await _safe_reply(update.message, full_response)
    except Exception as e:
        log.exception("Error processing photo from user %d", user_id)
        await update.message.reply_text(f"❌ Error: {e}")


async def run_telegram(config: Config) -> None:
    """Start the Telegram bot."""
    global _config
    _config = config

    if not config.telegram_bot_token:
        raise ValueError(
            "No Telegram bot token. Set telegram_bot_token in config or LAPKA_TELEGRAM_TOKEN env var."
        )

    app = Application.builder().token(config.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("reset", _cmd_reset))
    app.add_handler(CommandHandler("stats", _cmd_stats))
    app.add_handler(CommandHandler("compact", _cmd_compact))
    app.add_handler(CommandHandler("model", _cmd_model))
    app.add_handler(CommandHandler("setmodel", _cmd_setmodel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, _handle_photo))

    log.info("Starting Telegram bot...")
    print("🐾 Lapka Telegram bot started. Waiting for messages...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Run until interrupted
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

        # Cleanup agents
        for agent in _agents.values():
            await agent.close()

        print("\n🐾 Lapka Telegram bot stopped.")
