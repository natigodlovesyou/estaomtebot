# db/user_repo.py
import logging
from typing import List, Dict, Optional
from db.database import (
    get_user as db_get_user,
    add_score as db_add_score,
    get_top_scores as db_get_top_scores,
    add_referral as db_add_referral,
    get_invite_count as db_get_invite_count,
    register_user as db_register_user,
    _single,
    _rows,
    _scalar,
)

logger = logging.getLogger(__name__)

# -----------------------------
# User Registration
# -----------------------------
def register_user(user_id: int, username: Optional[str] = None, first_name: Optional[str] = None):
    try:
        db_register_user(user_id, username, first_name)
        logger.info(f"User registered: {user_id} | {username} | {first_name}")
    except Exception:
        logger.exception(f"Failed to register user {user_id}")


# -----------------------------
# Get Single User
# -----------------------------
def get_user(user_id: int) -> Optional[Dict]:
    try:
        row = db_get_user(user_id)
        if row:
            return {
                "user_id": row["user_id"],
                "username": row["username"],
                "first_name": row["first_name"],
                "joined_at": row["joined_at"],
            }
        return None
    except Exception:
        logger.exception(f"Failed fetching user {user_id}")
        return None


# -----------------------------
# Get All Users
# -----------------------------
def get_all_users() -> List[int]:
    try:
        result = _single("SELECT user_id FROM users", ())
        return [int(row["user_id"]) for row in _rows(result)]
    except Exception:
        logger.exception("Failed fetching all users")
        return []


# -----------------------------
# Get Total Users / Quizzes
# -----------------------------
def get_total_users() -> int:
    try:
        result = _single("SELECT COUNT(*) as total FROM users", ())
        return int(_scalar(result, 0) or 0)
    except Exception:
        logger.exception("Failed counting users")
        return 0


def get_total_quizzes() -> int:
    try:
        result = _single("SELECT COUNT(*) as total FROM scores", ())
        return int(_scalar(result, 0) or 0)
    except Exception:
        logger.exception("Failed counting quizzes")
        return 0


# -----------------------------
# Referral / Invite Count
# -----------------------------
def get_invite_count(user_id: int) -> int:
    try:
        return db_get_invite_count(user_id)
    except Exception:
        logger.exception(f"Failed fetching invite count for {user_id}")
        return 0


def add_referral(inviter_id: int, invited_user_id: int):
    try:
        db_add_referral(inviter_id, invited_user_id)
        logger.info(f"Referral added: inviter={inviter_id}, invited={invited_user_id}")
    except Exception:
        logger.exception(f"Failed adding referral inviter={inviter_id}, invited={invited_user_id}")


# -----------------------------
# Add / Update Score
# -----------------------------
def add_score(user_id: int, score: int):
    try:
        db_add_score(user_id, score)
        logger.info(f"Added {score} points to user {user_id}")
    except Exception:
        logger.exception(f"Failed adding score for user {user_id}")


# -----------------------------
# Get Leaderboard
# -----------------------------
def get_top_scores(limit: int = 10) -> List[Dict]:
    try:
        return db_get_top_scores(limit)
    except Exception:
        logger.exception("Failed fetching leaderboard")
        return []


# -----------------------------
# Get User Stats
# -----------------------------
def get_user_stats(user_id: int) -> Optional[Dict]:
    try:
        user = get_user(user_id)
        if not user:
            return None

        result = _single(
            "SELECT SUM(score) as total FROM scores WHERE user_id = ?",
            (user_id,)
        )
        total_score = int(_scalar(result, 0) or 0)

        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "first_name": user["first_name"],
            "total_score": total_score,
        }
    except Exception:
        logger.exception(f"Failed fetching stats for user {user_id}")
        return None
