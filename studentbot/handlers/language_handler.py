import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the language selection process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        keyboard = [
            [
                InlineKeyboardButton("🇬🇧 English", callback_data="en"),
                InlineKeyboardButton("🇮🇹 Italiano", callback_data="it"),
                InlineKeyboardButton("🇮🇷 فارسی", callback_data="fa"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("language_selection", lang)),
            reply_markup=reply_markup,
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ Language selection form sent to user {user_id}")
        await award_points_for_action(user_id, "interaction")
    except TelegramError as e:
        logger.error(f"❌ Telegram error sending language form to user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection callback."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        selected_lang = query.data
        lang_map = {"en": "English", "it": "Italiano", "fa": "فارسی"}
        
        if selected_lang not in lang_map:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("invalid_language", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Invalid language selected by user {user_id}: {selected_lang}")
            return
        
        context.user_data["lang"] = selected_lang
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("language_set", selected_lang).format(lang=lang_map[selected_lang])),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ Language set to {selected_lang} for user {user_id}")
        await award_points_for_action(user_id, "language_selection")
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
                "Language Selection",
                f"Selected language: {lang_map[selected_lang]}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling language callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


def get_language_handler():
    """Return the language selection handler."""
    return [
        CommandHandler("language", language_selection),
        CallbackQueryHandler(language_callback, pattern="^(en|it|fa)$"),
    ]