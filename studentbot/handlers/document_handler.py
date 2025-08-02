import logging
import tempfile
from typing import Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TelegramError
from studentbot.utils.common import get_translated_text, sanitize_markdown  # Changed from text_formatter
from studentbot.utils.gdrive import gdrive_client
from studentbot.utils.db_utils import AsyncSessionLocal, get_user, log_event
from studentbot.utils.models_db import Document
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx", ".odt", ".csv", ".jpg", ".jpeg", ".png", ".gif"}
UPLOAD_CONFIRM, UPLOAD_CANCEL = range(2)

async def store_document(user_id: int, file_name: str, file_id: str, drive_url: str) -> None:
    """Store document metadata in the database using ORM."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                document = Document(
                    user_id=user_id,
                    file_name=file_name,
                    file_id=file_id,
                    drive_url=drive_url
                )
                session.add(document)
                await session.commit()
                logger.info(f"✅ Stored document metadata for user {user_id}: {file_name}")
    except Exception as e:
        logger.error(f"❌ Error storing document for user {user_id}: {str(e)}")
        raise

async def validate_file(document: 'telegram.Document') -> Optional[str]:
    """Validate uploaded file."""
    file_extension = os.path.splitext(document.file_name)[1].lower()
    file_size_mb = document.file_size / (1024 * 1024)
    if file_extension not in ALLOWED_EXTENSIONS:
        return f"Invalid file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    if file_size_mb > MAX_FILE_SIZE_MB:
        return f"File too large. Max size: {MAX_FILE_SIZE_MB} MB"
    return None

async def start_document_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the document submission process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("document_submission_prompt", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info(f"📎 User {user_id} started document submission")
        await award_points_for_action(user_id, "interaction")
        return UPLOAD_CONFIRM
    except TelegramError as e:
        logger.error(f"❌ Telegram error starting document submission for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle document submission and prompt for confirmation."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    document = update.message.document

    if not document:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("no_document_received", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ No document received from user {user_id}")
        return UPLOAD_CONFIRM

    validation_error = await validate_file(document)
    if validation_error:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_file", lang).format(error=validation_error)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid file by user {user_id}: {validation_error}")
        return UPLOAD_CONFIRM

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=document.file_name) as tmp_file:
            file_path = tmp_file.name
            file = await context.bot.get_file(document.file_id)
            await file.download_to_drive(file_path)
            drive_url = await gdrive_client.upload_file(file_path, user_id, document.file_name)  # Updated to match gdrive.py signature
            os.remove(file_path)
        
        context.user_data["document"] = {
            "file_name": document.file_name,
            "file_id": document.file_id,
            "drive_url": drive_url
        }
        
        keyboard = [
            [
                InlineKeyboardButton(get_translated_text("confirm", lang), callback_data="confirm_upload"),
                InlineKeyboardButton(get_translated_text("cancel", lang), callback_data="cancel_upload")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("confirm_document", lang).format(file_name=document.file_name)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        logger.info(f"📄 User {user_id} uploaded document: {document.file_name}")
        return UPLOAD_CONFIRM
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling document for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Error handling document for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("upload_failed", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def confirm_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle document upload confirmation."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        document_data = context.user_data.get("document")
        if not document_data:
            await query.message.reply_text(
                sanitize_markdown(get_translated_text("no_document_received", lang)),
                parse_mode="MarkdownV2"
            )
            return ConversationHandler.END
        
        # Store in database
        await store_document(
            user_id=user_id,
            file_name=document_data["file_name"],
            file_id=document_data["file_id"],
            drive_url=document_data["drive_url"]
        )
        
        # Notify admin
        admin_chat_id = config.ADMIN_CHAT_ID
        if admin_chat_id:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=sanitize_markdown(
                    get_translated_text("admin_document_uploaded", lang).format(
                        user_id=user_id,
                        file_name=document_data["file_name"],
                        drive_url=document_data["drive_url"]
                    )
                ),
                parse_mode="MarkdownV2"
            )
        
        # Store in Google Sheets
        user = await get_user(user_id)
        if user:
            interaction_data = [
                user_id,
                user.first_name,
                user.last_name or "N/A",
                user.age or 0,
                user.email or "N/A",
                user.field_of_study or "N/A",
                user.country or "N/A",
                "Document Upload",
                f"File: {document_data['file_name']}, Drive URL: {document_data['drive_url']}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
            await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("document_submission_complete", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        await award_points_for_action(user_id, "file_upload")
        await log_event(user_id, "document_uploaded", f"File: {document_data['file_name']}")
        logger.info(f"✅ User {user_id} confirmed document upload: {document_data['file_name']}")
        
        context.user_data.clear()
        context.user_data["lang"] = lang
        return ConversationHandler.END
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error confirming upload for user {user_id}: {str(e)}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Error confirming upload for user {user_id}: {str(e)}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("upload_failed", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel document submission."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("document_submission_cancelled", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        context.user_data["lang"] = lang
        logger.info(f"✅ User {user_id} cancelled document submission")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error cancelling document submission for user {user_id}: {str(e)}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

def get_document_handler():
    """Return the document submission handler."""
    return [
        ConversationHandler(
            entry_points=[CommandHandler("upload_document", start_document_submission)],
            states={
                UPLOAD_CONFIRM: [
                    MessageHandler(filters.Document.ALL, document_handler),
                    CallbackQueryHandler(confirm_upload, pattern="^confirm_upload$"),
                    CallbackQueryHandler(cancel_upload, pattern="^cancel_upload$")
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel_upload)]
        )
    ]
