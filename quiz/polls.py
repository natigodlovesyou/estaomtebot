import logging

from telegram.ext import ContextTypes

from config import OPEN_PERIOD


logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Active Polls Tracker
# ---------------------------------------------------

ACTIVE_POLLS = {}


# Structure:
#
# ACTIVE_POLLS[poll_id] = {
#     "user_id": 123,
#     "correct_option": 2
# }


# ---------------------------------------------------
# Send Quiz Poll
# ---------------------------------------------------

async def send_quiz_poll(context: ContextTypes.DEFAULT_TYPE, user_id, question):

    """
    Sends a quiz poll to the user and tracks the poll_id.
    """

    try:

        message = await context.bot.send_poll(
            chat_id=user_id,
            question=question["question"],
            options=question["options"],
            type="quiz",
            correct_option_id=question["correct"],
            is_anonymous=False,
            open_period=OPEN_PERIOD
        )

        poll_id = message.poll.id

        ACTIVE_POLLS[poll_id] = {
            "user_id": user_id,
            "correct_option": question["correct"]
        }

        return poll_id

    except Exception:
        logger.exception("Failed to send quiz poll")
        return None


# ---------------------------------------------------
# Get Poll Data
# ---------------------------------------------------

def get_poll_data(poll_id):

    return ACTIVE_POLLS.get(poll_id)


# ---------------------------------------------------
# Remove Poll
# ---------------------------------------------------

def remove_poll(poll_id):

    if poll_id in ACTIVE_POLLS:
        del ACTIVE_POLLS[poll_id]