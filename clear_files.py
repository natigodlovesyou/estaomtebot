import os

files_to_delete = [
    'database/db/bot.db',
    'state.json',
    'leaderboard_history.json'
]

for file_path in files_to_delete:
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted: {file_path}")
    else:
        print(f"File not found: {file_path}")

print("✅ Bot data cleared successfully!")