import json
import logging
import tempfile
import os
import signal
import atexit
from pathlib import Path
from typing import Dict

from config import STATE_FILE
from state.models import BotState
import asyncio

STATE_LOCK = asyncio.Lock()

logger = logging.getLogger(__name__)

STATE_PATH = Path(STATE_FILE)

# ---------------------------------------------------
# MULTI-USER STATE STORE (IMPORTANT FIX)
# ---------------------------------------------------

USER_STATES: Dict[int, BotState] = {}

# ---------------------------------------------------
# CRASH PROTECTION
# ---------------------------------------------------
SAVE_INTERVAL = 300  # Save every 5 minutes
_save_task = None

def _setup_crash_protection():
    """Setup signal handlers and atexit for crash protection."""
    def signal_handler(signum, frame):
        logger.info("Received signal %s, saving state before exit", signum)
        save_bot_state()
        # Use sys.exit instead of os._exit for cleaner shutdown
        import sys
        sys.exit(0)

    # Register signal handlers for common termination signals
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Register atexit handler as backup
    atexit.register(save_bot_state)

    logger.info("Crash protection enabled")

async def _periodic_save():
    """Periodically save state to prevent data loss."""
    while True:
        await asyncio.sleep(SAVE_INTERVAL)
        try:
            async with STATE_LOCK:
                await asyncio.to_thread(save_bot_state)
            logger.debug("Periodic state save completed")
        except Exception:
            logger.exception("Periodic state save failed")

def load_bot_state() -> Dict[int, BotState]:
    global USER_STATES

    if not STATE_PATH.exists():
        logger.info("State file not found. Starting fresh.")
        USER_STATES = {}
        _setup_crash_protection()
        return USER_STATES

    try:
        with STATE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)

        USER_STATES = {
            int(user_id): BotState.from_dict(state)
            for user_id, state in data.items()
        }

        logger.info("Bot state loaded for %d users", len(USER_STATES))
        _setup_crash_protection()

    except Exception:
        logger.exception("Failed to load state. Resetting.")
        USER_STATES = {}
        _setup_crash_protection()

    return USER_STATES
def save_bot_state():
    global USER_STATES

    temp_name = None

    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            dir=STATE_PATH.parent,
            encoding="utf-8"
        ) as tmp:

            json.dump(
                {
                    str(user_id): state.to_dict()
                    for user_id, state in USER_STATES.items()
                },
                tmp,
                indent=2,
                ensure_ascii=False
            )

            temp_name = tmp.name

        os.replace(temp_name, STATE_PATH)

        logger.info("State saved (%d users)", len(USER_STATES))

    except Exception:
        logger.exception("Failed to save bot state")

        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)
def get_user_state(user_id: int) -> BotState:
    global USER_STATES

    if user_id not in USER_STATES:
        USER_STATES[user_id] = BotState()

    return USER_STATES[user_id]

async def update_user_state(user_id: int, state: BotState):
    global USER_STATES

    async with STATE_LOCK:
        USER_STATES[user_id] = state
        await asyncio.to_thread(save_bot_state)

    return USER_STATES[user_id]

async def update_user_state(user_id: int, state: BotState):
    global USER_STATES

    async with STATE_LOCK:
        USER_STATES[user_id] = state
        await asyncio.to_thread(save_bot_state)

def persist_all():
    save_bot_state()

async def start_periodic_save():
    """Start the periodic save task."""
    global _save_task
    if _save_task is None or _save_task.done():
        _save_task = asyncio.create_task(_periodic_save())
        logger.info("Periodic state saving started")

async def stop_periodic_save():
    """Stop the periodic save task."""
    global _save_task
    if _save_task and not _save_task.done():
        _save_task.cancel()
        try:
            await _save_task
        except asyncio.CancelledError:
            pass
        logger.info("Periodic state saving stopped")

def clear_state():
    """Clear all user states. USE WITH CAUTION!"""
    global USER_STATES
    USER_STATES = {}
    save_bot_state()
    print("✅ State cleared successfully!")