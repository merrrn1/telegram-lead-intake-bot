# Telegram Lead Intake Bot

A small, configurable Telegram bot that answers common questions, collects a structured customer request and sends a clean lead card to a manager.

It is designed for service businesses that need a reliable intake flow before adding an AI model or a full CRM.

## What it does

- answers FAQ entries from a JSON configuration;
- collects service, problem, location, urgency, name and contact;
- stores every lead in a UTF-8 CSV file;
- optionally sends an HTML-formatted lead card to a manager chat;
- keeps business copy and questions outside the Python code;
- runs locally, on a VPS or in Docker.

No OpenAI key is required. The default flow is deterministic, inexpensive and easy to audit.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python src/ai_admin_bot/main.py
```

Set `BOT_TOKEN` in `.env`. To receive lead cards in a private chat or group, also set `MANAGER_CHAT_ID`.

## Configuration

Edit `config/service_company.json` to change:

- business name and greeting;
- quick reply buttons;
- FAQ keywords and answers;
- lead field labels;
- intake questions.

`CONFIG_PATH` can point to another JSON file, so one deployment can be adapted for a different business without changing the application code.

## Docker

```bash
docker build -t telegram-lead-intake .
docker run --env-file .env -v "$(pwd)/data:/app/data" telegram-lead-intake
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests cover FAQ matching, request intent detection, safe lead formatting, CSV persistence and configuration conversion.

## Security notes

- Never commit a real bot token or customer data.
- Use a dedicated bot for each production client.
- Give the bot only the Telegram permissions it actually needs.
- Back up or rotate the local CSV if it contains personal data.

## Good next steps

- Google Sheets or CRM delivery;
- webhook deployment behind HTTPS;
- per-service branching questions;
- explicit consent and retention settings;
- optional LLM fallback with a human-review boundary.
