import os
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from studentbot.utils.text_formatter import get_translated_text
from studentbot.utils.gsheets import add_user_to_sheet
from studentbot.utils.db_utils import add_score, update_user_level

# States
TITLE, DESCRIPTION, TOPIC = range(3)


async def start_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the question conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("question_title_prompt", lang))
    return TITLE


async def title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the title and asks for the description."""
    context.user_data["question_title"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("question_description_prompt", lang))
    return DESCRIPTION


async def description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the description and asks for the topic."""
    context.user_data["question_description"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("question_topic_prompt", lang))
    return TOPIC


async def topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the topic and ends the conversation."""
    context.user_data["question_topic"] = update.message.text
    lang = context.user_data.get("lang", "en")

    # Save data to Google Sheets
    user_data = context.user_data
    user_id = update.message.from_user.id
    add_user_to_sheet(
        "questions",
        [
            user_id,
            user_data["question_title"],
            user_data["question_description"],
            user_data["question_topic"],
        ],
    )

    # Notify admin
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id:
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=f"New question from {update.message.from_user.first_name}:\n\n*Title:* {user_data['question_title']}\n*Description:* {user_data['question_description']}\n*Topic:* {user_data['question_topic']}",
            parse_mode="Markdown",
        )

    # Add score
    add_score(user_id, 5)
    update_user_level(user_id)

    await update.message.reply_text(get_translated_text("question_complete", lang))
    return ConversationHandler.END


async def cancel_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("question_cancelled", lang))
    return ConversationHandler.END


def get_question_handler():
    """Returns the question conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("question", start_question)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, topic)],
        },
        fallbacks=[CommandHandler("cancel", cancel_question)],
    )
