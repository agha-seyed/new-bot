import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError
from studentbot.utils.common import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import (
    get_user,
    delete_user,
    get_user_points,
    get_user_level,
    get_user_activity_stats,
    AsyncSessionLocal,
    log_event
)
from studentbot.utils.gsheets import gsheets_client, delete_user_from_sheet
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

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

            created_at = "N/A"
            if user.created_at:
                try:
                    created_at = user.created_at.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    created_at = sanitize_markdown(str(user.created_at))

            profile_text = f"""
👤 *{sanitize_markdown(get_translated_text("first_name", lang))}*: {sanitize_markdown(user.first_name)}
👥 *{sanitize_markdown(get_translated_text("last_name", lang))}*: {sanitize_markdown(user.last_name or "N/A")}
🎂 *{sanitize_markdown(get_translated_text("age", lang))}*: {user.age or "N/A"}
📧 *{sanitize_markdown(get_translated_text("email", lang))}*: {sanitize_markdown(user.email or "N/A")}
🌍 *{sanitize_markdown(get_translated_text("country", lang))}*: {sanitize_markdown(user.country or "N/A")}
📚 *{sanitize_markdown(get_translated_text("field_of_study", lang))}*: {sanitize_markdown(user.field_of_study or "N/A")}
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
            interaction_data = [
                user_id,
