from telegram import Update, BotCommand
from telegram.ext import ContextTypes, CommandHandler

from studentbot.utils.db_utils import get_user_points, get_leaderboard
from studentbot.utils.text_formatter import get_translated_text


async def points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's points."""
    user_id = update.message.from_user.id
    points = get_user_points(user_id)
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(
        get_translated_text("points", lang).format(points=points)
    )


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the leaderboard."""
    board = get_leaderboard()
    lang = context.user_data.get("lang", "en")
    leaderboard_text = f"*{get_translated_text('leaderboard', lang)}*
\n"
    for i, user in enumerate(board):
        leaderboard_text += f"{i+1}. {user[0]}: {user[1]}\n"
    await update.message.reply_text(leaderboard_text, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Resets the leaderboard (admin only)."""
    admin_id = int(context.bot_data.get("admin_id", 0))
    if update.message.from_user.id == admin_id:
        reset_leaderboard()
        await update.message.reply_text("Leaderboard reset successfully.")
    else:
        await update.message.reply_text("You are not authorized to perform this action.")


async def set_gamification_commands(application) -> None:
    """Sets bot commands for gamification."""
    commands = [
        BotCommand("points", "View your points"),
        BotCommand("leaderboard", "View top users"),
        BotCommand("reset", "Reset leaderboard (admin only)"),
    ]
    await application.bot.set_my_commands(commands)


# Handlers to register

def get_gamification_handlers():
    return [
        CommandHandler("points", points),
        CommandHandler("leaderboard", leaderboard),
        CommandHandler("reset", reset),
    ]
