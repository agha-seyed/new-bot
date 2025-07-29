from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from ..utils.db_utils import get_all_consultation_requests, update_consultation_request_status
from ..utils.text_formatter import get_translated_text


async def admin_consultations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays all consultation requests to the admin."""
    requests = get_all_consultation_requests()
    if not requests:
        await update.message.reply_text("No consultation requests.")
        return

    for req in requests:
        keyboard = [
            [
                f"Reply to {req[2]}",
                f"Archive request {req[0]}",
                f"View file for request {req[0]}",
            ]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        request_text = f"""
*Request ID:* {req[0]}
*User ID:* {req[1]}
*Name:* {req[2]}
*Field of Study:* {req[3]}
*Level:* {req[4]}
*GPA:* {req[5]}
*Destination Country:* {req[6]}
*Language Level:* {req[7]}
*Budget:* {req[8]}
*Work Experience:* {req[9]}
*Special Needs:* {req[10]}
*Status:* {req[11]}
        """
        await update.message.reply_text(
            request_text, parse_mode="Markdown", reply_markup=reply_markup
        )


async def reply_to_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Replies to a consultation request."""
    # TODO: Implement reply logic
    await update.message.reply_text("This feature is not yet implemented.")


async def archive_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Archives a consultation request."""
    request_id = int(update.message.text.split(" ")[2])
    update_consultation_request_status(request_id, "archived")
    await update.message.reply_text(f"Request {request_id} has been archived.")


async def view_consultation_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Views the file for a consultation request."""
    # TODO: Implement file viewing logic
    await update.message.reply_text("This feature is not yet implemented.")


def get_admin_handler():
    """Returns the admin handler."""
    return [
        CommandHandler("admin_consultations", admin_consultations),
        CommandHandler("reply", reply_to_consultation),
        CommandHandler("archive", archive_consultation),
        CommandHandler("view_file", view_consultation_file),
    ]
