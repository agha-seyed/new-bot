import json
import os
import re


def get_translated_text(key, lang):
    """Retrieves the translated text for a given key and language."""
    # Construct the full path to the language file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lang_file_path = os.path.join(base_dir, "lang", f"{lang}.json")

    with open(lang_file_path, "r", encoding="utf-8") as f:
        translations = json.load(f)
    return translations.get(key, f"Missing translation for key: {key}")


def sanitize_markdown(text):
    """Escapes special Markdown characters in a string."""
    return re.sub(r"([_*\[\]()~`>#\+\-=|{}.!])", r"\\\1", text)
