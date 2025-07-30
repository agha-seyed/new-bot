import logging
from typing import List
from telegram import Update, BotCommand
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError
from sqlalchemy import text
from studentbot import config
from studentbot.utils.db_utils import get_user_points, get_user_level, get_leaderboard, add_points, AsyncSessionLocal
from datetime import datetime

logger = logging.getLogger(__name__)

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's points and level."""
    from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown  # Import داخل تابع
    from studentbot.utils.gsheets import gsheets_client  # Import داخل تابع
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        points = await get_user_points(user_id)
        level = await get_user_level(user_id)
        message = get_translated_text("points", lang).format(points=points, level=level)
        await update.message.reply_text(sanitize_markdown(message), parse_mode="MarkdownV2")
        logger.info(f"✅ Displayed points ({points}) and level ({level}) for user {user_id}")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [user_id, "N/A", "N/A", 0, "N/A", "N/A", "N/A", "Viewed Points", f"Points: {points}, Level: {level}", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")]
        )
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying points for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying points for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the top 10 users by points with their levels."""
    from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown  # Import داخل تابع
    from studentbot.utils.gsheets import gsheets_client  # Import داخل تابع
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    try:
        board = await get_leaderboard()
        if not board:
            await update.message.reply_text(get_translated_text("empty_leaderboard", lang))
            return
        
        leaderboard_text = f"*{sanitize_markdown(get_translated_text('leaderboard', lang))}*\n\n"
        for i, user in enumerate(board):
            leaderboard_text += (
                f"{i+1}. *{sanitize_markdown(user['first_name'])} {sanitize_markdown(user['last_name'])}* "
                f"- {user['points']} {sanitize_markdown(get_translated_text('points', lang).split()[0])} "
                f"({sanitize_markdown(user['level'])})\n"
            )
        await update.message.reply_text(leaderboard_text, parse_mode="MarkdownV2")
        logger.info(f"✅ Displayed leaderboard for user {user_id}")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [user_id, "N/A", "N/A", 0, "N/A", "N/A", "N/A", "Viewed Leaderboard", "Top 10 users", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")]
        )
        await award_points_for_action(user_id, "interaction")
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying leaderboard: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying leaderboard: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

async def reset_leaderboard() -> None:
    """Reset all users' points and levels in the database."""
    from studentbot.utils.gsheets import gsheets_client  # Import داخل تابع
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("UPDATE users SET points = 0, score = 0, level = '🎓 Newbie'")
                )
                logger.info("✅ Leaderboard reset successfully")
                await gsheets_client.add_interaction_to_sheet(
                    config.QUESTIONS_SHEET_NAME,
                    [0, "Admin", "Admin", 0, "N/A", "N/A", "N/A", "Reset Leaderboard", "All points and levels reset", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")]
                )
    except Exception as e:
        logger.error(f"❌ Error resetting leaderboard: {str(e)}")
        raise

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset the leaderboard (admin only)."""
    from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown  # Import داخل تابع
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    if not config.ADMIN_CHAT_ID or str(user_id) != config.ADMIN_CHAT_ID:
        await update.message.reply_text(get_translated_text("unauthorized", lang))
        logger.warning(f"⚠️ Unauthorized reset attempt by user {user_id}")
        return
    
    try:
        await reset_leaderboard()
        await update.message.reply_text(get_translated_text("leaderboard_reset", lang))
        logger.info(f"✅ User {user_id} reset the leaderboard")
        await award_points_for_action(user_id, "admin_action")
    except TelegramError as e:
        logger.error(f"❌ Telegram error resetting leaderboard for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error resetting leaderboard for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

async def award_points_for_action(user_id: int, action: str) -> None:
    """Award points to a user based on their action."""
    from studentbot.utils.gsheets import gsheets_client  # Import داخل تابع
    points_map = {
        "registration": 10,        # For user registration
        "consultation": 20,        # For submitting a consultation request
        "file_upload": 15,         # For uploading a file
        "feedback": 5,             # For providing feedback
        "interaction": 2,          # For general interactions (e.g., viewing calendar, guide, or asking questions)
        "isee_calculation": 10,    # For calculating ISEE
        "tts": 5,                  # For using text-to-speech
        "stt": 5,                  # For using speech-to-text
        "admin_action": 5,         # For admin actions (e.g., archiving, responding, broadcasting)
    }
    
    points = points_map.get(action, 0)
    if points > 0:
        try:
            await add_points(user_id, points)
            logger.info(f"✅ Awarded {points} points to user {user_id} for action '{action}'")
            await gsheets_client.add_interaction_to_sheet(
                config.QUESTIONS_SHEET_NAME,
                [user_id, "N/A", "N/A", 0, "N/A", "N/A", "N/A", f"Action: {action}", f"Awarded {points} points", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")]
            )
        except Exception as e:
            logger.error(f"❌ Error awarding {points} points to user {user_id} for action '{action}': {str(e)}")

async def set_gamification_commands(application) -> None:
    """Set bot commands for gamification with localized descriptions."""
    from studentbot.utils.text_formatter import get_translated_text  # Import داخل تابع
    languages = ["en", "fa", "it"]
    commands_by_lang = {}
    
    for lang in languages:
        commands = [
            BotCommand("points", get_translated_text("points_command_desc", lang)),
            BotCommand("leaderboard", get_translated_text("leaderboard_command_desc", lang)),
            BotCommand("reset", get_translated_text("reset_command_desc", lang)),
        ]
        commands_by_lang[lang] = commands
    
    try:
        await application.bot.set_my_commands(commands_by_lang["en"])
        logger.info("✅ Set gamification commands for English")
        # Add commands for other languages if needed
        for lang in languages[1:]:
            await application.bot.set_my_commands(commands_by_lang[lang], language_code=lang)
            logger.info(f"✅ Set gamification commands for {lang}")
    except TelegramError as e:
        logger.error(f"❌ Error setting gamification commands: {str(e)}")

def get_gamification_handlers():
    """Return the list of gamification command handlers."""
    return [
        CommandHandler("points", points),
        CommandHandler("leaderboard", leaderboard),
        CommandHandler("reset", reset),
    ]
