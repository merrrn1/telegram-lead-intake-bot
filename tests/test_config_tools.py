from ai_admin_bot.config_tools import normalize_studio_config


def test_normalize_studio_config_keeps_public_fields_only():
    source = {
        "business_name": "Demo",
        "intro": "Hello",
        "fallback": "Fallback",
        "quick_buttons": [["Request"]],
        "faq": [{"keywords": ["price"], "answer": "Ask us"}],
        "fields": {"name": "Name"},
        "questions": {"name": "Your name?"},
        "internal_note": "must not be exported",
    }
    result = normalize_studio_config(source)
    assert result["business_name"] == "Demo"
    assert "internal_note" not in result
