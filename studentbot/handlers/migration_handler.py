import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from studentbot.utils.text_formatter import get_translated_text
from studentbot.utils.db_utils import get_user_migration_status, update_user_migration_status

logger = logging.getLogger(__name__)

async def migration_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's migration status."""
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    status = get_user_migration_status(user_id)
    progress_bar = "".join(["✅" if i < status else "❌" for i in range(10)])
    await update.message.reply_text(
        f"{get_translated_text('migration_status', lang)}:\n{progress_bar}"
    )
    logger.info(f"User {user_id} checked migration status: {status}/10")

async def update_migration_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Updates the user's migration status."""
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id

    if not context.args:
        await update.message.reply_text(get_translated_text("migration_status_no_arg", lang))
        return

    try:
        new_status = int(context.args[0])
        if not 0 <= new_status <= 10:
            raise ValueError("Out of range")
        update_user_migration_status(user_id, new_status)
        await update.message.reply_text(get_translated_text("migration_status_updated", lang))
        logger.info(f"User {user_id} updated migration status to {new_status}")
    except ValueError:
        await update.message.reply_text(get_translated_text("migration_status_invalid_arg", lang))
        logger.warning(f"User {user_id} entered invalid migration status update: {context.args[0]}")

def get_migration_handler():
    """Returns the migration handler."""
    return [
        CommandHandler("migration_status", migration_status),
        CommandHandler("update_migration_status", update_migration_status),
    ]
