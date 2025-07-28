from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import get_user, delete_user
from studentbot.utils.gsheets import delete_user_from_sheet


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's profile."""
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    user = get_user(user_id)

    if user:
        profile_text = f"""
*First Name:* {sanitize_markdown(user[1])}
*Last Name:* {sanitize_markdown(user[2])}
*Age:* {user[3]}
*Email:* {sanitize_markdown(user[4])}
*Country:* {sanitize_markdown(user[5])}
*Field of Study:* {sanitize_markdown(user[6])}
        """
        keyboard = [
            [get_translated_text("edit_profile", lang)],
            [get_translated_text("delete_profile", lang)],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            profile_text, parse_mode="MarkdownV2", reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(get_translated_text("not_registered", lang))


async def delete_profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes the user's profile."""
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    delete_user(user_id)
    delete_user_from_sheet("users", user_id)
    await update.message.reply_text(get_translated_text("profile_deleted", lang))
