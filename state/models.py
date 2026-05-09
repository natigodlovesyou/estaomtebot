# state/models.py

"""
State models for MegaMind Quiz Bot.

Handles:
- Active quiz sessions
- Player statistics
- Global bot state

Includes safe JSON serialization/deserialization.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set
import asyncio


# ---------------------------------------------------
# Quiz Session Model
# ---------------------------------------------------

@dataclass
class QuizSession:
    """
    Represents an active quiz session for a user.
    """

    user_id: int
    active: bool = False

    grade: Optional[str] = None
    subject: Optional[str] = None
    unit: Optional[str] = None

    questions: List[dict] = field(default_factory=list)
    question_index: int = 0

    score: int = 0
    streak: int = 0
    max_streak: int = 0
    correct_answers: int = 0
    wrong_answers: int = 0
    answered: bool = False

    chat_id: Optional[int] = None
    start_time: Optional[int] = None
    question_start_time: Optional[float] = None
    last_activity: Optional[float] = None

    current_poll_id: Optional[str] = None
    current_message_id: Optional[int] = None

    answered_polls: Set[str] = field(default_factory=set)

    time_limit: int = 60  # Default 60 seconds, adjustable per subject
    open_period: int = 60  # Telegram poll open period; should match time_limit

    # Runtime-only lock (not saved to disk)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)


    # ---------------------------------------------------
    # Serialize Session
    # ---------------------------------------------------

    def to_dict(self) -> dict:
        """
        Convert session to JSON-safe dictionary.
        """

        data = asdict(self)

        # Convert set -> list for JSON
        data["answered_polls"] = list(self.answered_polls)

        # Remove lock (not serializable)
        data.pop("lock", None)

        return data


    # ---------------------------------------------------
    # Deserialize Session
    # ---------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict):
        """
        Restore QuizSession from stored dictionary.
        """

        # Copy to avoid modifying original
        d = dict(data)

        answered = d.pop("answered_polls", [])

        session = cls(**d)

        # Restore set
        session.answered_polls = set(answered or [])

        # Recreate runtime lock
        session.lock = asyncio.Lock()

        return session


# ---------------------------------------------------
# Player Statistics
# ---------------------------------------------------

@dataclass
class PlayerStats:
    """
    Tracks lifetime player statistics.
    """

    user_id: int
    total_score: int = 0
    quizzes_taken: int = 0
    correct_answers: int = 0

    # Invite requirement
    requires_invites: bool = False

    # Referral tracking
    referral_code: Optional[str] = None  # Who invited this user
    invited_users: List[int] = field(default_factory=list)  # Users this player invited
    referral_bonus_earned: int = 0  # Total bonus points earned from referrals

    # Learning data
    learning_topics: Dict[str, dict] = field(default_factory=dict)
    weak_topics: Set[str] = field(default_factory=set)
    strong_topics: Set[str] = field(default_factory=set)
    neutral_topics: Set[str] = field(default_factory=set)


    def to_dict(self) -> dict:
        data = asdict(self)
        data["weak_topics"] = list(self.weak_topics)
        data["strong_topics"] = list(self.strong_topics)
        data["neutral_topics"] = list(self.neutral_topics)
        return data


    @classmethod
    def from_dict(cls, data: dict):
        d = dict(data)
        weak = set(d.pop("weak_topics", []))
        strong = set(d.pop("strong_topics", []))
        neutral = set(d.pop("neutral_topics", []))
        stats = cls(**d)
        stats.weak_topics = weak
        stats.strong_topics = strong
        stats.neutral_topics = neutral
        return stats


# ---------------------------------------------------
# Global Bot State
# ---------------------------------------------------

@dataclass
class BotState:
    """
    Global in-memory state for the bot.
    """

    sessions: Dict[int, QuizSession] = field(default_factory=dict)
    players: Dict[int, PlayerStats] = field(default_factory=dict)

    last_question_time: Optional[int] = None


    # ---------------------------------------------------
    # Serialize State
    # ---------------------------------------------------

    def to_dict(self) -> dict:

        return {
            "sessions": {
                str(uid): session.to_dict()
                for uid, session in self.sessions.items()
            },
            "players": {
                str(uid): player.to_dict()
                for uid, player in self.players.items()
            },
            "last_question_time": self.last_question_time
        }


    # ---------------------------------------------------
    # Deserialize State
    # ---------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict):

        sessions = {
            int(uid): QuizSession.from_dict(sess)
            for uid, sess in data.get("sessions", {}).items()
        }

        players = {
            int(uid): PlayerStats.from_dict(player)
            for uid, player in data.get("players", {}).items()
        }

        last_question_time = data.get("last_question_time")

        return cls(
            sessions=sessions,
            players=players,
            last_question_time=last_question_time
        )
@dataclass
class TopicStats:
    subject: str
    unit: str

    total_questions: int = 0
    correct: int = 0

    weak_score: float = 0.0  # AI difficulty signal
