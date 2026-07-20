import argparse
import json
from pathlib import Path


def normalize_studio_config(config: dict) -> dict:
    return {
        "business_name": config["business_name"],
        "intro": config["intro"],
        "fallback": config["fallback"],
        "quick_buttons": config["quick_buttons"],
        "faq": [
            {
                "keywords": item["keywords"],
                "answer": item["answer"],
            }
            for item in config["faq"]
        ],
        "fields": config["fields"],
        "questions": config["questions"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert LeadPilot Studio JSON to bot config.")
    parser.add_argument("input", help="Path to LeadPilot Studio JSON")
    parser.add_argument("output", help="Path to Telegram bot config JSON")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open("r", encoding="utf-8") as file:
        studio_config = json.load(file)

    bot_config = normalize_studio_config(studio_config)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(bot_config, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"Saved bot config to {output_path}")


if __name__ == "__main__":
    main()

