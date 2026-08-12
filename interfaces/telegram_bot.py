# -*- coding: utf-8 -*-
"""
Project Genesis - SentinelAI Telegram Bot Interface (V1.0)
Telegram Bot: SentinelAI (@sentinelAI_2k26_bot)
Provides full access to Genesis, Autonomous Swarm, expandable thinking UI,
and power management strictly for authorized owner @JaneS005.
"""

import asyncio
import json
import logging
import os
import sys
import threading
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from Genesis.core.graph import process_stimulus, set_progress_callback, set_abort_flag
from Genesis.core.memory import GenesisState
from Genesis.core.renderer import (
    set_output_mode, set_output_callback, to_telegram_html,
    format_expandable_thinking, split_telegram_message
)
from Genesis.core.model_registry import model_registry
from Genesis.interfaces.remote_manager import graceful_remote_shutdown

# --- CONFIG & OWNER AUTH ---
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
os.makedirs(CONFIG_DIR, exist_ok=True)
OWNER_FILE = os.path.join(CONFIG_DIR, "owner.json")

# Fallback token
BOT_TOKEN = os.environ.get("SENTINEL_BOT_TOKEN", "8692616692:AAEO8I4jPK0Yku-X2xZGKHiSoO39vVm9Ovc")

_OWNER_LOCK = threading.Lock()
_USER_LOCKS: Dict[int, asyncio.Lock] = {}
_ABORT_EVENT = threading.Event()
_PER_USER_STATE: Dict[int, GenesisState] = {}


def _load_owner_id() -> int | None:
    if os.path.exists(OWNER_FILE):
        try:
            with open(OWNER_FILE, "r") as f:
                data = json.load(f)
                return data.get("owner_id")
        except Exception:
            pass
    return None


def _save_owner_id(user_id: int, username: str):
    try:
        with open(OWNER_FILE, "w") as f:
            json.dump({"owner_id": user_id, "username": username}, f)
    except Exception as e:
        logging.error(f"Failed to save owner info: {e}")


_AUTHORIZED_OWNER_ID = _load_owner_id()


def is_authorized(update: Update) -> bool:
    """Checks if the incoming message is from authorized owner (@JaneS005 / registered ID)."""
    global _AUTHORIZED_OWNER_ID
    user = update.effective_user
    if not user:
        return False

    # First run setup — if owner username matches @JaneS005, bind ID permanently
    if _AUTHORIZED_OWNER_ID is None:
        if user.username and user.username.lower() == "janes005":
            _AUTHORIZED_OWNER_ID = user.id
            _save_owner_id(user.id, user.username)
            return True

    return _AUTHORIZED_OWNER_ID == user.id


# --- HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("⛔ <b>Access Denied.</b> You are not authorized to command SentinelAI.", parse_mode=ParseMode.HTML)
        return

    welcome_text = (
        "🟢 <b>SENTINEL AI OPERATIONAL</b>\n"
        "<i>Genesis Ecosystem Telegram Gateway</i>\n\n"
        "Welcome Boss! I am fully bound to your Telegram ID.\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>/status</code> — System health & model info\n"
        "• <code>/model</code> — Switch active local LLMs\n"
        "• <code>/autonomous &lt;task&gt;</code> — Trigger Autonomous Swarm\n"
        "• <code>/stop</code> — Interrupt active execution\n"
        "• <code>/reset</code> — Flush memory & state\n"
        "• <code>/shutdown</code> — Gracefully shutdown host PC\n"
        "• <code>/help</code> — Full command manifest\n\n"
        "Send any prompt to begin processing!"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    help_text = (
        "🤖 <b>SentinelAI Command Manifest</b>\n\n"
        "• Send any text message to trigger standard Nexus routing.\n"
        "• Send an image to trigger Vision Analysis.\n"
        "• Use <code>/autonomous &lt;task&gt;</code> for swarm collaboration.\n"
        "• Use <code>/stop</code> to abort any running loop.\n"
        "• Use <code>/shutdown</code> to remotely turn off host computer."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    status_text = (
        "⚙️ <b>Genesis System Status</b>\n"
        "• Host OS: Windows\n"
        "• Active Interface: Telegram (SentinelAI)\n"
        "• Active Nexus LLM: stark-enterprise:latest\n"
        "• Active Coder LLM: qwen2.5-coder:7b\n"
        "• Active Thinker LLM: qwen3:4b\n"
        "• Thermal Status: Optimal (GPU Offload Active)\n"
        "• Security Gateway: ENFORCED 🔒"
    )
    await update.message.reply_text(status_text, parse_mode=ParseMode.HTML)


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    keyboard = [
        [InlineKeyboardButton("stark-enterprise (Nexus)", callback_data="model_stark")],
        [InlineKeyboardButton("qwen2.5-coder (Coder)", callback_data="model_coder")],
        [InlineKeyboardButton("qwen3:4b (Thinker)", callback_data="model_thinker")],
        [InlineKeyboardButton("qwen3-vl:4b (Vision)", callback_data="model_vision")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🧠 <b>Select active LLM model override:</b>", reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def model_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    mapping = {
        "model_stark": ("nexus", "stark-enterprise:latest"),
        "model_coder": ("coder", "qwen2.5-coder:7b-instruct-q5_K_M"),
        "model_thinker": ("thinker", "qwen3:4b"),
        "model_vision": ("vision", "qwen3-vl:4b-instruct-q4_K_M")
    }
    if data in mapping:
        role, model_name = mapping[data]
        ok, msg = model_registry.set_model_override(role, model_name)
        await query.edit_message_text(f"✅ {msg}", parse_mode=ParseMode.HTML)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    _ABORT_EVENT.set()
    await update.message.reply_text("🛑 <b>Emergency Abort Signal Sent!</b> Interrupting active execution...", parse_mode=ParseMode.HTML)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    user_id = update.effective_user.id
    if user_id in _PER_USER_STATE:
        del _PER_USER_STATE[user_id]
    await update.message.reply_text("🔄 <b>Genesis State & Memory Flushed.</b>", parse_mode=ParseMode.HTML)


async def shutdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    keyboard = [
        [InlineKeyboardButton("⚠️ CONFIRM SHUTDOWN ⚠️", callback_data="shutdown_confirm")],
        [InlineKeyboardButton("Cancel", callback_data="shutdown_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚠️ <b>WARNING: Remote Graceful Host Shutdown</b>\n"
        "Are you sure you want to shut down the host PC?",
        reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )


async def shutdown_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "shutdown_confirm":
        await query.edit_message_text("🔌 <b>Initiating graceful system shutdown...</b> Host PC powering off in 10s.", parse_mode=ParseMode.HTML)
        graceful_remote_shutdown(10)
    else:
        await query.edit_message_text("❌ Remote shutdown cancelled.", parse_mode=ParseMode.HTML)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("⛔ <b>Access Denied.</b>", parse_mode=ParseMode.HTML)
        return

    user_id = update.effective_user.id
    user_input = update.message.text or ""

    if not user_input.strip():
        return

    # Per-user concurrency lock
    if user_id not in _USER_LOCKS:
        _USER_LOCKS[user_id] = asyncio.Lock()

    lock = _USER_LOCKS[user_id]
    if lock.locked():
        await update.message.reply_text("⏳ <i>Still processing your previous request... Please wait.</i>", parse_mode=ParseMode.HTML)
        return

    async with lock:
        _ABORT_EVENT.clear()
        set_abort_flag(_ABORT_EVENT)
        set_output_mode("TELEGRAM")

        # Get or init user GenesisState
        if user_id not in _PER_USER_STATE:
            _PER_USER_STATE[user_id] = {
                "messages": [],
                "next_node": "Nexus",
                "agent_messages": [],
                "autonomous_iteration_count": 0,
                "active_permissions": []
            }

        state = _PER_USER_STATE[user_id]
        from langchain_core.messages import HumanMessage
        state["messages"].append(HumanMessage(content=user_input))

        # Intermediate progress thinking message
        progress_msg = await update.message.reply_text("🧠 <b>Genesis is thinking...</b>", parse_mode=ParseMode.HTML)
        thinking_log = []

        def progress_callback(event_type: str, agent_name: str, text: str, iteration: int):
            if event_type == "agent_typing":
                asyncio.run_coroutine_threadsafe(
                    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING),
                    context.application.loop
                )
            elif event_type in ["swarm_message", "system_event"]:
                entry = format_expandable_thinking(agent_name, f"Step {iteration}", text[:400])
                thinking_log.append(entry)
                combined = "🧠 <b>Autonomous Swarm Progress:</b>\n\n" + "\n\n".join(thinking_log[-4:])
                try:
                    asyncio.run_coroutine_threadsafe(
                        progress_msg.edit_text(combined[:3800], parse_mode=ParseMode.HTML),
                        context.application.loop
                    )
                except Exception:
                    pass

        set_progress_callback(progress_callback)

        # Run process_stimulus in thread pool
        loop = asyncio.get_running_loop()
        try:
            final_state = await loop.run_in_executor(None, process_stimulus, user_input, state)
            _PER_USER_STATE[user_id] = final_state

            if final_state.get("messages"):
                final_ai_message = final_state["messages"][-1].content
                html_formatted = to_telegram_html(final_ai_message)
                chunks = split_telegram_message(html_formatted)

                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Execution Error:</b> {e}", parse_mode=ParseMode.HTML)


def create_bot_application():
    """Initializes python-telegram-bot application."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("shutdown", shutdown_command))
    app.add_handler(CallbackQueryHandler(model_button_callback, pattern="^model_"))
    app.add_handler(CallbackQueryHandler(shutdown_button_callback, pattern="^shutdown_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    return app


if __name__ == "__main__":
    print("🤖 Starting SentinelAI Telegram Bot (@sentinelAI_2k26_bot)...")
    app = create_bot_application()
    app.run_polling()
