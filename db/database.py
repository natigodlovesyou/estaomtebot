import sqlite3
from pathlib import Path

from config import DATABASE_FILE


DB_PATH = Path(DATABASE_FILE)


# ---------------------------------------------------
# Connection
# ---------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------------------------------
# Initialize Database
# ---------------------------------------------------

def init_db():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            score INTEGER,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            inviter_id INTEGER,
            invited_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state_data TEXT NOT NULL
        )
    """)

    # indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scores_user_id ON scores(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_referrals_inviter ON referrals(inviter_id)")

    conn.commit()
    conn.close()

# ---------------------------------------------------
# User Functions
# ---------------------------------------------------

def register_user(user_id, username, first_name):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (user_id, username, first_name))

    conn.commit()
    conn.close()


def get_user(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM users WHERE user_id = ?
    """, (user_id,))

    user = cur.fetchone()

    conn.close()

    return user


# ---------------------------------------------------
# Score Functions
# ---------------------------------------------------

def add_score(user_id, score):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scores (user_id, score)
        VALUES (?, ?)
    """, (user_id, score))

    conn.commit()
    conn.close()


def get_user_total_score(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT SUM(score) as total
        FROM scores
        WHERE user_id = ?
    """, (user_id,))

    result = cur.fetchone()
    conn.close()

    return result["total"] or 0


def get_top_scores(limit=10):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, SUM(score) as total
        FROM scores
        GROUP BY user_id
        ORDER BY total DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()

    conn.close()

    return rows


# ---------------------------------------------------
# Referral Functions
# ---------------------------------------------------

def add_referral(inviter_id, invited_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO referrals (inviter_id, invited_id)
        VALUES (?, ?)
    """, (inviter_id, invited_id))

    conn.commit()
    conn.close()


def get_invite_count(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) as total
        FROM referrals
        WHERE inviter_id = ?
    """, (user_id,))

    result = cur.fetchone()

    conn.close()

    return result["total"]


# ---------------------------------------------------
# Clear Database (for testing/reset)
# ---------------------------------------------------

def save_user_state(user_id, state_data):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO user_states (user_id, state_data)
        VALUES (?, ?)
    """, (user_id, state_data))

    conn.commit()
    conn.close()


def load_user_state(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT state_data FROM user_states WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()
    conn.close()

    return row["state_data"] if row else None


def load_all_user_states():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT user_id, state_data FROM user_states")

    rows = cur.fetchall()
    conn.close()

    return {row["user_id"]: row["state_data"] for row in rows}


def clear_user_states():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM user_states")

    conn.commit()
    conn.close()
