from telegram import Update
from telegram.ext import ContextTypes

from studentbot.utils.db_utils import get_user_points, get_leaderboard
from studentbot.utils.text_formatter import get_translated_text


async def points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's points."""
    user_id = update.message.from_user.id
    points = get_user_points(user_id)
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("points", lang).format(points=points))


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the leaderboard."""
    leaderboard = get_leaderboard()
    lang = context.user_data.get("lang", "en")
    leaderboard_text = f"*{get_translated_text('leaderboard', lang)}*\n\n"
    for i, user in enumerate(leaderboard):
        leaderboard_text += f"{i+1}. {user[0]}: {user[1]}\n"
    await update.message.reply_text(leaderboard_text, parse_mode="Markdown")
