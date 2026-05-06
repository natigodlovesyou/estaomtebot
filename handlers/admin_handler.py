"""
handlers/admin_handler.py

Production-ready admin commands for MegaMind Quiz Bot.

- Broadcast messages to all users
- Fetch bot statistics
- Admin check
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_ID
from db.user_repo import get_all_users, get_total_users, get_total_quizzes
from utils.telegram_utils import safe_send

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Admin Check
# ---------------------------------------------------
def is_admin(user_id: int) -> bool:
    """Check if a user is the bot admin."""
    return user_id == ADMIN_ID


# ---------------------------------------------------
# Broadcast Message
# ---------------------------------------------------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Broadcast a message to all registered users.
    Usage: /broadcast Your message here
    """

    user_id = update.effective_user.id

    if not is_admin(user_id):
        logger.warning("Non-admin attempted broadcast | user=%s", user_id)
        return

    if not context.args:
        await safe_send(context.bot, user_id, "Usage: /broadcast Your message here")
        return

    message = " ".join(context.args)

    try:
        users = get_all_users()  # returns list of user_ids
        logger.info("Broadcasting message to %d users", len(users))

        success_count = 0
        fail_count = 0

        for uid in users:
            success = await _send_with_retry(context.bot, uid, message)
            if success:
                success_count += 1
            else:
                fail_count += 1
                logger.warning("Failed to send broadcast to user %s after retries", uid)
            await asyncio.sleep(0.05)  # small delay to reduce flood risk

        await safe_send(context.bot, user_id, f"✅ Broadcast sent to {success_count} users. Failed: {fail_count}.")

    except Exception:
        logger.exception("Broadcast failed")
        await safe_send(context.bot, user_id, "⚠️ Broadcast failed. Check logs.")


async def _send_with_retry(bot, user_id: int, message: str, max_retries: int = 3) -> bool:
    """Send message with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            success = await safe_send(bot, user_id, message)
            if success:
                return True
        except Exception as e:
            logger.warning("Broadcast attempt %d failed for user %s: %s", attempt + 1, user_id, e)

        if attempt < max_retries - 1:
            delay = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
            await asyncio.sleep(delay)

    return False


# ---------------------------------------------------
# Bot Stats
# ---------------------------------------------------
async def bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send simple bot statistics to admin."""

    user_id = update.effective_user.id

    if not is_admin(user_id):
        logger.warning("Non-admin attempted stats check | user=%s", user_id)
        return

    try:
        total_users = get_total_users()
        total_quizzes = get_total_quizzes()

        stats_message = (
            f"📊 Bot Stats\n\n"
            f"Users registered: {total_users}\n"
            f"Quizzes played: {total_quizzes}"
        )

        await safe_send(context.bot, user_id, stats_message)

    except Exception:
        logger.exception("Failed to fetch bot stats")
        await safe_send(context.bot, user_id, "⚠️ Failed to fetch bot stats.")