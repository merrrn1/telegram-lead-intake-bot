import csv
from pathlib import Path

from ai_admin_bot import main


CONFIG = {
    "business_name": "Test & Service",
    "faq": [
        {"keywords": ["цен", "сколько"], "answer": "Цена после оценки."},
    ],
    "fields": {
        "need": "Услуга",
        "problem": "Проблема",
        "location": "Район",
        "urgency": "Срочность",
        "name": "Имя",
        "contact": "Контакт",
    },
}


def test_find_faq_answer_normalizes_russian_text():
    assert main.find_faq_answer(CONFIG, "СКОЛЬКО это стоит?") == "Цена после оценки."
    assert main.find_faq_answer(CONFIG, "Гарантия") is None


def test_request_intent_detection():
    assert main.wants_to_leave_request("Хочу оставить заявку")
    assert main.wants_to_leave_request("Мне нужно настроить сервер")
    assert not main.wants_to_leave_request("Какая у вас гарантия?")


def test_format_lead_escapes_user_content():
    lead = {
        "need": "<script>",
        "problem": "Не работает",
        "location": "Example City",
        "urgency": "Сегодня",
        "name": "Иван & Ко",
        "contact": "demo-contact",
    }
    message = main.format_lead(CONFIG, lead, 42, "user_name")
    assert "&lt;script&gt;" in message
    assert "Иван &amp; Ко" in message
    assert "Test &amp; Service" in message


def test_save_lead_writes_header_and_row(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    lead = {
        "need": "Настройка",
        "problem": "Ошибка",
        "location": "Example City",
        "urgency": "Завтра",
        "name": "Alex",
        "contact": "demo-contact",
    }
    main.save_lead(7, "sergey", lead)

    rows = list(csv.DictReader((tmp_path / "leads.csv").open(encoding="utf-8-sig")))
    assert len(rows) == 1
    assert rows[0]["user_id"] == "7"
    assert rows[0]["contact"] == "demo-contact"
