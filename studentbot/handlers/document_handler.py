import os
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from utils.text_formatter import get_translated_text
from utils.gdrive import upload_file


async def start_document_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the document submission process."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("document_submission_prompt", lang))


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the document submission."""
    lang = context.user_data.get("lang", "en")
    document = update.message.document
    file = await context.bot.get_file(document.file_id)
    file_path = f"{document.file_name}"
    await file.download_to_drive(file_path)
    upload_file(file_path, document.file_name)
    os.remove(file_path)
    await update.message.reply_text(get_translated_text("document_submission_complete", lang))


def get_document_handler():
    """Returns the document submission handler."""
    return [
        CommandHandler("upload_document", start_document_submission),
        MessageHandler(filters.Document.ALL, document_handler),
    ]
