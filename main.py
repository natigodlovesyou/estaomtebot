import asyncio
import logging
import os
import signal
import threading

from flask import Flask
from logging.handlers import RotatingFileHandler
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    ContextTypes,
)

# configuration
from config import BOT_TOKEN, LOG_FILE, LOG_LEVEL

# database initialization
from db.database import init_db

# handlers
from handlers.start_handler import cmd_start, cmd_help, cmd_stop, cmd_resume
from handlers.callback_handler import callback_router
from handlers.poll_handler import handle_poll_answer
from handlers.admin_handler import broadcast, bot_stats

# state saving
from state.storage import (
    persist_all,
    load_bot_state,
    start_periodic_save,
    stop_periodic_save,
)

# --------------------------------------------------
# Logging Setup
# --------------------------------------------------

logger = logging.getLogger("megamind_bot")
logger.setLevel(LOG_LEVEL)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler with rotation
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
)
file_handler.setLevel(LOG_LEVEL)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

APP: Optional[Application] = None

# --------------------------------------------------
# Flask Web Server (for Render)
# --------------------------------------------------

web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "MegaMind Quiz Bot is running!"


def run_web_server():
    port = int(os.environ.get("PORT", 10000))

    logger.info(f"Starting Flask web server on port {port}")

    web_app.run(
        host="0.0.0.0",
        port=port,
    )


# --------------------------------------------------
# Global Error Handler
# --------------------------------------------------

async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    """Logs all exceptions globally"""
    logger.error(
        "Exception while handling update: %s",
        update,
        exc_info=context.error,
    )


# --------------------------------------------------
# Graceful Shutdown
# --------------------------------------------------

is_shutting_down = False


async def shutdown():
    global is_shutting_down

    if is_shutting_down:
        return

    is_shutting_down = True

    logger.warning("Bot shutting down...")

    try:
        logger.info("Stopping periodic save...")

        await stop_periodic_save()

        logger.info("Persisting bot state...")

        await asyncio.to_thread(persist_all)

        logger.info("State saved successfully")

    except Exception:
        logger.exception("Failed to persist bot state")

    if APP:
        await APP.stop()
        await APP.shutdown()

    logger.info("Shutdown complete")


# --------------------------------------------------
# OS Signal Handler
# --------------------------------------------------

def handle_signal(signum, frame):
    logger.warning(f"Received signal {signum}, scheduling shutdown...")

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(shutdown())

    except RuntimeError:
        asyncio.run(shutdown())


def register_signals():
    """Register OS signals for graceful shutdown"""

    signal.signal(signal.SIGINT, handle_signal)

    try:
        signal.signal(signal.SIGTERM, handle_signal)

    except AttributeError:
        logger.info("SIGTERM not supported on this OS")


# --------------------------------------------------
# Register Bot Handlers
# --------------------------------------------------

def register_handlers(app: Application):
    logger.info("Registering handlers...")

    # user commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("resume", cmd_resume))

    # admin commands
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", bot_stats))

    # button callbacks
    app.add_handler(CallbackQueryHandler(callback_router))

    # quiz answers
    app.add_handler(PollAnswerHandler(handle_poll_answer))

    # global error handler
    app.add_error_handler(error_handler)

    logger.info("Handlers registered successfully")


# --------------------------------------------------
# Main Entry
# --------------------------------------------------

async def main_async():
    global APP

    logger.info("Starting MegaMind Quiz Bot...")

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing in config.py")

    # Create database tables
    # Delete corrupted database if exists
    init_db()

    # Restore saved in-memory state
    load_bot_state()

    APP = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(False)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    register_handlers(APP)
    register_signals()

    # Start periodic state saving
    await start_periodic_save()

    logger.info("Bot is now running with polling...")

    # Initialize bot
    await APP.initialize()
    await APP.start()
    await APP.bot.initialize()

    # Start polling
    await APP.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )

    # Keep bot alive forever
    await asyncio.Event().wait()


def main():
    # Start Flask web server in background thread
    threading.Thread(
        target=run_web_server,
        daemon=True
    ).start()

    # Start Telegram bot
    asyncio.run(main_async())


# --------------------------------------------------

if __name__ == "__main__":
    main()
    
