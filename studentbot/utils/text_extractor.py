import os
import logging
from datetime import datetime
import fitz  # PyMuPDF
import docx
import asyncio
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

MAX_RESULT_LENGTH = 1000  # max characters to return to avoid Telegram overflow


async def search_in_documents(query: str, user_id: int = None, lang: str = "en") -> str | None:
    """Searches for a query in PDF and Word documents in the assets folder."""
    try:
        query = query.strip().lower()
        results = []

        pdf_dir = "studentbot/assets/pdfs"
        docx_dir = "studentbot/assets/docs"

        # Search in PDFs
        if os.path.exists(pdf_dir):
            for filename in os.listdir(pdf_dir):
                if filename.lower().endswith(".pdf"):
                    try:
                        doc = await asyncio.get_event_loop().run_in_executor(None, fitz.open, os.path.join(pdf_dir, filename))
                        for page in doc:
                            text = page.get_text().lower()
                            if query in text:
                                snippet = text[text.find(query):text.find(query)+MAX_RESULT_LENGTH]
                                results.append(f"📄 [PDF] {sanitize_markdown(filename)}:\n{sanitize_markdown(snippet)}")
                    except Exception as e:
                        logger.error(f"⚠️ Error reading PDF {filename}: {str(e)}")

        # Search in Word files
        if os.path.exists(docx_dir):
            for filename in os.listdir(docx_dir):
                if filename.lower().endswith(".docx"):
                    try:
                        doc = await asyncio.get_event_loop().run_in_executor(None, docx.Document, os.path.join(docx_dir, filename))
                        for para in doc.paragraphs:
                            text = para.text.strip().lower()
                            if query in text:
                                results.append(f"📝 [DOCX] {sanitize_markdown(filename)}:\n{sanitize_markdown(text[:MAX_RESULT_LENGTH])}")
                    except Exception as e:
                        logger.error(f"⚠️ Error reading DOCX {filename}: {str(e)}")

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
                    "N/A",
                    "N/A",
                    "Document Search",
                    f"Document search result for {query}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )
        logger.info(f"✅ Document search for query: {query}, found {len(results)} results")
        return final_result
    except Exception as e:
        logger.error(f"❌ Unexpected error in document search for query {query}: {str(e)}")
        return None