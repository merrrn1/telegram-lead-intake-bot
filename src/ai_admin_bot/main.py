import csv
import json
import logging
import os
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


ASK_NEED, ASK_PROBLEM, ASK_LOCATION, ASK_URGENCY, ASK_NAME, ASK_CONTACT = range(6)
FIELD_ORDER = ["need", "problem", "location", "urgency", "name", "contact"]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize(text: str) -> str:
    return text.lower().replace("ё", "е")


def wants_to_leave_request(text: str) -> bool:
    normalized = normalize(text)
    return any(marker in normalized for marker in ["заяв", "остав", "заказ", "нужно", "хочу"])


def load_config() -> dict:
    root = project_root()
    config_path = os.getenv("CONFIG_PATH", "config/service_company.json")
    path = Path(config_path)
    if not path.is_absolute():
        path = root / path

    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    business_name = os.getenv("BUSINESS_NAME")
    if business_name:
        config["business_name"] = business_name

    return config


def keyboard(config: dict) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        config["quick_buttons"],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие или напишите вопрос",
    )


def find_faq_answer(config: dict, text: str) -> str | None:
    normalized = normalize(text)
    for item in config["faq"]:
        if any(keyword in normalized for keyword in item["keywords"]):
            return item["answer"]
    return None


def lead_file() -> Path:
    root = project_root()
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    if not data_dir.is_absolute():
        data_dir = root / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "leads.csv"


def save_lead(user_id: int, username: str | None, lead: dict) -> None:
    path = lead_file()
    is_new = not path.exists()

    with path.open("a", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "created_at",
                "user_id",
                "username",
                "need",
                "problem",
                "location",
                "urgency",
                "name",
                "contact",
            ],
        )
        if is_new:
            writer.writeheader()

        row = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "username": username or "",
        }
        row.update({field: lead.get(field, "") for field in FIELD_ORDER})
        writer.writerow(row)


def format_lead(config: dict, lead: dict, user_id: int, username: str | None) -> str:
    fields = config["fields"]
    lines = [
        f"<b>Новая заявка: {escape(config['business_name'])}</b>",
        f"Telegram user_id: <code>{user_id}</code>",
    ]
    if username:
        lines.append(f"Username: @{escape(username)}")

    for field in FIELD_ORDER:
        label = fields[field]
        value = lead.get(field, "не указано")
        lines.append(f"<b>{escape(label)}:</b> {escape(value)}")

    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    user = update.effective_user
    logging.info("start user_id=%s username=%s", user.id if user else None, user.username if user else None)
    await update.message.reply_text(config["intro"], reply_markup=keyboard(config))


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("lead", None)
    await update.message.reply_text(
        "Ок, заявку не сохраняю. Если нужно начать заново, нажмите \"Оставить заявку\".",
        reply_markup=keyboard(context.bot_data["config"]),
    )
    return ConversationHandler.END


async def request_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    config = context.bot_data["config"]
    context.user_data["lead"] = {}
    await update.message.reply_text(
        "Соберу короткую заявку для менеджера. Можно отменить командой /cancel.\n\n"
        + config["questions"]["need"],
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NEED


async def ask_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["lead"]["need"] = update.message.text.strip()
    await update.message.reply_text(context.bot_data["config"]["questions"]["problem"])
    return ASK_PROBLEM


async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["lead"]["problem"] = update.message.text.strip()
    await update.message.reply_text(context.bot_data["config"]["questions"]["location"])
    return ASK_LOCATION


async def ask_urgency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["lead"]["location"] = update.message.text.strip()
    await update.message.reply_text(context.bot_data["config"]["questions"]["urgency"])
    return ASK_URGENCY


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["lead"]["urgency"] = update.message.text.strip()
    await update.message.reply_text(context.bot_data["config"]["questions"]["name"])
    return ASK_NAME


async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["lead"]["name"] = update.message.text.strip()
    await update.message.reply_text(context.bot_data["config"]["questions"]["contact"])
    return ASK_CONTACT


async def finish_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    config = context.bot_data["config"]
    user = update.effective_user
    lead = context.user_data.get("lead", {})
    lead["contact"] = update.message.text.strip()

    save_lead(user.id, user.username, lead)
    message = format_lead(config, lead, user.id, user.username)

    manager_chat_id = os.getenv("MANAGER_CHAT_ID", "").strip()
    if manager_chat_id:
        await context.bot.send_message(
            chat_id=manager_chat_id,
            text=message,
            parse_mode="HTML",
        )

    await update.message.reply_text(
        "Спасибо. Я передал заявку менеджеру. Он свяжется с вами, чтобы уточнить детали.",
        reply_markup=keyboard(config),
    )
    context.user_data.pop("lead", None)
    return ConversationHandler.END


async def answer_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    text = update.message.text.strip()

    faq_answer = find_faq_answer(config, text)
    if faq_answer:
        await update.message.reply_text(faq_answer, reply_markup=keyboard(config))
        return

    await update.message.reply_text(config["fallback"], reply_markup=keyboard(config))


def main() -> None:
    load_dotenv(project_root() / ".env")

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is required. Copy .env.example to .env and fill it.")

    config = load_config()
    app = Application.builder().token(token).build()
    app.bot_data["config"] = config

    conversation = ConversationHandler(
        entry_points=[
            CommandHandler("request", request_start),
            MessageHandler(filters.Regex(r"(?i).*(остав|заяв|заказ|нужно|хочу).*"), request_start),
        ],
        states={
            ASK_NEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_problem)],
            ASK_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_location)],
            ASK_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_urgency)],
            ASK_URGENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)],
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_request)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conversation)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer_message))

    logging.info("Bot started for business=%s", config["business_name"])
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
