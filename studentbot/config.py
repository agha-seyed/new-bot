import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the StudentBot project."""
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
    BASE_URL = os.getenv("BASE_URL")
    PORT = os.getenv("PORT", "8080")  # Default port as string
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

    # Database and Cache
    DATABASE_URL = os.getenv("DATABASE_URL")
    REDIS_URL = os.getenv("REDIS_URL")

    # Google API Settings
    GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")
    GOOGLE_DRIVE_CREDS = os.getenv("GOOGLE_DRIVE_CREDS")
    GOOGLE_DRIVE_UPLOAD_FOLDER_ID = os.getenv("GOOGLE_DRIVE_UPLOAD_FOLDER_ID")
    SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
    SHEET_ID = os.getenv("SHEET_ID")
    QUESTIONS_SHEET_NAME = os.getenv("QUESTIONS_SHEET_NAME", "StudentBotQuestions")

    # Third-Party API Keys
    OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
    EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Email Settings
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    # ISEE Calculation Constants
    ISEE_COEFFICIENTS = {
        1: 1, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85,
        6: 3.20, 7: 3.50, 8: 3.80, 9: 4.00, 10: 4.20
    }
    PROPERTY_VALUE_FACTOR = 500
    PROPERTY_VALUE_MULTIPLIER = 0.2
    SCHOLARSHIP_THRESHOLDS = {
        "full": 12650, "medium": 16445, "partial": 23000
    }

    # Logging Settings
    BASE_DIR = Path(__file__).resolve().parent
    LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
    LOG_FILE = LOG_DIR / "studentbot.log"

    # Other Settings
    PYTHON_VERSION = os.getenv("PYTHON_VERSION", "3.11.9")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

    @staticmethod
    def validate():
        """Validate critical environment variables."""
        required_vars = {
            "TELEGRAM_BOT_TOKEN": Config.TELEGRAM_BOT_TOKEN,
            "DATABASE_URL": Config.DATABASE_URL,
            "REDIS_URL": Config.REDIS_URL,
            "GOOGLE_CREDS": Config.GOOGLE_CREDS,
            "GOOGLE_DRIVE_CREDS": Config.GOOGLE_DRIVE_CREDS,
            "SHEET_ID": Config.SHEET_ID,
            "BASE_URL": Config.BASE_URL,
            "ADMIN_CHAT_ID": Config.ADMIN_CHAT_ID,
            "EMAIL_SENDER": Config.EMAIL_SENDER,
            "EMAIL_PASSWORD": Config.EMAIL_PASSWORD,
            "HUGGINGFACE_API_KEY": Config.HUGGINGFACE_API_KEY,
            "OPENWEATHERMAP_API_KEY": Config.OPENWEATHERMAP_API_KEY,
        }
        missing_vars = [name for name, value in required_vars.items() if not value]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logging.error(error_msg)
            raise ValueError(error_msg)

        # Validate DATABASE_URL format
        if Config.DATABASE_URL and not Config.DATABASE_URL.startswith("postgresql+asyncpg://"):
            error_msg = f"Invalid DATABASE_URL format: {Config.DATABASE_URL}. Must start with 'postgresql+asyncpg://'"
            logging.error(error_msg)
            raise ValueError(error_msg)

        # Validate numeric variables
        try:
            Config.PORT = int(Config.PORT)
            Config.ADMIN_CHAT_ID = int(Config.ADMIN_CHAT_ID or 0)
            if Config.PORT <= 0:
                logging.warning("PORT is invalid or missing, defaulting to 8080")
                Config.PORT = 8080
            if Config.ADMIN_CHAT_ID <= 0:
                logging.warning("ADMIN_CHAT_ID is invalid or missing, defaulting to 0")
                Config.ADMIN_CHAT_ID = 0
        except (ValueError, TypeError) as e:
            logging.error(f"Invalid format for numeric variables: {str(e)}")
            raise ValueError(f"Invalid format for numeric variables: {str(e)}")

    @staticmethod
    def setup_logging():
        """Setup logging configuration."""
        Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("studentbot")
        logger.setLevel(logging.DEBUG if Config.ENVIRONMENT == "development" else logging.INFO)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            Config.LOG_FILE, maxBytes=5_000_000, backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
        ))
        logger.addHandler(file_handler)

        # Console handler for development
        if Config.ENVIRONMENT == "development":
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                "%(name)s - %(levelname)s - %(message)s"
            ))
            logger.addHandler(console_handler)

        return logger

# Initialize configuration
config = Config()
try:
    config.validate()
except ValueError as e:
    logging.error(f"Configuration validation failed: {str(e)}")
    raise
logger = config.setup_logging()
logger.info("Configuration loaded successfully")
