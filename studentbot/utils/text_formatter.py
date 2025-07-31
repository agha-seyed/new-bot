import os
import json
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime
import aiosmtplib
from email.message import EmailMessage
from studentbot import config
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action

logger = logging.getLogger(__name__)

MAX_EMAIL_BODY_LENGTH = 4000

async def send_email(to_email: str, subject: str, body: str, user_id: int, lang: str = "en") -> bool:
    """Send an email with the given subject and body asynchronously."""
    try:
        if not config.EMAIL_SENDER or not config.EMAIL_PASSWORD:
            logger.error("❌ EMAIL_SENDER or EMAIL_PASSWORD not set")
            return False

        msg = EmailMessage()
        msg["From"] = config.EMAIL_SENDER
        msg["To"] = to_email
        msg["Subject"] = sanitize_markdown(subject)
        msg.set_content(sanitize_markdown(body[:MAX_EMAIL_BODY_LENGTH]))

        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=465,
            username=config.EMAIL_SENDER,
            password=config.EMAIL_PASSWORD,
            use_tls=True
        )
        
        await award_points_for_action(user_id, "interaction")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id, "N/A", body[:1000], 0, "N/A", to_email, "N/A",
                "Email Sent", f"Sent email to {to_email}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
        logger.info(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False

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
