import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TelegramError
from config import config
from studentbot.utils.db_utils import get_all_consultation_requests, update_consultation_request_status, get_all_users, log_event
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.gamification_handler import award_points_for_action

logger = logging.getLogger(__name__)

async def is_admin(user_id: int) -> bool:
    """Check if the user is an admin."""
    return str(user_id) == config.ADMIN_CHAT_ID

async def admin_consultations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display all consultation requests for admin."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(get_translated_text("unauthorized", lang))
        logger.warning(f"⚠️ Unauthorized admin_consultations attempt by user {user_id}")
        return
    
    try:
        requests = await get_all_consultation_requests()
        if not requests:
            await update.message.reply_text(get_translated_text("no_consultation_requests", lang))
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
📌 *Request ID:* {req['id']}
👤 *User:* {sanitize_markdown(req['name'])}
🎓 *Field:* {sanitize_markdown(req['field_of_study'] or 'N/A')}
📊 *GPA:* {req['gpa'] or 'N/A'}
🌍 *Destination Country:* {sanitize_markdown(req['destination_country'] or 'N/A')}
🗂 *Status:* {sanitize_markdown(req['status'])}
📎 *File ID:* {sanitize_markdown(req['file_id'] or 'N/A')}
"""
            await update.message.reply_text(
                request_text.strip(),
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )
        logger.info(f"✅ Displayed consultation requests for admin {user_id}")
        await award_points_for_action(user_id, "admin_action")
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying consultations for admin {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying consultations for admin {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

async def archive_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Archive a consultation request."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(get_translated_text("unauthorized", lang))
        logger.warning(f"⚠️ Unauthorized archive attempt by user {user_id}")
        return
    
    query = update.callback_query
    await query.answer()
    
    try:
        request_id = int(query.data.split("_")[-1])
        await update_consultation_request_status(request_id, "archived")
        await query.message.reply_text(
            get_translated_text("consultation_archived", lang).format(request_id=request_id),
            reply_markup=ReplyKeyboardRemove(),
        )
        await log_event(user_id, "consultation_archived", f"Request ID: {request_id}")
        await award_points_for_action(user_id, "admin_action")
        logger.info(f"✅ Archived consultation request {request_id} by admin {user_id}")
    except ValueError:
        logger.error(f"❌ Invalid request ID format for admin {user_id}")
        await query.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Error archiving consultation request for admin {user_id}: {str(e)}")
        await query.message.reply_text(get_translated_text("error_occurred", lang))

async def reply_to_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiate replying to a consultation request."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(get_translated_text("unauthorized", lang))
        logger.warning(f"⚠️ Unauthorized reply attempt by user {user_id}")
        return
    
    query = update.callback_query
    await query.answer()
    
    try:
        request_id = int(query.data.split("_")[-1])
        context.user_data["awaiting_reply"] = {"request_id": request_id}
        await query.message.reply_text(
            get_translated_text("enter_reply_message", lang),
            reply_markup=ReplyKeyboardRemove(),
        )
        logger.info(f"✅ Admin {user_id} started replying to consultation {request_id}")
    except ValueError:
        logger.error(f"❌ Invalid request ID format for admin {user_id}")
        await query.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Error initiating reply for admin {user_id}: {str(e)}")
        await query.message.reply_text(get_translated_text("error_occurred", lang))

async def handle_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the reply message for a consultation request."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(get_translated_text("unauthorized", lang))
        return
    
    if not context.user_data.get("awaiting_reply"):
        await update.message.reply_text(get_translated_text("no_reply_context", lang))
        return
    
    try:
        request_id = context.user_data["awaiting_reply"]["request_id"]
        reply_text = update.message.text.strip()
        request = await get_consultation_requests(request_id)
        if not request:
            await update.message.reply_text(get_translated_text("request_not_found", lang))
            context.user_data.pop("awaiting_reply", None)
            return
        
        user_id_to_reply = request[0]["user_id"]
        await context.bot.send_message(
            chat_id=user_id_to_reply,
            text=f"📬 {get_translated_text('admin_reply', lang)}:\n{reply_text}",
        )
        await update_consultation_request_status(request_id, "responded")
        await update.message.reply_text(
            get_translated_text("consultation_responded", lang).format(request_id=request_id),
        )
        await log_event(user_id, "consultation_responded", f"Request ID: {request_id}, Reply: {reply_text}")
        await award_points_for_action(user_id, "admin_action")
        context.user_data.pop("awaiting_reply", None)
        logger.info(f"✅ Admin {user_id} replied to consultation {request_id}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error replying to consultation for admin {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error replying to consultation for admin {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

async def view_consultation_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the file associated with a consultation request."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(get_translated_text("unauthorized", lang))
        logger.warning(f"⚠️ Unauthorized file view attempt by user {user_id}")
        return
    
    query = update.callback_query
    await query.answer()
    
    try:
        request_id = int(query.data.split("_")[-1])
        requests = await get_all_consultation_requests()
        request = next((r for r in requests if r["id"] == request_id), None)
        if not request or not request["file_id"]:
            await query.message.reply_text(get_translated_text("no_file_found", lang))
            return
        
        file_url = f"https://drive.google.com/file/d/{request['file_id']}/view"
        await query.message.reply_text(
            get_translated_text("file_link", lang).format(file_url=file_url),
            parse_mode="MarkdownV2",
        )
        await log_event(user_id, "file_viewed", f"Request ID: {request_id}, File ID: {request['file_id']}")
        await award_points_for_action(user_id, "admin_action")
        logger.info(f"✅ Admin {user_id} viewed file for consultation {request_id}")
    except ValueError:
        logger.error(f"❌ Invalid request ID format for admin {user_id}")
        await query.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Error viewing file for admin {user_id}: {str(e)}")
        await query.message.reply_text(get_translated_text("error_occurred", lang))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiate broadcasting a message to users."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(get_translated_text("unauthorized", lang))
        logger.warning(f"⚠️ Unauthorized broadcast attempt by user {user_id}")
        return
    
    try:
        await update.message.reply_text(get_translated_text("enter_broadcast_message", lang))
        context.user_data["awaiting_broadcast"] = True
        logger.info(f"✅ Admin {user_id} started broadcast process")
    except TelegramError as e:
        logger.error(f"❌ Telegram error initiating broadcast for admin {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast message and field filter."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(get_translated_text("unauthorized", lang))
        return
    
    try:
        if context.user_data.get("awaiting_broadcast"):
            context.user_data["broadcast_text"] = update.message.text.strip()
            await update.message.reply_text(get_translated_text("enter_field_filter", lang))
            context.user_data["awaiting_field_filter"] = True
            context.user_data.pop("awaiting_broadcast")
            logger.info(f"✅ Admin {user_id} entered broadcast message")
        
        elif context.user_data.get("awaiting_field_filter"):
            field = update.message.text.strip()
            users = await get_all_users()
            filtered = users if field.lower() == get_translated_text("all", lang).lower() else [
                u for u in users if u["field_of_study"] and u["field_of_study"].lower() == field.lower()
            ]
            
            count = 0
            for u in filtered:
                try:
                    await update.get_bot().send_message(
                        chat_id=u["id"],
                        text=context.user_data["broadcast_text"],
                        parse_mode="MarkdownV2",
                    )
                    count += 1
                except TelegramError:
                    logger.warning(f"⚠️ Failed to send broadcast to user {u['id']}")
                    continue
            
            await update.message.reply_text(
                get_translated_text("broadcast_sent", lang).format(count=count),
            )
            await log_event(user_id, "broadcast_sent", f"Sent to {count} users, Field: {field}")
            await award_points_for_action(user_id, "admin_action")
            context.user_data.clear()
            context.user_data["lang"] = lang
            logger.info(f"✅ Admin {user_id} sent broadcast to {count} users")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling broadcast for admin {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error handling broadcast for admin {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

def get_admin_handler():
    """Return the admin handlers."""
    return [
        CommandHandler("admin_consultations", admin_consultations),
        CommandHandler("broadcast", broadcast),
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(user_id=int(config.ADMIN_CHAT_ID)), handle_broadcast_message),
        MessageHandler(filters.Regex("^📥 پاسخ") & filters.User(user_id=int(config.ADMIN_CHAT_ID)), reply_to_consultation),
        MessageHandler(filters.Regex("^🗂 بایگانی") & filters.User(user_id=int(config.ADMIN_CHAT_ID)), archive_consultation),
        MessageHandler(filters.Regex("^📁 فایل") & filters.User(user_id=int(config.ADMIN_CHAT_ID)), view_consultation_file),
        CallbackQueryHandler(archive_consultation, pattern="^archive_consult_"),
        CallbackQueryHandler(reply_to_consultation, pattern="^respond_consult_"),
        CallbackQueryHandler(view_consultation_file, pattern="^view_file_"),
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(user_id=int(config.ADMIN_CHAT_ID)), handle_reply_message),
    ]