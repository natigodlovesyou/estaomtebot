import os
import logging
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------
# Load environment variables from .env file
# ---------------------------------------------------------
load_dotenv()

# =========================================================
# Project Base Directory
# =========================================================
BASE_DIR = Path(__file__).resolve().parent

# =========================================================
# Data & File Paths
# =========================================================
DATA_DIR = BASE_DIR / "data"                 # Folder for quiz JSON files
STATE_FILE = BASE_DIR / "state.json"         # Persistent bot state
HISTORY_FILE = BASE_DIR / "leaderboard_history.json"  # Optional leaderboard archive
LOG_FILE = BASE_DIR / "bot.log"              # Log file

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# Environment Variables
# =========================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
COMMUNITY_CHAT_ID = os.getenv("COMMUNITY_CHAT_ID", "-1002706693000")
COMMUNITY_INVITE = os.getenv("COMMUNITY_INVITE", "https://t.me/+sw9Iezu2kWxlOTQ0")

ADMIN_ID = int(ADMIN_ID)
COMMUNITY_CHAT_ID = int(COMMUNITY_CHAT_ID)
PRIVATE_CHANNEL_ID = int(os.getenv("PRIVATE_CHANNEL_ID", "0"))

# =========================================================
# Turso Database
# =========================================================
TURSO_URL = os.getenv("TURSO_URL")
TURSO_TOKEN = os.getenv("TURSO_TOKEN")

# =========================================================
# MegaMind Mini Game
# =========================================================
GAME_URL = os.getenv("GAME_URL", "https://your-app-name.onrender.com/game")
# 👆 Set GAME_URL in your Render environment variables,
#    or replace the default with your actual Render URL.

# =========================================================
# Quiz Behavior Settings
# =========================================================
OPEN_PERIOD = 90                # Poll open time (seconds)
NEXT_DELAY_BUFFER = 3           # Delay between questions (seconds)
EARLY_ANSWER_WAIT = 5           # Wait after early answer (seconds)
REFERRAL_BONUS_POINTS = 10      # Points given per successful referral

# =========================================================
# Referral System Limits
# =========================================================
INVITE_CONFIRM_DELAY = 60       # Seconds to confirm invite
INVITE_MAX_PER_DAY = 10         # Max referrals per day per user

# =========================================================
# Supported Grades
# =========================================================
GRADES = ["grade9", "grade10", "grade11", "grade12"]

# =========================================================
# Supported Subjects
# =========================================================
SUBJECTS = ["math", "physics", "chemistry", "biology", "english"]

# =========================================================
# Units per Subject
# =========================================================
PREDEFINED_UNIT_COUNT = 10  # Number of units per subject

# =========================================================
# Logging Configuration
# =========================================================
LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

# =========================================================
# Validation Checks
# =========================================================
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is not set.\n"
        "Set it using:\n"
        "export BOT_TOKEN=your_token_here"
    )

if not TURSO_URL or not TURSO_TOKEN:
    raise RuntimeError(
        "TURSO_URL and TURSO_TOKEN environment variables are not set.\n"
        "Add them in your Render environment settings."
    )

if ADMIN_ID == 0:
    print("⚠️ Warning: ADMIN_ID not set. Admin commands may not work.")
