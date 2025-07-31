import os
import json
import logging
from datetime import datetime
import asyncio
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional
import fitz  # PyMuPDF
import docx
from bs4 import BeautifulSoup
from telegram.error import TelegramError
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

MAX_RESULT_LENGTH = 1200
MAX_TELEGRAM_MESSAGE_LENGTH = 4096
MAX_EMAIL_BODY_LENGTH = 4000

async def send_email(to_email: str, subject: str, body: str, user_id: int, lang: str = "en") -> bool:
    """Send an email with the given subject and body."""
    try:
        if not config.EMAIL_SENDER or not config.EMAIL_PASSWORD:
            logger.error("❌ EMAIL_SENDER or EMAIL_PASSWORD not set.")
            return False

        msg = EmailMessage()
        msg["From"] = config.EMAIL_SENDER
        msg["To"] = to_email
        msg["Subject"] = sanitize_markdown(subject)
        msg.set_content(sanitize_markdown(body[:MAX_EMAIL_BODY_LENGTH]))

        loop = asyncio.get_event_loop()
        smtp_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        try:
            await loop.run_in_executor(None, lambda: smtp_server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD))
            await loop.run_in_executor(None, lambda: smtp_server.send_message(msg))
        finally:
            smtp_server.quit()
        
        await award_points_for_action(user_id, "interaction")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                "N/A",
                body[:1000],
                0,
                "N/A",
                to_email,
                "N/A",
                "Email Sent",
                f"Sent email to {to_email}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
        logger.info(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False

async def extract_text_from_html(file_path: str) -> str:
    """Extract visible text from an HTML file."""
    try:
        loop = asyncio.get_event_loop()
        with open(file_path, "r", encoding="utf-8") as f:
            soup = await loop.run_in_executor(None, BeautifulSoup, f.read(), "html.parser")
            return soup.get_text(separator="\n")
    except Exception as e:
        logger.error(f"⚠️ Error reading HTML {file_path}: {str(e)}")
        return ""

async def search_in_documents(query: str, user_id: int = None, user_email: str = None, lang: str = "en") -> Optional[str]:
    """Search for a query in PDFs, DOCX, TXT, and HTML files."""
    try:
        query = query.strip().lower()
        if len(query) < 3:
            return get_translated_text("search_too_short", lang)
        
        results = []
        directories = {
            "PDF": "studentbot/assets/pdfs",
            "Word": "studentbot/assets/docs",
            "Text": "studentbot/assets/texts",
            "HTML": "studentbot/assets/html",
        }

        for file_type, dir_path in directories.items():
            if not os.path.exists(dir_path):
                continue

            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                try:
                    if file_type == "PDF" and filename.endswith(".pdf"):
                        doc = await asyncio.get_event_loop().run_in_executor(None, fitz.open, file_path)
                        for page in doc:
                            text = page.get_text().lower()
                            if query in text:
                                snippet = text[text.find(query):text.find(query)+MAX_RESULT_LENGTH]
                                results.append(f"📄 [{file_type}] {sanitize_markdown(filename)}:\n{sanitize_markdown(snippet)}")
                        doc.close()

                    elif file_type == "Word" and filename.endswith(".docx"):
                        doc = await asyncio.get_event_loop().run_in_executor(None, docx.Document, file_path)
                        for para in doc.paragraphs:
                            text = para.text.strip().lower()
                            if query in text:
                                results.append(f"📝 [{file_type}] {sanitize_markdown(filename)}:\n{sanitize_markdown(text[:MAX_RESULT_LENGTH])}")

                    elif file_type == "Text" and filename.endswith(".txt"):
                        with open(file_path, "r", encoding="utf-8") as f:
                            for line in f:
                                if query in line.lower():
                                    results.append(f"📜 [{file_type}] {sanitize_markdown(filename)}:\n{sanitize_markdown(line.strip()[:MAX_RESULT_LENGTH])}")

                    elif file_type == "HTML" and filename.endswith(".html"):
                        text = await extract_text_from_html(file_path)
                        text = text.lower()
                        if query in text:
                            snippet = text[text.find(query):text.find(query)+MAX_RESULT_LENGTH]
                            results.append(f"🌐 [{file_type}] {sanitize_markdown(filename)}:\n{sanitize_markdown(snippet)}")
                except Exception as e:
                    logger.error(f"⚠️ Error processing {file_type} file {filename}: {str(e)}")

        if not results:
            return get_translated_text("search_failed", lang)

        final_result = "\n\n---\n\n".join(results)
        if len(final_result) > MAX_TELEGRAM_MESSAGE_LENGTH:
            final_result = final_result[:MAX_TELEGRAM_MESSAGE_LENGTH-3] + "..."

        if user_id:
            await award_points_for_action(user_id, "search")
            await gsheets_client.add_interaction_to_sheet(
                config.QUESTIONS_SHEET_NAME,
                [
                    user_id,
                    query,
                    final_result[:1000],
                    0,
                    "Documents",
                    user_email or "N/A",
                    "N/A",
                    "Document Search",
                    f"Document search result for {query}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )

        if user_email:
            subject = get_translated_text("search_email_subject", lang)
            body = final_result[:MAX_EMAIL_BODY_LENGTH]
            await send_email(user_email, subject, body, user_id, lang)

        logger.info(f"✅ Document search for query: {query}, found {len(results)} results")
        return final_result
    except Exception as e:
        logger.error(f"❌ Unexpected error in document search for query {query}: {str(e)}")
        return get_translated_text("search_failed", lang)

def sanitize_markdown(text: str) -> str:
    """Sanitize text for Telegram MarkdownV2 by escaping special characters."""
    if not text:
        return ""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text

def get_translated_text(key: str, lang: str = "en") -> str:
    """Retrieve translated text from JSON files based on the language code."""
    lang_dir = Path(__file__).resolve().parent.parent / "lang"
    lang_file = lang_dir / f"{lang}.json"
    
    try:
        if not lang_file.exists():
            logger.warning(f"⚠️ Language file {lang_file} not found, falling back to 'en'")
            lang_file = lang_dir / "en.json"
        
        with open(lang_file, "r", encoding="utf-8") as f:
            translations = json.load(f)
        
        # Handle nested translations
        result = translations
        for part in key.split("."):
            result = result.get(part, part)
        
        if isinstance(result, dict):
            return result.get(lang, result.get("en", key))
        return result if isinstance(result, str) else key
    except Exception as e:
        logger.error(f"❌ Error loading translations for {lang}: {str(e)}")
        return key  # Fallback to key if translation fails
