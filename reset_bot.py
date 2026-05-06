#!/usr/bin/env python3
"""
reset_bot.py - Complete bot reset script
Clears all database data and user states for fresh start
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import clear_database
from state.storage import clear_state

def main():
    print("🔄 Starting bot reset...")
    print("⚠️  This will delete ALL user data, scores, and states!")
    print()

    # Confirm
    confirm = input("Are you sure you want to continue? (type 'YES' to confirm): ")
    if confirm != "YES":
        print("❌ Reset cancelled.")
        return

    print("🗑️  Clearing database...")
    clear_database()

    print("🗑️  Clearing user states...")
    clear_state()

    print()
    print("✅ Bot reset complete!")
    print("🎉 The bot is now ready for a fresh start.")

if __name__ == "__main__":
    main()