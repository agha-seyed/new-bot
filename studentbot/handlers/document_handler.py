import os
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from utils.text_formatter import get_translated_text
from utils.gdrive import upload_file

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx", ".odt", ".csv", ".jpg", ".jpeg", ".png", ".gif"}

async def start_document_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the document submission process."""
    lang = context.user_data.get("lang", "en")
    logger.info("Document submission started for user %s", update.effective_user.id)
    await update.message.reply_text(get_translated_text("document_submission_prompt", lang))


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the document submission."""
    lang = context.user_data.get("lang", "en")
    document = update.message.document

    if not document:
        logger.warning("No document received from user %s", update.effective_user.id)
        await update.message.reply_text(get_translated_text("no_document_received", lang))
        return

    file_extension = os.path.splitext(document.file_name)[1].lower()
    file_size_mb = document.file_size / (1024 * 1024)

    if file_extension not in ALLOWED_EXTENSIONS:
        logger.warning("Invalid file format: %s", file_extension)
        await update.message.reply_text(get_translated_text("invalid_file_format", lang))
        return

    if file_size_mb > MAX_FILE_SIZE_MB:
        logger.warning("File too large: %.2f MB", file_size_mb)
        await update.message.reply_text(get_translated_text("file_too_large", lang))
        return

    try:
        file = await context.bot.get_file(document.file_id)
        file_path = document.file_name
        await file.download_to_drive(file_path)
        upload_file(file_path, document.file_name)
        os.remove(file_path)
        logger.info("File uploaded successfully: %s", document.file_name)
        await update.message.reply_text(get_translated_text("document_submission_complete", lang))
    except Exception as e:
        logger.exception("Error handling document: %s", e)
        await update.message.reply_text(get_translated_text("upload_failed", lang))


def get_document_handler():
    """Returns the document submission handler."""
    return [
        CommandHandler("upload_document", start_document_submission),
        MessageHandler(filters.Document.ALL, document_handler),
    ]
