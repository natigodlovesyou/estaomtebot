import logging
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


# -----------------------------------------
# Safe Send Message
# -----------------------------------------

async def safe_send(bot, chat_id, text, **kwargs):
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            **kwargs
        )

    except TelegramError as e:
        logger.error(
            "Failed to send message | chat_id=%s | error=%s",
            chat_id,
            e
        )
        return None


# -----------------------------------------
# Safe Edit Message
# -----------------------------------------

async def safe_edit(query, text, **kwargs):
    try:
        return await query.edit_message_text(
            text=text,
            **kwargs
        )

    except TelegramError as e:

        if "message is not modified" in str(e).lower():
            return None

        logger.error(
            "Failed to edit message | chat_id=%s | message_id=%s | error=%s",
            query.message.chat.id if query.message else None,
            query.message.message_id if query.message else None,
            e
        )

        return None


# -----------------------------------------
# Safe Delete Message
# -----------------------------------------

async def safe_delete(bot, chat_id, message_id):
    try:
        await bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )

        return True

    except TelegramError as e:

        if "message to delete not found" in str(e).lower():
            return False

        logger.error(
            "Failed to delete message | chat_id=%s | message_id=%s | error=%s",
            chat_id,
            message_id,
            e
        )

        return False


# -----------------------------------------
# Safe Send Poll
# -----------------------------------------

async def safe_send_poll(bot, chat_id, question, options, **kwargs):
    try:
        return await bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            **kwargs
        )

    except TelegramError as e:
        logger.error(
            "Failed to send poll | chat_id=%s | question=%s | error=%s",
            chat_id,
            question,
            e
        )

        return None


# -----------------------------------------
# Check Community Membership
# -----------------------------------------

async def check_user_member_of_community(bot, user_id, chat_id):
    """
    Check if a user is a member of a Telegram channel or group.
    Works with both chat_id and channel username.
    """

    try:

        member = await bot.get_chat_member(
            chat_id=chat_id,
            user_id=user_id
        )

        valid_status = ["member", "administrator", "creator"]

        return member.status in valid_status

    except TelegramError as e:

        logger.error(
            "Failed checking membership | user_id=%s | chat_id=%s | error=%s",
            user_id,
            chat_id,
            e
        )

        return False