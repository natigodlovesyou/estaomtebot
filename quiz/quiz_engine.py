import logging
import random
import time
import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from quiz.questions import load_questions
from leaderboard.leaderboard import update_user_score
from quiz.answer_engine import evaluate_answer
from quiz.learning_tracker import update_learning
from state.storage import get_user_state, update_user_state
from state.models import QuizSession
from config import OPEN_PERIOD, ADMIN_ID

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Safe Send Utility
# ---------------------------------------------------

async def safe_send(user, text, reply_markup=None):
    try:
        await user.send_message(text=text, reply_markup=reply_markup)
    except Exception:
        logger.warning(f"Failed to message user {user.id}")


# ---------------------------------------------------
# Get Time Limit by Subject
# ---------------------------------------------------

def get_time_limit(subject: str) -> int:
    """Return time limit in seconds based on subject."""
    if subject in ["maths", "physics"]:
        return 150
    if subject == "chemistry":
        return 80
    return 60


# ---------------------------------------------------
# Start Quiz
# ---------------------------------------------------

async def start_quiz_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    user_id = update.effective_user.id

    await query.answer()

    try:
        grade = context.user_data.get("grade")
        subject = context.user_data.get("subject")
        unit = context.user_data.get("unit")
        mode = context.user_data.get("mode", "timed")

        questions = load_questions(grade, subject, unit)

        if not questions:
            from handlers.start_handler import build_main_menu
            await query.edit_message_text("⚠️ No questions available for this selection.", reply_markup=build_main_menu())
            return

        random.shuffle(questions)

        time_limit = get_time_limit(subject)
        if mode == "practice":
            time_limit = 300  # 5 minutes for practice

        session = QuizSession(
            user_id=user_id,
            active=True,
            grade=grade,
            subject=subject,
            unit=unit,
            questions=questions,
            time_limit=time_limit,
            open_period=time_limit,
            start_time=int(time.time())
        )

        user_state = get_user_state(user_id)
        user_state.sessions[user_id] = session
        await update_user_state(user_id, user_state)

        await query.edit_message_text(
            f"🧠 Quiz Started!\n"
            f"❓ {len(questions)} questions\n"
            f"🎮 Mode: {mode.title()}\n"
            f"⏱ {time_limit} seconds per question.\n"
            f"🔥 Build your streak!"
        )

        await send_next_question(update, context)

    except Exception:
        logger.exception("Error starting quiz")
        await query.edit_message_text("⚠️ Failed to start quiz.")


# ---------------------------------------------------
# Send Next Question
# ---------------------------------------------------

async def send_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    user_state = get_user_state(user_id)
    session = user_state.sessions.get(user_id)

    if not session or not session.active:
        return

    questions = session.questions
    index = session.question_index

    if index >= len(questions):
        await finish_quiz(update, context)
        return

    question = questions[index]

    session.answered = False
    session.question_start_time = time.time()
    session.last_activity = time.time()

    total = len(questions)

    open_period = session.open_period or OPEN_PERIOD
    poll_msg = await context.bot.send_poll(
        chat_id=user_id,
        question=(
            f"{question['question']}\n\n"
            f"📊 {index + 1}/{total} | 🔥 Streak: {session.streak}"
        ),
        options=question["options"],
        type="quiz",
        correct_option_id=question["correct"],
        is_anonymous=False,
        open_period=open_period
    )

    session.current_poll_id = poll_msg.poll.id
    await update_user_state(user_id, user_state)

    # Start timer update task
    question_base = (
        f"{question['question']}\n\n"
        f"📊 {index + 1}/{total} | 🔥 Streak: {session.streak}"
    )
    async def update_timer():
        if open_period <= 10:
            return
        for remaining in range(open_period - 10, 0, -10):
            await asyncio.sleep(10)
            new_question = f"{question_base}\n\n⏱️ Time remaining: {remaining}s"
            try:
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=poll_msg.message_id,
                    text=new_question
                )
            except Exception:
                break  # Stop if can't edit

    asyncio.create_task(update_timer())


# ---------------------------------------------------
# Process Answer
# ---------------------------------------------------

async def process_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        answer = update.poll_answer
        user_id = answer.user.id

        user_state = get_user_state(user_id)
        session = user_state.sessions.get(user_id)

        if not session or not session.active:
            return

        if answer.poll_id != session.current_poll_id:
            return

        if session.answered:
            return

        session.answered = True
        session.last_activity = time.time()

        if not answer.option_ids:
            return

        index = session.question_index
        questions = session.questions

        if index >= len(questions):
            return

        question = questions[index]
        selected = answer.option_ids[0]

        now = time.time()
        start_time = session.question_start_time or now
        time_taken = now - start_time

        result = evaluate_answer(
            session=session,
            question=question,
            selected=selected,
            time_taken=time_taken
        )

        if result["is_timeout"]:
            result["is_correct"] = False

        if result["is_correct"]:
            session.score += 1
            session.correct_answers += 1
            session.streak += 1
        else:
            session.wrong_answers += 1
            session.streak = 0

        session.max_streak = max(session.max_streak, session.streak)

        await update_learning(
            user_id=user_id,
            topic=question.get("topic", "general"),
            is_correct=result["is_correct"]
        )

        correct_option = question["options"][question["correct"]]
        explanation = question.get("explanation", "No explanation provided.")

        feedback = result["feedback"] + "\n\n"

        if result.get("is_timeout"):
            feedback += "⏱ Time's up!\n\n"

        if not result["is_correct"] and not result.get("is_timeout"):
            feedback += f"✅ Correct Answer: {correct_option}\n\n"

        feedback += f"📘 Explanation:\n{explanation}"

        await safe_send(update.effective_user, feedback)

        session.question_index += 1
        await update_user_state(user_id, user_state)
        await send_next_question(update, context)

    except Exception:
        logger.exception("Error processing answer")


# ---------------------------------------------------
# Finish Quiz
# ---------------------------------------------------

async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_state = get_user_state(user_id)
    session = user_state.sessions.get(user_id)

    if not session or not session.active:
        return

    # ✅ ALWAYS create player FIRST
    player = user_state.players.get(user_id)
    if not player:
        from state.models import PlayerStats
        player = PlayerStats(user_id=user_id)
        user_state.players[user_id] = player

    score = session.score
    total = len(session.questions)
    percentage = round((score / total) * 100) if total > 0 else 0

    await safe_send(
        user,
        "🏁 Quiz Finished!\n\n"
        f"📊 Score: {score}/{total}\n"
        f"🎯 Accuracy: {percentage}%\n"
        f"🔥 Max Streak: {session.max_streak}"
    )

    # ✅ Update stats
    player.quizzes_taken += 1
    player.correct_answers += score
    player.total_score += score

    # ✅ Save leaderboard
    try:
        await update_user_score(user_id, score)
    except Exception as e:
        print("LEADERBOARD ERROR:", e)

    # ✅ Cleanup session BEFORE sending game button
    del user_state.sessions[user_id]
    await update_user_state(user_id, user_state)

    # ✅ Invite requirement check (skip for admin)
    if user_id != ADMIN_ID:
        from db.database import get_invite_count
        invite_count = get_invite_count(user_id)

        if invite_count < 2:
            player.requires_invites = True
            await safe_send(
                user,
                "🎁 Great work on completing the quiz!\n\n"
                "To help more students and unlock full access, invite 2 friends.\n\n"
                f"Current invites: {invite_count}/2\n\n"
                "Each successful invite gives you 10 bonus points!"
            )
            from referrals.referral_system import send_invite_message
            await send_invite_message(update, context)
            return  # 👈 Don't show game if they still need to invite

    # ✅ Send MegaMind game button after quiz
    await _send_game_button(user, score, percentage)


# ---------------------------------------------------
# Send Game Button (Mini App)
# ---------------------------------------------------

async def _send_game_button(user, score: int, percentage: int):
    """Send the MegaMind Challenge game button after quiz completion."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    from config import GAME_URL

    # Pick motivational message based on performance
    if percentage >= 90:
        mood = "🔥 Incredible score! You earned a brain break."
    elif percentage >= 60:
        mood = "⚡ Nice work! Time to relax and recharge."
    else:
        mood = "💪 Good effort! Clear your mind before the next round."

    try:
        await user.send_message(
            text=(
                f"{mood}\n\n"
                f"🎮 Play MegaMind Challenge — a quick brain game\n"
                f"to relax between study sessions!\n\n"
                f"🏆 Your quiz score: {score} pts ({percentage}%)"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🎮 Play MegaMind Challenge",
                    web_app=WebAppInfo(url=GAME_URL)
                )
            ]])
        )
    except Exception:
        logger.warning(f"Failed to send game button to user {user.id}")

# ---------------------------------------------------
# Stop Quiz
# ---------------------------------------------------

async def stop_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    user_id = user.id
    user_state = get_user_state(user_id)
    session = user_state.sessions.get(user_id)

    if session and session.active:
        del user_state.sessions[user_id]
        await update_user_state(user_id, user_state)

    from handlers.start_handler import build_main_menu

    await safe_send(
        user,
        "🛑 Quiz stopped.",
        reply_markup=build_main_menu()
    )


# ---------------------------------------------------
# Resume Quiz
# ---------------------------------------------------

async def resume_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    user_id = user.id
    user_state = get_user_state(user_id)
    session = user_state.sessions.get(user_id)

    if not session or not session.active:
        await safe_send(
            user,
            "⚠️ No active quiz found. Use /start or the menu to begin a new quiz."
        )
        return

    await safe_send(user, "🔁 Resuming your quiz...")
    await send_next_question(update, context)
