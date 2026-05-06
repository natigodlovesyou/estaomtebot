"""
leaderboard/leaderboard_service.py

Handles leaderboard display and user score updates for MegaMind Quiz Bot.
"""
from html import escape
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from db.database import add_score, get_top_scores, get_user

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Ranking Emoji
# ---------------------------------------------------
def get_rank_emoji(position: int) -> str:
    if position == 1:
        return "🥇"
    elif position == 2:
        return "🥈"
    elif position == 3:
        return "🥉"
    else:
        return f"{position}."


# ---------------------------------------------------
# Update User Score
# ---------------------------------------------------
async def update_user_score(user_id: int, score: int):
    """
    Add score to user's total and log the action.
    """
    try:
        add_score(user_id, score)
        logger.info("Score saved | user=%s score=%s", user_id, score)
    except Exception:
        logger.exception("Failed updating score for user %s", user_id)


# ---------------------------------------------------
# Format Leaderboard
# ---------------------------------------------------
def format_leaderboard(rows: list) -> str:
    if not rows:
        return "🏆 Leaderboard is empty.\n\nPlay a quiz to become the first!"

    message = "🏆 <b>MegaMind Leaderboard</b>\n\n"

    for index, row in enumerate(rows, start=1):
        user_id = row["user_id"]
        score = row["total"]

        user = get_user(user_id)

        if user:
            # ✅ FIX: use [] instead of .get()
            username = user["username"] if "username" in user.keys() else None
            first_name = user["first_name"] if "first_name" in user.keys() else None

            if username:
                name = "@" + escape(username)
            else:
                name = escape(first_name if first_name else str(user_id))
        else:
            name = str(user_id)

        rank = get_rank_emoji(index)
        message += f"{rank} {name} — <b>{score} pts</b>\n"

    return message

# ---------------------------------------------------
# Show Leaderboard
# ---------------------------------------------------
async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Displays the top 10 users in the leaderboard.
    """
    query = update.callback_query
    if not query:
        logger.warning("Leaderboard callback without query")
        return

    await query.answer()

    try:
        rows = get_top_scores(limit=10)
        message = format_leaderboard(rows)

        await query.edit_message_text(
            message,
            parse_mode="HTML"
        )

        logger.info("Leaderboard displayed to user=%s", query.from_user.id)

    except Exception:
        logger.exception("Failed to show leaderboard")
        await query.edit_message_text("⚠️ Could not load leaderboard.")