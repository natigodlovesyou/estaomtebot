# MegaMind Quiz Bot

A Telegram quiz bot built with `python-telegram-bot` and SQLite.

## Setup

1. Copy `.env.example` to `.env`.
2. Fill in `BOT_TOKEN`, `ADMIN_ID`, and optional chat/invite settings.
3. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Start the bot:
   ```bash
   python main.py
   ```

## Deployment

- Ensure environment variables are set in your deployment environment.
- Run the bot as a long-lived worker process:
  ```bash
  python main.py
  ```

### Heroku / Railway

If you deploy to Heroku or a similar platform, use a worker process:

```text
worker: python main.py
```

## Testing & CI

- Install development dependencies:
  ```bash
  python -m pip install -r requirements.txt -r dev-requirements.txt
  ```
- Run unit tests:
  ```bash
  pytest -q
  ```

This repository also includes a GitHub Actions workflow at `.github/workflows/python-app.yml` for automated testing on push and pull requests.

## Notes

- Data is stored in `database/bot.db`.
- Runtime state is persisted in `state.json`.
- Keep your bot token and admin ID private.
