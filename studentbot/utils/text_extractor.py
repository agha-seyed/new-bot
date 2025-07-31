import os
import logging
from typing import Optional
from datetime import datetime
import fitz
import docx
from bs4 import BeautifulSoup
import asyncio
from studentbot import config
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action

logger = logging.getLogger(__name__)

MAX_RESULT_LENGTH = 1000
MAX_TELEGRAM_MESSAGE_LENGTH = 4000

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

async def search_in_documents(query: str, user_id: int = None, lang: str = "en") -> Optional[str]:
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
            "HTML": "studentbot/assets/html"
        }

        loop = asyncio.get_event_loop()
        for file_type, dir_path in directories.items():
            if not os.path.exists(dir_path):
                continue

            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                try:
                    if file_type == "PDF" and filename.endswith(".pdf"):
                        doc = await loop.run_in_executor(None, fitz.open, file_path)
                        try:
                            for page in doc:
                                text = page.get_text().lower()
                                if query in text:
                                    snippet = text[max(0, text.find(query)-50):text.find(query)+MAX_RESULT_LENGTH]
                                    results.append(f"📄 [{file_type}] {sanitize_markdown(filename)}:\n{sanitize_markdown(snippet)}")
                        finally:
                            doc.close()

                    elif file_type == "Word" and filename.endswith(".docx"):
                        doc = await loop.run_in_executor(None, docx.Document, file_path)
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
                            snippet = text[max(0, text.find(query)-50):text.find(query)+MAX_RESULT_LENGTH]
                            results.append(f"🌐 [{file_type}] {sanitize_markdown(filename)}:\n{sanitize_markdown(snippet)}")
                except Exception as e:
                    logger.error(f"⚠️ Error processing {file_type} file {filename}: {str(e)}")

        if not results:
            return get_translated_text("search_failed", lang)

        final_result = "\n\n---\n\n".join(results)
        if len(final_result) > MAX_TELEGRAM_MESSAGE_LENGTH:
            final_result = final_result[:MAX_TELEGRAM_MESSAGE_LENGTH-3] + "..."

        if user_id:
            await award_points_for_action(user_id, "interaction")
            await gsheets_client.add_interaction_to_sheet(
                config.QUESTIONS_SHEET_NAME,
                [
                    user_id, query, final_result[:1000], 0, "Documents", "N/A", "N/A",
                    "Document Search", f"Search query: {query}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )

        logger.info(f"✅ Search for '{query}' found {len(results)} results")
        return final_result
    except Exception as e:
        logger.error(f"❌ Error in document search for '{query}': {str(e)}")
        return get_translated_text("search_failed", lang)
