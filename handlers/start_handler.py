"""
handlers/start_handler.py

Handles the /start command and main menu for MegaMind Quiz Bot.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import COMMUNITY_INVITE, COMMUNITY_CHAT_ID
from db.user_repo import register_user
from quiz.quiz_engine import stop_quiz, resume_quiz
from state.models import PlayerStats
from state.storage import get_user_state, update_user_state
from utils.telegram_utils import check_user_member_of_community

logger = logging.getLogger(__name__)


# -----------------------------
# Build Main Menu
# -----------------------------

def build_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🧠 Start Quiz", callback_data="main_start")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="main_leaderboard")],
        [
            InlineKeyboardButton("📊 My Stats", callback_data="main_stats"),
            InlineKeyboardButton("📄 Report Card", callback_data="main_report"),
        ],
        [InlineKeyboardButton("🎁 Invite Friends", callback_data="main_invite")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def ensure_player_profile(user_id: int):
    user_state = get_user_state(user_id)

    if user_id not in user_state.players:
        user_state.players[user_id] = PlayerStats(user_id=user_id)
        await update_user_state(user_id, user_state)

    return user_state


# -----------------------------
# /start Handler
# -----------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command:
    1. Registers the user
    2. Processes referral code (if any)
    3. Checks community membership
    4. Sends welcome message and main menu
    """

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        logger.warning("/start called without user or message")
        return

    try:
        # -------------------------------------------------
        # 1️⃣ Check if user is new
        # -------------------------------------------------
        from db.user_repo import get_user
        is_new_user = get_user(user.id) is None

        # -------------------------------------------------
        # 2️⃣ Process Referral (only for new users)
        # -------------------------------------------------
        if context.args and is_new_user:
            referral_code = context.args[0]

            from referrals.referral_system import process_referral_start

            await process_referral_start(user.id, referral_code, context)

            logger.info(
                "Referral processed | user_id=%s | code=%s",
                user.id,
                referral_code
            )

        # -------------------------------------------------
        # 3️⃣ Register User
        # -------------------------------------------------
        register_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )

        await ensure_player_profile(user.id)

        logger.info("User registered | user_id=%s", user.id)

        # -------------------------------------------------
        # 3️⃣ Check Community Membership
        # -------------------------------------------------
        joined = await check_user_member_of_community(
            context.bot,
            user.id,
            COMMUNITY_CHAT_ID
        )

        if not joined:

            join_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Community", url=COMMUNITY_INVITE)],
                [InlineKeyboardButton("✅ I Joined", callback_data="joined_confirm")]
            ])

            await message.reply_text(
                "👋 *Welcome to MegaMind Academy!*\n\n"
                "Before using the quiz bot, please join our community.\n"
                "After joining, press *I Joined*.",
                parse_mode="Markdown",
                reply_markup=join_keyboard,
            )

            return

        # -------------------------------------------------
        # 4️⃣ Send Welcome + Main Menu
        # -------------------------------------------------
        await message.reply_text(
            f"👋 Welcome *{user.first_name}*!\n\n"
            "🧠 *MegaMind Academy Quiz Bot*\n\n"
            "Choose an option below to begin:",
            parse_mode="Markdown",
            reply_markup=build_main_menu(),
        )

        logger.info("Start message sent | user_id=%s", user.id)

    except Exception:
        logger.exception("Error in /start handler")

        await message.reply_text(
            "⚠️ Something went wrong while starting the bot.\n"
            "Please try again later."
        )


# -----------------------------
# /help Handler
# -----------------------------
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        "🧠 *MegaMind Quiz Bot Help*\n\n"
        "Use /start to open the main menu.\n"
        "Use /stop to cancel an active quiz.\n"
        "Use /resume to continue an interrupted quiz.\n"
        "You can also use the buttons to view stats, leaderboard, and invite friends.",
        parse_mode="Markdown",
        reply_markup=build_main_menu(),
    )


# -----------------------------
# /stop Handler
# -----------------------------
async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_quiz(update, context)


# -----------------------------
# /resume Handler
# -----------------------------
async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await resume_quiz(update, context)
