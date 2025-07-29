import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gdrive import upload_file
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx", ".odt", ".csv", ".jpg", ".jpeg", ".png", ".gif"}


async def start_document_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the document submission process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("document_submission_prompt", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} started document submission")
        await award_points_for_action(user_id, "interaction")
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the document submission."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    document = update.message.document

    if not document:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("no_document_received", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ No document received from user {user_id}")
        return

    file_extension = os.path.splitext(document.file_name)[1].lower()
    file_size_mb = document.file_size / (1024 * 1024)

    if file_extension not in ALLOWED_EXTENSIONS:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_file_format", lang).format(allowed=",".join(ALLOWED_EXTENSIONS))),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid file format by user {user_id}: {file_extension}")
        return

    if file_size_mb > MAX_FILE_SIZE_MB:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("file_too_large", lang).format(max_size=MAX_FILE_SIZE_MB)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ File too large by user {user_id}: {file_size_mb:.2f} MB")
        return

    try:
        file = await context.bot.get_file(document.file_id)
        file_path = f"uploads/{document.file_name}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        await file.download_to_drive(file_path)
        
        # Upload to Google Drive
        drive_url = upload_file(file_path, document.file_name)
        
        # Notify admin
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if admin_chat_id:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=sanitize_markdown(
                    get_translated_text("admin_document_uploaded", lang).format(
                        user_id=user_id,
                        file_name=document.file_name,
                        drive_url=drive_url
                    )
                ),
                parse_mode="MarkdownV2"
            )
        
        # Clean up
        os.remove(file_path)
        
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("document_submission_complete", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} uploaded document: {document.file_name}")
        await award_points_for_action(user_id, "file_upload")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                "N/A",
                "N/A",
                0,
                "N/A",
                "N/A",
                "N/A",
                "Document Upload",
                f"File: {document.file_name}, Drive URL: {drive_url}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Error handling document for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("upload_failed", lang)),
            parse_mode="MarkdownV2"
        )


def get_document_handler():
    """Return the document submission handler."""
    return [
        CommandHandler("upload_document", start_document_submission),
        MessageHandler(filters.Document.ALL, document_handler),
    ]