import logging
import libsql_experimental as libsql
from config import TURSO_URL, TURSO_TOKEN

logger = logging.getLogger(__name__)

# ---------------------------------------------------
# Connection
# ---------------------------------------------------

def get_connection():
    conn = libsql.connect(database=TURSO_URL, auth_token=TURSO_TOKEN)
    return conn

# ---------------------------------------------------
# Initialize Database
# ---------------------------------------------------

def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            score INTEGER,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            inviter_id INTEGER,
            invited_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state_data TEXT NOT NULL
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_scores_user_id ON scores(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_referrals_inviter ON referrals(inviter_id)")

    conn.commit()
    conn.close()
    logger.info("Turso DB initialized")

# ---------------------------------------------------
# User Functions
# ---------------------------------------------------

def register_user(user_id, username, first_name):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user_id, username, first_name),
    )
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    result = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = result.fetchone()
    conn.close()
    if not row:
        return None
    return dict(zip([d[0] for d in result.description], row))

# ---------------------------------------------------
# Score Functions
# ---------------------------------------------------

def add_score(user_id, score):
    conn = get_connection()
    conn.execute(
        "INSERT INTO scores (user_id, score) VALUES (?, ?)",
        (user_id, score),
    )
    conn.commit()
    conn.close()

def get_user_total_score(user_id):
    conn = get_connection()
    result = conn.execute(
        "SELECT SUM(score) as total FROM scores WHERE user_id = ?",
        (user_id,),
    )
    row = result.fetchone()
    conn.close()
    return row[0] or 0 if row else 0

def get_top_scores(limit=10):
    conn = get_connection()
    result = conn.execute("""
        SELECT user_id, SUM(score) as total
        FROM scores
        GROUP BY user_id
        ORDER BY total DESC
        LIMIT ?
    """, (limit,))
    rows = result.fetchall()
    cols = [d[0] for d in result.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

# ---------------------------------------------------
# Referral Functions
# ---------------------------------------------------

def add_referral(inviter_id, invited_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO referrals (inviter_id, invited_id) VALUES (?, ?)",
        (inviter_id, invited_id),
    )
    conn.commit()
    conn.close()

def get_invite_count(user_id):
    conn = get_connection()
    result = conn.execute(
        "SELECT COUNT(*) as total FROM referrals WHERE inviter_id = ?",
        (user_id,),
    )
    row = result.fetchone()
    conn.close()
    return row[0] if row else 0

# ---------------------------------------------------
# User State Functions
# ---------------------------------------------------

def save_user_state(user_id, state_data):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state_data) VALUES (?, ?)",
        (user_id, state_data),
    )
    conn.commit()
    conn.close()

def load_user_state(user_id):
    conn = get_connection()
    result = conn.execute(
        "SELECT state_data FROM user_states WHERE user_id = ?",
        (user_id,),
    )
    row = result.fetchone()
    conn.close()
    return row[0] if row else None

def load_all_user_states():
    conn = get_connection()
    result = conn.execute("SELECT user_id, state_data FROM user_states")
    rows = result.fetchall()
    conn.close()
    return {str(row[0]): row[1] for row in rows}

def clear_user_states():
    conn = get_connection()
    conn.execute("DELETE FROM user_states")
    conn.commit()
    conn.close()
