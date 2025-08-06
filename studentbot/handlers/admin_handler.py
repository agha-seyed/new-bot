import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TelegramError
from studentbot import config
from studentbot.utils.db_utils import get_consultation_request_by_id, update_consultation_request_status, get_all_users, log_event, get_all_consultation_requests
from studentbot.utils.common import get_translated_text, sanitize_markdown  # Changed from text_formatter
from studentbot.handlers.gamification_handler import award_points_for_action

logger = logging.getLogger(__name__)

async def is_admin(user_id: int) -> bool:
    """Check if the user is an admin."""
    return str(user_id) == config.ADMIN_CHAT_ID

async def admin_consultations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display all consultation requests for admin."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("unauthorized", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Unauthorized admin_consultations attempt by user {user_id}")
        return
    
    try:
        requests = await get_all_consultation_requests()
        if not requests:
            await update.message.reply_text(
                sanitize_markdown(get_translated_text("no_consultation_requests", lang)),
                parse_mode="MarkdownV2"
            )
            return
        
        for req in requests:
            keyboard = [
                [
                    InlineKeyboardButton("📥 Respond", callback_data=f"respond_consult_{req['id']}"),
                    InlineKeyboardButton("🗑 Archive", callback_data=f"archive_consult_{req['id']}"),
                    InlineKeyboardButton("📁 View File", callback_data=f"view_file_{req['id']}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            request_text = f"""
📌 *Request ID:* {sanitize_markdown(str(req['id']))}
👤 *User:* {sanitize_markdown(req['name'])}
🎓 *Field:* {sanitize_markdown(req['field_of_study'] or 'N/A')}
📊 *GPA:* {sanitize_markdown(str(req['gpa']) or 'N/A')}
🌍 *Destination Country:* {sanitize_markdown(req['destination_country'] or 'N/A')}
🗂 *Status:* {sanitize_markdown(req['status'])}
📎 *File ID:* {sanitize_markdown(req['file_id'] or 'N/A')}
"""
            await update.message.reply_text(
                request_text.strip(),
                parse_mode="MarkdownV2",
                reply_markup=reply_markup
            )
        logger.info(f"✅ Displayed consultation requests for admin {user_id}")
        await award_points_for_action(user_id, "admin_action")
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying consultations for admin {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying consultations for admin {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def archive_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Archive a consultation request."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("unauthorized", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Unauthorized archive attempt by user {user_id}")
        return
    
    query = update.callback_query
    await query.answer()
    
    try:
        request_id = int(query.data.split("_")[-1])
        await update_consultation_request_status(request_id, "archived")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("consultation_archived", lang).format(request_id=request_id)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        await log_event(user_id, "consultation_archived", f"Request ID: {request_id}")
        await award_points_for_action(user_id, "admin_action")
        logger.info(f"✅ Archived consultation request {request_id} by admin {user_id}")
    except ValueError:
        logger.error(f"❌ Invalid request ID format for admin {user_id}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Error archiving consultation request for admin {user_id}: {str(e)}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def reply_to_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiate replying to a consultation request."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("unauthorized", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Unauthorized reply attempt by user {user_id}")
        return
    
    query = update.callback_query
    await query.answer()
    
    try:
        request_id = int(query.data.split("_")[-1])
        context.user_data["request_id"] = request_id
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("enter_reply_message", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info(f"✅ Admin {user_id} started replying to consultation {request_id}")
        return AWAITING_REPLY
    except ValueError:
        logger.error(f"❌ Invalid request ID format for admin {user_id}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Error initiating reply for admin {user_id}: {str(e)}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def handle_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the reply message for a consultation request."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("unauthorized", lang)),
            parse_mode="MarkdownV2"
        )
        return
    
    try:
        request_id = context.user_data.pop("request_id", None)
        if not request_id:
            return ConversationHandler.END

        reply_text = update.message.text.strip()
        request = await get_consultation_request_by_id(request_id)
        if not request:
            await update.message.reply_text(
                sanitize_markdown(get_translated_text("request_not_found", lang)),
                parse_mode="MarkdownV2"
            )
            return ConversationHandler.END
        
        user_id_to_reply = request["user_id"]
        await context.bot.send_message(
            chat_id=user_id_to_reply,
            text=sanitize_markdown(f"📬 {get_translated_text('admin_reply', lang)}:\n{reply_text}"),
            parse_mode="MarkdownV2"
        )
        await update_consultation_request_status(request_id, "responded")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("consultation_responded", lang).format(request_id=request_id)),
            parse_mode="MarkdownV2"
        )
        await log_event(user_id, "consultation_responded", f"Request ID: {request_id}, Reply: {reply_text}")
        await award_points_for_action(user_id, "admin_action")
        logger.info(f"✅ Admin {user_id} replied to consultation {request_id}")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error replying to consultation for admin {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error replying to consultation for admin {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def view_consultation_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the file associated with a consultation request."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("unauthorized", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Unauthorized file view attempt by user {user_id}")
        return
    
    query = update.callback_query
    await query.answer()
    
    try:
        request_id = int(query.data.split("_")[-1])
        request = await get_consultation_request_by_id(request_id)
        if not request or not request["file_id"]:
            await query.message.reply_text(
                sanitize_markdown(get_translated_text("no_file_found", lang)),
                parse_mode="MarkdownV2"
            )
            return
        
        file_url = f"https://drive.google.com/file/d/{sanitize_markdown(request['file_id'])}/view"
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("file_link", lang).format(file_url=file_url)),
            parse_mode="MarkdownV2"
        )
        await log_event(user_id, "file_viewed", f"Request ID: {request_id}, File ID: {request['file_id']}")
        await award_points_for_action(user_id, "admin_action")
        logger.info(f"✅ Admin {user_id} viewed file for consultation {request_id}")
    except ValueError:
        logger.error(f"❌ Invalid request ID format for admin {user_id}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Error viewing file for admin {user_id}: {str(e)}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiate broadcasting a message to users."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("unauthorized", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Unauthorized broadcast attempt by user {user_id}")
        return
    
    try:
        context.user_data["broadcast_state"] = AWAITING_BROADCAST_MESSAGE
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("enter_broadcast_message", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ Admin {user_id} started broadcast process")
        return AWAITING_BROADCAST_MESSAGE
    except TelegramError as e:
        logger.error(f"❌ Telegram error initiating broadcast for admin {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle broadcast message."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("unauthorized", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    
    try:
        broadcast_text = update.message.text.strip()
        users = await get_all_users()
        
        count = 0
        for u in users:
            try:
                await update.get_bot().send_message(
                    chat_id=u["id"],
                    text=sanitize_markdown(broadcast_text),
                    parse_mode="MarkdownV2"
                )
                count += 1
            except TelegramError:
                logger.warning(f"⚠️ Failed to send broadcast to user {u['id']}")
                continue

        await update.message.reply_text(
            sanitize_markdown(get_translated_text("broadcast_sent", lang).format(count=count)),
            parse_mode="MarkdownV2"
        )
        await log_event(user_id, "broadcast_sent", f"Sent to {count} users")
        await award_points_for_action(user_id, "admin_action")
        context.user_data.clear()
        context.user_data["lang"] = lang
        logger.info(f"✅ Admin {user_id} sent broadcast to {count} users")
        return ConversationHandler.END
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling broadcast for admin {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error handling broadcast for admin {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

(
    AWAITING_REPLY,
    AWAITING_BROADCAST_MESSAGE,
    AWAITING_FIELD_FILTER,
) = range(3)

def get_admin_handler():
    """Return the admin handlers."""
    return [
        CommandHandler("admin_consultations", admin_consultations),
        CallbackQueryHandler(archive_consultation, pattern="^archive_consult_"),
        CallbackQueryHandler(view_consultation_file, pattern="^view_file_"),
        ConversationHandler(
            entry_points=[
                CommandHandler("broadcast", broadcast),
                CallbackQueryHandler(reply_to_consultation, pattern="^respond_consult_"),
            ],
            states={
                AWAITING_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_message)],
                AWAITING_BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message)],
                AWAITING_FIELD_FILTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message)],
            },
            fallbacks=[CommandHandler("cancel", cancel_conversation)],
        ),
    ]

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current admin conversation."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id

    await update.message.reply_text(
        sanitize_markdown(get_translated_text("conversation_cancelled", lang)),
        parse_mode="MarkdownV2"
    )
    context.user_data.clear()
    context.user_data["lang"] = lang
    logger.info(f"✅ Admin conversation cancelled by user {user_id}")
    return ConversationHandler.END
