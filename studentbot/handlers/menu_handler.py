from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from utils.text_formatter import get_translated_text


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the main menu."""
    lang = context.user_data.get("lang", "en")
    keyboard = [
        [get_translated_text("scholarships_menu", lang), get_translated_text("migration_menu", lang)],
        [get_translated_text("housing_menu", lang), get_translated_text("documents_menu", lang)],
        [get_translated_text("consulting_menu", lang), get_translated_text("upload_document_menu", lang)],
        [get_translated_text("isee_menu", lang), get_translated_text("deadlines_menu", lang)],
        [get_translated_text("weather_menu", lang), get_translated_text("search_menu", lang)],
        [get_translated_text("news_menu", lang), get_translated_text("cost_of_living_menu", lang)],
        [get_translated_text("language_courses_menu", lang), get_translated_text("feedback_menu", lang)],
        [get_translated_text("gamification_menu", lang)],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(get_translated_text("main_menu", lang), reply_markup=reply_markup)
