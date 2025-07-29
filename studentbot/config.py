import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Configuration class for the StudentBot project."""

    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
    BASE_URL = os.getenv("BASE_URL")
    PORT = int(os.getenv("PORT", 8080))
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

    # ISEE Calculation Constants
    ISEE_COEFFICIENTS = {
        1: 1, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85,
        6: 3.20, 7: 3.50, 8: 3.80, 9: 4.00, 10: 4.20
    }
    PROPERTY_VALUE_FACTOR = 500
    PROPERTY_VALUE_MULTIPLIER = 0.2
    SCHOLARSHIP_THRESHOLDS = {
        "full": 12650,
        "medium": 16445,
        "partial": 23000,
    }

    # Logging Settings
    LOG_DIR = "logs"
    LOG_FILE = os.path.join(LOG_DIR, "studentbot.log")

    # Other Settings
    PYTHON_VERSION = os.getenv("PYTHON_VERSION", "3.11.9")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")  # development or production

    @staticmethod
    def validate():
        """Validate critical environment variables."""
        required_vars = [
            ("TELEGRAM_BOT_TOKEN", Config.TELEGRAM_BOT_TOKEN),
            ("DATABASE_URL", Config.DATABASE_URL),
            ("REDIS_URL", Config.REDIS_URL),
            ("GOOGLE_CREDS", Config.GOOGLE_CREDS),
            ("SHEET_ID", Config.SHEET_ID),
            ("BASE_URL", Config.BASE_URL),
            ("ADMIN_CHAT_ID", Config.ADMIN_CHAT_ID)
        ]
        missing_vars = [name for name, value in required_vars if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Validate numeric variables
        try:
            Config.PORT = int(Config.PORT)
            if Config.PORT <= 0:
                raise ValueError("PORT must be a positive integer")
            Config.ADMIN_CHAT_ID = int(Config.ADMIN_CHAT_ID)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid format for numeric variables: {str(e)}")

    @staticmethod
    def setup_logging():
        """Setup logging configuration."""
        os.makedirs(Config.LOG_DIR, exist_ok=True)
        logger = logging.getLogger("studentbot")
        logger.setLevel(logging.DEBUG if Config.ENVIRONMENT == "development" else logging.INFO)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            Config.LOG_FILE, maxBytes=2_000_000, backupCount=5  # Increased backup count
        )
        file_formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(name)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler for development
        if Config.ENVIRONMENT == "development":
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

        return logger

# Initialize configuration and validate
config = Config()
config.validate()
logger = config.setup_logging()

# Log configuration loaded
logger.info("Configuration loaded successfully")