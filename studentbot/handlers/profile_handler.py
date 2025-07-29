import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import (
    get_user,
    delete_user,
    get_user_points,
    get_user_level,
    get_user_activity_stats,
    AsyncSessionLocal
)
from studentbot.utils.gsheets import gsheets_client, delete_user_from_sheet
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


def get_level_badge(level: int) -> str:
    """Return a badge based on user level."""
    if level <= 5:
        return "🧱 Beginner"
    elif level <= 10:
        return "🥉 Bronze"
    elif level <= 20:
        return "🥈 Silver"
    elif level <= 30:
        return "🥇 Gold"
    else:
        return "🏅 Champion"


def get_progress_bar(level: int) -> str:
    """Generate a progress bar based on user level."""
    full = "🔵"
    empty = "⚪"
    total = 5
    filled = min(level % total, total)
    return full * filled + empty * (total - filled)


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's profile with interactive options."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        async with AsyncSessionLocal() as session:
            user = await get_user(session, user_id)
            if not user:
                await update.message.reply_text(
                    sanitize_markdown(get_translated_text("not_registered", lang)),
                    parse_mode="MarkdownV2"
                )
                return

            level = await get_user_level(session, user_id)
            points = await get_user_points(session, user_id)
            stats = await get_user_activity_stats(session, user_id)

            # Format registration time
            created_at = "N/A"
            if user.created_at:
                try:
                    created_at = user.created_at.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    created_at = sanitize_markdown(str(user.created_at))

            profile_text = f"""
👤 *{sanitize_markdown(get_translated_text("first_name", lang))}*: {sanitize_markdown(user.first_name)}
👥 *{sanitize_markdown(get_translated_text("last_name", lang))}*: {sanitize_markdown(user.last_name)}
🎂 *{sanitize_markdown(get_translated_text("age", lang))}*: {user.age}
📧 *{sanitize_markdown(get_translated_text("email", lang))}*: {sanitize_markdown(user.email)}
🌍 *{sanitize_markdown(get_translated_text("country", lang))}*: {sanitize_markdown(user.country)}
📚 *{sanitize_markdown(get_translated_text("field_of_study", lang))}*: {sanitize_markdown(user.field_of_study)}
🕒 *{sanitize_markdown(get_translated_text("registration_time", lang))}*: {created_at}
🏆 *{sanitize_markdown(get_translated_text("points", lang))}*: {points}
🚀 *{sanitize_markdown(get_translated_text("level", lang))}*: {level} ({get_level_badge(level)})
📈 *{sanitize_markdown(get_translated_text("progress", lang))}*: {get_progress_bar(level)}
❓ *{sanitize_markdown(get_translated_text("questions_asked", lang))}*: {stats.get("questions_asked", 0)}
📬 *{sanitize_markdown(get_translated_text("answers_received", lang))}*: {stats.get("answers_received", 0)}
            """

            keyboard = [
                [
                    InlineKeyboardButton(get_translated_text("edit_profile", lang), callback_data="edit_profile"),
                    InlineKeyboardButton(get_translated_text("delete_profile", lang), callback_data="delete_profile")
                ],
                [InlineKeyboardButton(get_translated_text("upload_document_menu", lang), callback_data="upload_document")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                profile_text.strip(),
                parse_mode="MarkdownV2",
                reply_markup=reply_markup
            )
            logger.info(f"✅ Profile displayed for user {user_id}")
            await award_points_for_action(user_id, "interaction")
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
                    "Profile View",
                    "Viewed user profile",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying profile for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying profile for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle profile-related callbacks."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        if query.data == "delete_profile":
            async with AsyncSessionLocal() as session:
                await delete_user(session, user_id)
                await delete_user_from_sheet("users", user_id)
            
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("profile_deleted", lang)),
                parse_mode="MarkdownV2"
            )
            logger.info(f"✅ User {user_id} deleted their profile")
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
                    "Profile Deletion",
                    "Deleted user profile",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )
        elif query.data in ["edit_profile", "upload_document"]:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text(f"start_{query.data}", lang)),
                parse_mode="MarkdownV2"
            )
            logger.info(f"✅ User {user_id} triggered {query.data}")
        else:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("invalid_selection", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Invalid callback by user {user_id}: {query.data}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling profile callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


def get_profile_handler():
    """Return the profile handler."""
    return [
        CommandHandler("profile", profile),
        CallbackQueryHandler(profile_callback, pattern="^(edit_profile|delete_profile|upload_document)$"),
    ]