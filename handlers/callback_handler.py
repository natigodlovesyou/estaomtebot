import logging
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest, NetworkError, TimedOut

from quiz.quiz_engine import start_quiz_flow
from state.storage import get_user_state
from quiz.report_generator import build_study_report_message, format_list
from quiz.learning_tracker import get_user_insights
from leaderboard.leaderboard import show_leaderboard
from referrals.referral_system import send_invite_message
from handlers.start_handler import build_main_menu
from config import COMMUNITY_CHAT_ID, COMMUNITY_INVITE, ADMIN_ID
from utils.telegram_utils import check_user_member_of_community

from .ui_builder import subject_menu, grade_menu, unit_menu, confirm_menu, quiz_options_menu
from .flow_service import set_subject, set_grade, set_unit, set_mode, reset_all, is_ready_to_start
from .data_service import get_subject_label, get_grade_label, get_units, _decode_file_key, format_file_label

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# GLOBAL SAFE CALL WRAPPER (IMPORTANT FIX)
# ---------------------------------------------------

async def tg_safe(call, retries=3, delay=1):
    for _ in range(retries):
        try:
            return await call()
        except (NetworkError, TimedOut) as e:
            logger.warning(f"Telegram API retrying due to: {e}")
            await asyncio.sleep(delay)
    return None


# ---------------------------------------------------
# SAFE EDIT MESSAGE
# ---------------------------------------------------

async def safe_edit(query, text, reply_markup=None, **kwargs):
    try:
        await tg_safe(
            lambda: query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                **kwargs
            )
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            logger.debug("Safe edit skipped: message not modified")
            return None
        raise


# ---------------------------------------------------
# SAFE ANSWER CALLBACK
# ---------------------------------------------------

async def safe_answer(query, text=None, alert=False):
    await tg_safe(
        lambda: query.answer(text=text, show_alert=alert)
    )


# ---------------------------------------------------
# COMMUNITY MEMBERSHIP CHECK
# ---------------------------------------------------

async def ensure_membership(query, context):
    user_id = query.from_user.id
    joined = await check_user_member_of_community(
        context.bot,
        user_id,
        COMMUNITY_CHAT_ID
    )

    if not joined:
        join_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Community", url=COMMUNITY_INVITE)],
            [InlineKeyboardButton("✅ I Joined", callback_data="joined_confirm")]
        ])

        await safe_edit(
            query,
            "👋 Please join our community before starting quizzes.",
            join_keyboard
        )
        return False

    return True


# ---------------------------------------------------
# MAIN ROUTER
# ---------------------------------------------------

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    data = query.data

    # ALWAYS SAFE FIRST
    await safe_answer(query)

    # Check invite requirement (skip for admin)
    user_id = update.effective_user.id
    user_state = get_user_state(user_id)
    player = user_state.players.get(user_id)
    if player and player.requires_invites and user_id != ADMIN_ID:
        if data == "main_invite":
            await tg_safe(lambda: send_invite_message(update, context))
            return

        if data == "referral_stats":
            from referrals.referral_system import send_referral_stats
            await tg_safe(lambda: send_referral_stats(update, context))
            return

        await safe_edit(
            query,
            "🎁 We’re here to help you unlock full access!\n\n"
            "Invite 2 friends and earn 10 bonus points for each successful referral.\n\n"
            "Tap Invite Friends so we can give you your personal referral link.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 Invite Friends", callback_data="main_invite")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back_menu")]
            ])
        )
        return

    try:

        # ---------------- MAIN MENU ----------------

        if data == "main_start":
            if not await ensure_membership(query, context):
                return

            await safe_edit(
                query,
                "🧠 MegaMind Quiz\n\nSelect a subject:",
                subject_menu()
            )
            return

        if data == "main_leaderboard":
            await tg_safe(lambda: show_leaderboard(update, context))
            return

        if data == "main_report":
            user_id = update.effective_user.id
            user_state = get_user_state(user_id)
            session = user_state.sessions.get(user_id)

            insights = get_user_insights(user_id)

            if not session or not session.active:
                # Show overall learning insights
                weak = insights.get("weak_topics", [])
                strong = insights.get("strong_topics", [])
                neutral = insights.get("neutral_topics", [])

                if not weak and not strong and not neutral:
                    report = "📊 No learning data yet. Start taking quizzes to generate insights!"
                else:
                    report = f"""
📊 *Your Learning Insights*

⚠️ *Weak Topics*
{format_list(weak)}

📘 *Needs Practice*
{format_list(neutral)}

✅ *Strong Topics*
{format_list(strong)}

💡 *Tip:* Focus on weak topics for better improvement!
"""
                await safe_edit(
                    query,
                    report,
                    build_main_menu(),
                    parse_mode="Markdown"
                )
                return

            # Show session report
            report = build_study_report_message(user_id, session, insights)

            await safe_edit(
                query,
                report,
                build_main_menu(),
                parse_mode="Markdown"
            )
            return

        if data == "joined_confirm":
            user_id = update.effective_user.id
            joined = await check_user_member_of_community(
                context.bot,
                user_id,
                COMMUNITY_CHAT_ID
            )

            if not joined:
                join_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Join Community", url=COMMUNITY_INVITE)],
                    [InlineKeyboardButton("✅ I Joined", callback_data="joined_confirm")]
                ])

                await safe_edit(
                    query,
                    "⚠️ We still couldn't verify your membership. Please join the community and press I Joined again.",
                    join_keyboard
                )
                return

            await safe_edit(
                query,
                "✅ Thanks for joining! Here is the main menu:",
                build_main_menu()
            )
            return

        if data == "main_stats":
            user_id = update.effective_user.id

            state = get_user_state(user_id)
            player = state.players.get(user_id)

            # fallback values
            total_score = 0
            quizzes_taken = 0
            correct_answers = 0

            if player:
                total_score = player.total_score
                quizzes_taken = player.quizzes_taken
                correct_answers = player.correct_answers

            text = (
                "📊 Your Stats\n\n"
                f"🏆 Total Score: {total_score}\n"
                f"🎯 Quizzes Taken: {quizzes_taken}\n"
                f"✅ Correct Answers: {correct_answers}"
            )

            await safe_edit(query, text, build_main_menu())
            return

        if data == "main_invite":
            await tg_safe(lambda: send_invite_message(update, context))
            return

        if data == "referral_stats":
            from referrals.referral_system import send_referral_stats
            await tg_safe(lambda: send_referral_stats(update, context))
            return

        # ---------------- SUBJECT ----------------

        if data.startswith("subject_"):
            subject = data.split("_", 1)[1]
            set_subject(context, subject)

            await safe_edit(
                query,
                f"{get_subject_label(subject)} selected\n\nSelect Grade:",
                grade_menu()
            )
            return

        # ---------------- GRADE ----------------

        if data.startswith("grade_"):
            grade = data.split("_", 1)[1]
            set_grade(context, grade)

            subject = context.user_data.get("subject")
            if not subject:
                await safe_answer(query, "⚠️ Select subject first", alert=True)
                return

            units = get_units(grade, subject)

            await safe_edit(
                query,
                f"{get_grade_label(grade)}\n\nSelect Unit:",
                unit_menu(units)
            )
            return

        # ---------------- UNIT ----------------

        if data.startswith("unit_"):
            key = data.split("_", 1)[1]
            unit = _decode_file_key(key)
            set_unit(context, unit)

            grade = context.user_data.get("grade")
            subject = context.user_data.get("subject")

            if not grade or not subject:
                await safe_answer(query, "⚠️ Flow error, restart", alert=True)
                return

            await safe_edit(
                query,
                f"📚 Grade: {get_grade_label(grade)}\n"
                f"📘 Subject: {get_subject_label(subject)}\n"
                f"📖 Unit: {format_file_label(unit)}\n\n"
                "Ready to start the quiz?",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Start Quiz", callback_data="quiz_start")],
                    [InlineKeyboardButton("⬅ Back", callback_data="back_unit")]
                ])
            )
            return

        # ---------------- START QUIZ ----------------

        if data == "quiz_start":

            if not is_ready_to_start(context):
                await safe_answer(query, "⚠️ Complete selection first", alert=True)
                return

            if not await ensure_membership(query, context):
                return

            await tg_safe(lambda: start_quiz_flow(update, context))
            return

        # ---------------- QUIZ OPTIONS ----------------

        if data.startswith("mode_"):
            mode = data.split("_", 1)[1]
            set_mode(context, mode)

            grade = context.user_data.get("grade")
            subject = context.user_data.get("subject")
            unit = context.user_data.get("unit")

            await safe_edit(
                query,
                "🎯 Ready to start?\n\n"
                f"📚 Grade: {grade}\n"
                f"📘 Subject: {subject}\n"
                f"📖 Unit: {unit}\n"
                f"🎮 Mode: {mode.title()}",
                confirm_menu()
            )
            return

        # ---------------- BACK NAVIGATION ----------------

        if data == "back_options":
            from .flow_service import reset_options
            reset_options(context)

            grade = context.user_data.get("grade")
            subject = context.user_data.get("subject")
            unit = context.user_data.get("unit")

            await safe_edit(
                query,
                "⚙️ Customize your quiz:\n\n"
                f"📚 Grade: {grade}\n"
                f"📘 Subject: {subject}\n"
                f"📖 Unit: {unit}",
                quiz_options_menu()
            )
            return

        if data == "back_menu":
            reset_all(context)
            await safe_edit(query, "🏠 Main Menu", build_main_menu())
            return

        if data == "back_subject":
            reset_all(context)
            await safe_edit(query, "🧠 Select Subject:", subject_menu())
            return

        if data == "back_grade":
            context.user_data.pop("grade", None)
            context.user_data.pop("unit", None)

            if not context.user_data.get("subject"):
                await safe_answer(query, "⚠️ Select subject first", alert=True)
                return

            await safe_edit(query, "🎓 Select Grade:", grade_menu())
            return

        if data == "back_unit":
            context.user_data.pop("unit", None)
            context.user_data.pop("mode", None)

            grade = context.user_data.get("grade")
            subject = context.user_data.get("subject")

            if not grade or not subject:
                await safe_answer(query, "⚠️ Flow error, restart", alert=True)
                return

            units = get_units(grade, subject)

            await safe_edit(query, "📖 Select Unit:", unit_menu(units))
            return

        # ---------------- FALLBACK ----------------

        logger.warning(f"Unhandled callback: {data}")
        await safe_answer(query, "⚠️ Unknown action", alert=True)

    except Exception as e:
        logger.exception(e)
        await safe_answer(query, "⚠️ Something went wrong", alert=True)
