from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from studentbot.utils.text_formatter import get_translated_text
from studentbot.utils.db_utils import get_user_migration_status, update_user_migration_status


async def migration_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's migration status."""
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    status = get_user_migration_status(user_id)
    progress_bar = ""
    for i in range(10):
        if i < status:
            progress_bar += "✅"
        else:
            progress_bar += "❌"
    await update.message.reply_text(
        f"{get_translated_text('migration_status', lang)}:\n{progress_bar}"
    )


async def update_migration_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Updates the user's migration status."""
    user_id = update.message.from_user.id
    new_status = int(context.args[0])
    update_user_migration_status(user_id, new_status)
    await update.message.reply_text(get_translated_text("migration_status_updated", lang))


def get_migration_handler():
    """Returns the migration handler."""
    return [
        CommandHandler("migration_status", migration_status),
        CommandHandler("update_migration_status", update_migration_status),
    ]
