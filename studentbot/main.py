import logging
import os

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from studentbot.handlers.cmd_start import start
from studentbot.handlers.language_handler import language_handler
from studentbot.handlers.profile_handler import profile
from studentbot.handlers.menu_handler import menu
from studentbot.handlers.registration_flow import get_registration_handler
from studentbot.handlers.edit_profile_flow import get_edit_profile_handler
from studentbot.handlers.isee_handler import get_isee_handler
from studentbot.handlers.gamification_handler import points, leaderboard
from studentbot.handlers.news_handler import news
from studentbot.handlers.registration_flow import get_registration_handler
from studentbot.utils.db_utils import create_users_table

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    # Create the users table if it doesn't already exist
    create_users_table()

    # Get the token from the environment variable
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable not set")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(get_registration_handler())
    application.add_handler(get_edit_profile_handler())
    application.add_handler(get_isee_handler())
    application.add_handler(CommandHandler("points", points))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("news", news))
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^(🇬🇧 English|🇮🇹 Italiano|🇮🇷 فارسی)$"), language_handler
        )
    )

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
