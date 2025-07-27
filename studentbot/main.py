import logging
import os

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from studentbot.handlers.cmd_start import start
from studentbot.handlers.language_handler import language_handler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    # Get the token from the environment variable
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable not set")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^(🇬🇧 English|🇮🇹 Italiano|🇮🇷 فارسی)$"), language_handler
        )
    )

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
