import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from studentbot.utils.text_formatter import get_translated_text
from studentbot.utils.gsheets import add_user_to_sheet
from studentbot.utils.db_utils import add_score, update_user_level

logger = logging.getLogger(__name__)


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a feedback form."""
    lang = context.user_data.get("lang", "en")
    try:
        keyboard = [
            [
                InlineKeyboardButton(get_translated_text("excellent", lang), callback_data="excellent"),
                InlineKeyboardButton(get_translated_text("average", lang), callback_data="average"),
                InlineKeyboardButton(get_translated_text("poor", lang), callback_data="poor"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(get_translated_text("feedback_prompt", lang), reply_markup=reply_markup)
        logger.info(f"Feedback form sent to user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error sending feedback form: {e}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))


async def feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the feedback callback."""
    query = update.callback_query
    lang = context.user_data.get("lang", "en")
    await query.answer()

    try:
        feedback_choice = query.data
        user_id = query.from_user.id

        add_user_to_sheet("feedback", [user_id, feedback_choice])
        add_score(user_id, 3)
        update_user_level(user_id)

        await query.edit_message_text(text=get_translated_text("feedback_thanks", lang))
        logger.info(f"Feedback '{feedback_choice}' submitted by user {user_id}")
    except Exception as e:
        logger.error(f"Error handling feedback callback: {e}")
        await query.edit_message_text(text=get_translated_text("error_occurred", lang))


def get_feedback_handler():
    """Returns the feedback handler."""
    return [
        CommandHandler("feedback", feedback),
        CallbackQueryHandler(feedback_callback),
    ]
