"""
referrals/referral_system.py

Handles user referrals, invite links, and bonus point rewards
for the MegaMind Quiz Bot.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from config import INVITE_MAX_PER_DAY, REFERRAL_BONUS_POINTS
from db.database import add_referral, get_invite_count, add_score, get_user

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Generate User-Specific Referral Link
# ---------------------------------------------------
def generate_referral_link(bot_username: str, user_id: int) -> str:
    """Return the personal referral link for a user."""
    if not bot_username:
        # Try to get from context or use fallback
        import os
        bot_username = os.getenv("BOT_USERNAME", "Estaomtebotv1")
    return f"https://t.me/{bot_username}?start=ref_{user_id}"


# ---------------------------------------------------
# Process Referral Start
# ---------------------------------------------------
async def process_referral_start(user_id: int, referral_code: str, context=None) -> bool:
    """
    Process a referral when a new user joins using a referral code.
    Adds bonus points to the inviter and tracks invite.
    Returns True if referral was successfully applied.
    """
    try:
        if not referral_code.startswith("ref_"):
            logger.info("Invalid referral code: %s", referral_code)
            return False

        inviter_id = int(referral_code.split("_")[1])

        if inviter_id == user_id:
            logger.info("Self-referral blocked | user=%s", user_id)
            return False

        # Check if already referred
        from db.database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM referrals WHERE inviter_id = ? AND invited_id = ?", (inviter_id, user_id))
        if cur.fetchone():
            conn.close()
            logger.info("User %s already referred by %s", user_id, inviter_id)
            return False
        conn.close()

        existing_invites = get_invite_count(inviter_id)
        if existing_invites >= INVITE_MAX_PER_DAY:
            logger.info("Inviter %s reached max invites today", inviter_id)
            return False

        # Record referral
        add_referral(inviter_id, user_id)

        # Add bonus points to inviter
        add_score(inviter_id, REFERRAL_BONUS_POINTS)
        logger.info(
            "Referral processed | inviter=%s invited=%s +%s pts",
            inviter_id, user_id, REFERRAL_BONUS_POINTS
        )

        # Update user states with referral tracking
        from state.storage import get_user_state, update_user_state

        # Update invited user's state
        invited_state = get_user_state(user_id)
        if user_id not in invited_state.players:
            from state.models import PlayerStats
            invited_state.players[user_id] = PlayerStats(user_id=user_id)
        invited_player = invited_state.players[user_id]
        invited_player.referral_code = f"ref_{inviter_id}"
        await update_user_state(user_id, invited_state)

        # Update inviter's state
        inviter_state = get_user_state(inviter_id)
        if inviter_id not in inviter_state.players:
            from state.models import PlayerStats
            inviter_state.players[inviter_id] = PlayerStats(user_id=inviter_id)
        inviter_player = inviter_state.players[inviter_id]
        if user_id not in inviter_player.invited_users:
            inviter_player.invited_users.append(user_id)
        inviter_player.referral_bonus_earned += REFERRAL_BONUS_POINTS
        await update_user_state(inviter_id, inviter_state)

        # Check if inviter has completed invite requirement
        new_invite_count = get_invite_count(inviter_id)
        if new_invite_count >= 2:
            from state.storage import get_user_state, update_user_state
            from handlers.start_handler import build_main_menu
            user_state = get_user_state(inviter_id)
            player = user_state.players.get(inviter_id)
            if player and player.requires_invites:
                player.requires_invites = False
                await update_user_state(inviter_id, user_state)
                if context:
                    await context.bot.send_message(
                        chat_id=inviter_id,
                        text="🎉 Invite requirement completed! You can now access all features.",
                        reply_markup=build_main_menu()
                    )

        if context:
            await notify_inviter(context, inviter_id, user_id)

        return True

    except Exception:
        logger.exception("Referral processing failed | user=%s code=%s", user_id, referral_code)
        return False


# ---------------------------------------------------
# Send Invite Message
# ---------------------------------------------------
async def send_invite_message(update: Update, context):
    """
    Sends the user's personal referral link and current invite count.
    """
    try:
        user_id = update.effective_user.id
        user = get_user(user_id)
        if not user:
            return

        # Get actual bot username
        bot_username = context.bot.username or "Estaomtebotv1"

        invite_link = generate_referral_link(bot_username, user_id)
        invite_count = get_invite_count(user_id)

        # Get referral stats
        stats = get_referral_stats(user_id)

        message = (
            "<b>🎁 Invite Friends & Grow the Community!</b>\n\n"
            "We’re here to help — invite 2 friends and unlock full access.\n\n"
            "Each successful invite gives you 10 bonus points.\n\n"
            f"👥 Invites: {stats['total_invites']}\n"
            f"💰 Bonus Earned: {stats['referral_bonus_earned']} pts\n"
            f"🔗 Your Link:\n{invite_link}\n\n"
            "Share this link with friends so you both benefit from the learning community."
        )

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 View Detailed Stats", callback_data="referral_stats")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back_menu")]
        ])

        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        logger.info("Invite message sent | user=%s invites=%s", user_id, stats['total_invites'])

    except Exception as e:
        logger.exception("Failed to send invite message | user=%s error=%s", user_id, e)


# ---------------------------------------------------
# Notify Inviter
# ---------------------------------------------------
async def notify_inviter(context, inviter_id: int, invited_user_id: int):
    """
    Notify the inviter that a new user joined via referral and
    that bonus points were awarded.
    """
    try:
        inviter = get_user(inviter_id)
        invited = get_user(invited_user_id)

        if not inviter or not invited:
            return

        invited_name = invited.get("username") or invited.get("first_name") or str(invited_user_id)

        await context.bot.send_message(
            chat_id=inviter_id,
            text=f"🎉 You just earned {REFERRAL_BONUS_POINTS} pts! Invited: {invited_name}"
        )

        logger.info("Inviter notified | inviter=%s invited=%s", inviter_id, invited_user_id)

    except Exception:
        logger.exception("Failed to notify inviter | inviter=%s invited=%s", inviter_id, invited_user_id)


# ---------------------------------------------------
# Get Referral Statistics
# ---------------------------------------------------
def get_referral_stats(user_id: int) -> dict:
    """
    Get detailed referral statistics for a user.
    Returns dict with referral data and invited users info.
    """
    from db.database import get_connection
    from state.storage import get_user_state

    conn = get_connection()
    cur = conn.cursor()

    # Get invited users with their details
    cur.execute("""
        SELECT u.user_id, u.username, u.first_name, r.created_at
        FROM referrals r
        JOIN users u ON r.invited_id = u.user_id
        WHERE r.inviter_id = ?
        ORDER BY r.created_at DESC
    """, (user_id,))

    invited_users = []
    for row in cur.fetchall():
        invited_users.append({
            'user_id': row['user_id'],
            'username': row['username'],
            'first_name': row['first_name'],
            'invited_at': row['created_at']
        })

    conn.close()

    # Get user state for additional stats
    user_state = get_user_state(user_id)
    player = user_state.players.get(user_id)

    referral_bonus_earned = 0
    if player:
        referral_bonus_earned = player.referral_bonus_earned

    return {
        'total_invites': len(invited_users),
        'invited_users': invited_users,
        'referral_bonus_earned': referral_bonus_earned,
        'referral_code': f"ref_{user_id}"
    }


# ---------------------------------------------------
# Send Detailed Referral Stats
# ---------------------------------------------------
async def send_referral_stats(update: Update, context):
    """
    Send detailed referral statistics to user.
    """
    try:
        user_id = update.effective_user.id
        user = get_user(user_id)
        if not user:
            return

        stats = get_referral_stats(user_id)

        message = (
            "<b>📊 Your Referral Statistics</b>\n\n"
            f"👥 Total Invites: {stats['total_invites']}\n"
            f"💰 Bonus Points Earned: {stats['referral_bonus_earned']}\n"
            f"🔗 Your Referral Code: {stats['referral_code']}\n\n"
        )

        if stats['invited_users']:
            message += "<b>Invited Users:</b>\n"
            for i, invited in enumerate(stats['invited_users'][:10], 1):  # Show max 10
                name = invited['username'] or invited['first_name'] or f"User {invited['user_id']}"
                date = invited['invited_at'][:10] if invited['invited_at'] else 'Unknown'
                message += f"{i}. {name} ({date})\n"

            if len(stats['invited_users']) > 10:
                message += f"... and {len(stats['invited_users']) - 10} more\n"
        else:
            message += "No invited users yet. We’re here to help — share your personal link to begin earning bonuses."

        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 Invite Friends", callback_data="main_invite")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back_menu")]
            ])
        )

        logger.info("Referral stats sent | user=%s invites=%s", user_id, stats['total_invites'])

    except Exception as e:
        logger.exception("Failed to send referral stats | user=%s error=%s", user_id, e)