import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def sanitize_markdown(text: str) -> str:
    """Sanitize text for Telegram MarkdownV2."""
    if not text:
        return ""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text

def get_translated_text(key: str, lang: str = "en") -> str:
    """Retrieve translated text from JSON files."""
    lang_dir = Path(__file__).resolve().parent.parent / "lang"
    lang_file = lang_dir / f"{lang}.json"
    
    try:
        if not lang_file.exists():
            logger.warning(f"⚠️ Language file {lang_file} not found, falling back to 'en'")
            lang_file = lang_dir / "en.json"
        
        with open(lang_file, "r", encoding="utf-8") as f:
            translations = json.load(f)
        
        result = translations
        for part in key.split("."):
            result = result.get(part, part)
        
        if isinstance(result, dict):
            return result.get(lang, result.get("en", key))
        return result if isinstance(result, str) else key
    except Exception as e:
        logger.error(f"❌ Error loading translations for {lang}: {str(e)}")
        return key
