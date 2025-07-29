from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..utils.text_formatter import get_translated_text
from ..utils.gsheets import add_user_to_sheet
from ..utils.db_utils import add_score, update_user_level


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a feedback form."""
    lang = context.user_data.get("lang", "en")
    keyboard = [
        [
            InlineKeyboardButton(
                get_translated_text("excellent", lang), callback_data="excellent"
            ),
            InlineKeyboardButton(
                get_translated_text("average", lang), callback_data="average"
            ),
            InlineKeyboardButton(
                get_translated_text("poor", lang), callback_data="poor"
            ),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_translated_text("feedback_prompt", lang), reply_markup=reply_markup
    )


async def feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the feedback callback."""
    query = update.callback_query
    await query.answer()
    add_user_to_sheet("feedback", [query.from_user.id, query.data])

    # Add score
    add_score(query.from_user.id, 3)
    update_user_level(query.from_user.id)

    lang = context.user_data.get("lang", "en")
    await query.edit_message_text(text=get_translated_text("feedback_thanks", lang))


def get_feedback_handler():
    """Returns the feedback handler."""
    return [
        CommandHandler("feedback", feedback),
        CallbackQueryHandler(feedback_callback),
    ]
