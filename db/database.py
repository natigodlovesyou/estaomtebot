import logging
import httpx
from config import TURSO_URL, TURSO_TOKEN

logger = logging.getLogger(__name__)

# Convert libsql:// to https://
BASE_URL = TURSO_URL.replace("libsql://", "https://")
HEADERS = {
    "Authorization": f"Bearer {TURSO_TOKEN}",
    "Content-Type": "application/json",
}

# ---------------------------------------------------
# Execute SQL via Turso HTTP API
# ---------------------------------------------------

def _execute(statements: list) -> list:
    """Send one or more SQL statements to Turso and return results."""
    payload = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": [{"type": _infer_type(a), "value": str(a)} for a in args]}}
            for sql, args in statements
        ] + [{"type": "close"}]
    }
    response = httpx.post(f"{BASE_URL}/v2/pipeline", headers=HEADERS, json=payload, timeout=10)
    response.raise_for_status()
    results = response.json().get("results", [])
    return results

def _infer_type(value):
    if value is None:
        return "null"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    return "text"

def _single(sql, args=()):
    """Execute a single statement."""
    return _execute([(sql, args)])

def _rows(result) -> list:
    """Extract rows from a Turso result."""
    try:
        rs = result[0]["response"]["result"]
        cols = [c["name"] for c in rs["cols"]]
        return [dict(zip(cols, [v["value"] for v in row])) for row in rs["rows"]]
    except Exception:
        return []

def _scalar(result, default=None):
    rows = _rows(result)
    if not rows:
        return default
    first = next(iter(rows[0].values()))
    return first

# ---------------------------------------------------
# Initialize Database
# ---------------------------------------------------

def init_db():
    _execute([
        ("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", ()),
        ("CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, score INTEGER, played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", ()),
        ("CREATE TABLE IF NOT EXISTS referrals (inviter_id INTEGER, invited_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", ()),
        ("CREATE TABLE IF NOT EXISTS user_states (user_id INTEGER PRIMARY KEY, state_data TEXT NOT NULL)", ()),
        ("CREATE INDEX IF NOT EXISTS idx_scores_user_id ON scores(user_id)", ()),
        ("CREATE INDEX IF NOT EXISTS idx_referrals_inviter ON referrals(inviter_id)", ()),
    ])
    logger.info("Turso DB initialized via HTTP")

# ---------------------------------------------------
# User Functions
# ---------------------------------------------------

def register_user(user_id, username, first_name):
    _single(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user_id, username or "", first_name or ""),
    )

def get_user(user_id):
    result = _single("SELECT * FROM users WHERE user_id = ?", (user_id,))
    rows = _rows(result)
    return rows[0] if rows else None

# ---------------------------------------------------
# Score Functions
# ---------------------------------------------------

def add_score(user_id, score):
    _single("INSERT INTO scores (user_id, score) VALUES (?, ?)", (user_id, score))

def get_user_total_score(user_id):
    result = _single("SELECT SUM(score) as total FROM scores WHERE user_id = ?", (user_id,))
    return int(_scalar(result, 0) or 0)

def get_top_scores(limit=10):
    result = _single("""
        SELECT user_id, SUM(score) as total
        FROM scores GROUP BY user_id
        ORDER BY total DESC LIMIT ?
    """, (limit,))
    return _rows(result)

# ---------------------------------------------------
# Referral Functions
# ---------------------------------------------------

def add_referral(inviter_id, invited_id):
    _single("INSERT INTO referrals (inviter_id, invited_id) VALUES (?, ?)", (inviter_id, invited_id))

def get_invite_count(user_id):
    result = _single("SELECT COUNT(*) as total FROM referrals WHERE inviter_id = ?", (user_id,))
    return int(_scalar(result, 0) or 0)

# ---------------------------------------------------
# User State Functions
# ---------------------------------------------------

def save_user_state(user_id, state_data):
    _single(
        "INSERT OR REPLACE INTO user_states (user_id, state_data) VALUES (?, ?)",
        (user_id, state_data),
    )

def load_user_state(user_id):
    result = _single("SELECT state_data FROM user_states WHERE user_id = ?", (user_id,))
    rows = _rows(result)
    return rows[0]["state_data"] if rows else None

def load_all_user_states():
    result = _single("SELECT user_id, state_data FROM user_states", ())
    return {str(row["user_id"]): row["state_data"] for row in _rows(result)}

def clear_user_states():
    _single("DELETE FROM user_states", ())
