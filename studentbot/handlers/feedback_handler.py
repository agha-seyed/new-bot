import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import gsheets_client
from studentbot.utils.db_utils import add_score, update_user_level, AsyncSessionLocal
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a feedback form to the user."""
    user_id = update.effective_user.id
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
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("feedback_prompt", lang)),
            reply_markup=reply_markup,
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ Feedback form sent to user {user_id}")
        await award_points_for_action(user_id, "interaction")
    except TelegramError as e:
        logger.error(f"❌ Telegram error sending feedback form to user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


async def feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the feedback callback."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        feedback_choice = query.data
        if feedback_choice not in ["excellent", "average", "poor"]:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("invalid_feedback", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Invalid feedback choice by user {user_id}: {feedback_choice}")
            return

        async with AsyncSessionLocal() as session:
            await add_score(session, user_id, 5 if feedback_choice == "excellent" else 3)
            await update_user_level(session, user_id)
        
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
                "Feedback",
                f"Rating: {feedback_choice}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )

        # Notify admin for poor feedback
        if feedback_choice == "poor":
            admin_chat_id = config.ADMIN_CHAT_ID
            if admin_chat_id:
                await context.bot.send_message(
                    chat_id=admin_chat_id,
                    text=sanitize_markdown(
                        get_translated_text("admin_poor_feedback", lang).format(user_id=user_id)
                    ),
                    parse_mode="MarkdownV2"
                )

        await query.edit_message_text(
            sanitize_markdown(get_translated_text("feedback_thanks", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ Feedback '{feedback_choice}' submitted by user {user_id}")
        await award_points_for_action(user_id, "feedback")
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling feedback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error handling feedback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


def get_feedback_handler():
    """Return the feedback handler."""
    return [
        CommandHandler("feedback", feedback),
        CallbackQueryHandler(feedback_callback, pattern="^(excellent|average|poor)$"),
    ]