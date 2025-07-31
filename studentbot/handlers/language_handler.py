import logging
from typing import List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import AsyncSessionLocal, get_user, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config
from pathlib import Path
from datetime import datetime
from sqlalchemy import update
from studentbot.utils.models_db import User

logger = logging.getLogger(__name__)

async def get_available_languages() -> List[Tuple[str, str]]:
    """Load available languages dynamically from lang/ directory."""
    lang_dir = Path(__file__).resolve().parent.parent / "lang"
    languages = []
    try:
        for file in lang_dir.glob("*.json"):
            lang_code = file.stem
            lang_name = {
                "en": "🇬🇧 English",
                "fa": "🇮🇷 فارسی",
                "it": "🇮🇹 Italiano"
            }.get(lang_code, lang_code)
            languages.append((lang_name, lang_code))
        if not languages:
            logger.warning("⚠️ No language files found in lang/ directory")
        return languages
    except Exception as e:
        logger.error(f"❌ Error loading language files: {str(e)}")
        return [("🇬🇧 English", "en")]  # Fallback to English

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the language selection menu."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    logger.info(f"🌐 Language selection started by user {user_id}")

    try:
        languages = await get_available_languages()
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"lang_{code}")]
            for name, code in languages
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("select_language", lang)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        await log_event(user_id, "language_menu_accessed", "Opened language selection menu")
        await award_points_for_action(user_id, "interaction")
        logger.info(f"✅ Language selection menu displayed for user {user_id}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying language menu for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying language menu for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection callback."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    new_lang = query.data.split("_", 1)[1]

    try:
        languages = await get_available_languages()
        if new_lang not in [code for _, code in languages]:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("invalid_language", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Invalid language selected by user {user_id}: {new_lang}")
            return

        # Update user language in database
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    update(User).where(User.id == user_id).values(lang=new_lang)
                )
                logger.info(f"✅ Updated language to {new_lang} for user {user_id}")

        context.user_data["lang"] = new_lang
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("language_updated", new_lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )

        # Log interaction in Google Sheets
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
                "Language Selection",
                f"Changed language to {new_lang}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
            await gsheets_client.add_consultation_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)

        await award_points_for_action(user_id, "interaction")
        await log_event(user_id, "language_changed", f"Language changed to {new_lang}")
        logger.info(f"✅ User {user_id} changed language to {new_lang}")

    except TelegramError as e:
        logger.error(f"❌ Telegram error in language callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in language callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

def get_language_handler():
    """Return the language handler."""
    return [
        CommandHandler("language", language),
        CallbackQueryHandler(language_callback, pattern="^lang_")
    ]
