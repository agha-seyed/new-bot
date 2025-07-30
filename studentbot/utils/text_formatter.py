import os
import logging
from datetime import datetime
import fitz  # PyMuPDF
import docx
import smtplib
import asyncio
from email.message import EmailMessage
from bs4 import BeautifulSoup
from telegram.error import TelegramError
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

MAX_RESULT_LENGTH = 1200


async def send_email(to_email: str, subject: str, body: str, user_id: int, lang: str = "en") -> bool:
    """Sends an email with the given subject and body."""
    try:
        sender = config.EMAIL_SENDER
        password = config.EMAIL_PASSWORD
        if not sender or not password:
            logger.error("❌ EMAIL_SENDER or EMAIL_PASSWORD not set.")
            return False

        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = sanitize_markdown(subject)
        msg.set_content(sanitize_markdown(body))

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: smtplib.SMTP_SSL("smtp.gmail.com", 465).login(sender, password))
        await loop.run_in_executor(None, lambda: smtplib.SMTP_SSL("smtp.gmail.com", 465).send_message(msg))
        
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


async def search_in_documents(query: str, user_id: int = None, user_email: str = None, lang: str = "en") -> str | None:
    """Searches for a query in PDFs, DOCX, TXT, and HTML files."""
    try:
        query = query.strip().lower()
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
                if file_type == "PDF" and filename.endswith(".pdf"):
                    try:
                        doc = await asyncio.get_event_loop().run_in_executor(None, fitz.open, file_path)
                        for page in doc:
                            text = page.get_text().lower()
                            if query in text:
                                snippet = text[text.find(query):text.find(query)+MAX_RESULT_LENGTH]
                                results.append(f"📄 [{file_type}] {sanitize_markdown(filename)}:\n{sanitize_markdown(snippet)}")
                    except Exception as e:
                        logger.error(f"⚠️ PDF Error {filename}: {str(e)}")

                elif file_type == "Word" and filename.endswith(".docx"):
                    try:
                        doc = await asyncio.get_event_loop().run_in_executor(None, docx.Document, file_path)
                        for para in doc.paragraphs:
                            text = para.text.strip().lower()
                            if query in text:
                                results.append(f"📝 [{file_type}] {sanitize_markdown(filename)}:\n{sanitize_markdown(text[:MAX_RESULT_LENGTH])}")
                    except Exception as e:
                        logger.error(f"⚠️ DOCX Error {filename}: {str(e)}")

                elif file_type == "Text" and filename.endswith(".txt"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            for line in f:
                                if query in line.lower():
                                    results.append(f"📜 [{file_type}] {sanitize_markdown(filename)}:\n{sanitize_markdown(line.strip()[:MAX_RESULT_LENGTH])}")
                    except Exception as e:
                        logger.error(f"⚠️ TXT Error {filename}: {str(e)}")

                elif file_type == "HTML" and filename.endswith(".html"):
                    text = await extract_text_from_html(file_path)
                    text = text.lower()
                    if query in text:
                        snippet = text[text.find(query):text.find(query)+MAX_RESULT_LENGTH]
                        results.append(f"🌐 [{file_type}] {sanitize_markdown(filename)}:\n{sanitize_markdown(snippet)}")

        if not results:
            return None

        final_result = "\n\n---\n\n".join(results)
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
            body = final_result[:4000]  # Limit to avoid SMTP errors
            await send_email(user_email, subject, body, user_id, lang)

        logger.info(f"✅ Document search for query: {query}, found {len(results)} results")
        return final_result
    except Exception as e:
        logger.error(f"❌ Unexpected error in document search for query {query}: {str(e)}")
        return None
