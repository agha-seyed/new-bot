


from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import (
    get_user,
    delete_user,
    get_user_points,
    get_user_level,
    get_user_activity_stats,
)
from studentbot.utils.gsheets import delete_user_from_sheet


def get_level_badge(level: int) -> str:
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
    full = "🔵"
    empty = "⚪️"
    total = 5
    filled = min(level % total, total)
    return full * filled + empty * (total - filled)


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    user = get_user(user_id)

    if user:
        level = get_user_level(user_id)
        points = get_user_points(user_id)
        stats = get_user_activity_stats(user_id)

        profile_text = f"""
👤 *{get_translated_text("first_name", lang)}:* {sanitize_markdown(user[1])}
👥 *{get_translated_text("last_name", lang)}:* {sanitize_markdown(user[2])}
🎂 *{get_translated_text("age", lang)}:* {user[3]}
📧 *{get_translated_text("email", lang)}:* {sanitize_markdown(user[4])}
🌍 *{get_translated_text("country", lang)}:* {sanitize_markdown(user[5])}
📚 *{get_translated_text("field_of_study", lang)}:* {sanitize_markdown(user[6])}

🏆 *{get_translated_text("points", lang)}:* {points}
🚀 *{get_translated_text("level", lang)}:* {level} ({get_level_badge(level)})
📈 *{get_translated_text("progress", lang)}:* {get_progress_bar(level)}

❓ *{get_translated_text("questions_asked", lang)}:* {stats.get("questions_asked", 0)}
📬 *{get_translated_text("answers_received", lang)}:* {stats.get("answers_received", 0)}
        """

        keyboard = [
            [f"✏️ {get_translated_text('edit_profile', lang)}"],
            [f"🗑️ {get_translated_text('delete_profile', lang)}"],
            [f"📤 {get_translated_text('upload_document_menu', lang)}"],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            profile_text.strip(), parse_mode="MarkdownV2", reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(get_translated_text("not_registered", lang))


async def delete_profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    delete_user(user_id)
    delete_user_from_sheet("users", user_id)
    await update.message.reply_text(get_translated_text("profile_deleted", lang))
