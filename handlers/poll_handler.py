import logging

from telegram import Update
from telegram.ext import ContextTypes

from quiz.quiz_engine import process_answer


logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Handle Poll Answers
# ---------------------------------------------------

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles incoming poll answers from Telegram.
    """

    if not update.poll_answer:
        return

    try:
        await process_answer(update, context)

    except Exception:
        logger.exception("Error handling poll answer")