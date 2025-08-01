import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    """Configuration class for the StudentBot project."""

    def __init__(self):
        # Telegram
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
        self.BASE_URL = os.getenv("BASE_URL")
        self.PORT = int(os.getenv("PORT", "8080"))
        self.ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

        # DB & Redis
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.REDIS_URL = os.getenv("REDIS_URL")

        # Google APIs
        self.GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")
        self.GOOGLE_DRIVE_CREDS = os.getenv("GOOGLE_DRIVE_CREDS")
        self.GOOGLE_DRIVE_UPLOAD_FOLDER_ID = os.getenv("GOOGLE_DRIVE_UPLOAD_FOLDER_ID")
        self.SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
        self.SHEET_ID = os.getenv("SHEET_ID")
        self.QUESTIONS_SHEET_NAME = os.getenv("QUESTIONS_SHEET_NAME", "StudentBotQuestions")

        # APIs
        self.OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
        self.EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")
        self.HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

        # Email
        self.EMAIL_SENDER = os.getenv("EMAIL_SENDER")
        self.EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

        # Misc
        self.PYTHON_VERSION = os.getenv("PYTHON_VERSION", "3.11.9")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

        # Constants
        self.ISEE_COEFFICIENTS = {
            1: 1, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85,
            6: 3.20, 7: 3.50, 8: 3.80, 9: 4.00, 10: 4.20
        }
        self.PROPERTY_VALUE_FACTOR = 500
        self.PROPERTY_VALUE_MULTIPLIER = 0.2
        self.SCHOLARSHIP_THRESHOLDS = {
            "full": 12650, "medium": 16445, "partial": 23000
        }

        # Logging
        self.BASE_DIR = Path(__file__).resolve().parent
        self.LOG_DIR = Path(os.getenv("LOG_DIR", self.BASE_DIR / "logs"))
        self.LOG_FILE = self.LOG_DIR / "studentbot.log"

    def validate(self):
        """Validate critical environment variables."""
        required_vars = {
            "TELEGRAM_BOT_TOKEN": self.TELEGRAM_BOT_TOKEN,
            "DATABASE_URL": self.DATABASE_URL,
            "REDIS_URL": self.REDIS_URL,
            "GOOGLE_CREDS": self.GOOGLE_CREDS,
            "GOOGLE_DRIVE_CREDS": self.GOOGLE_DRIVE_CREDS,
            "SHEET_ID": self.SHEET_ID,
            "BASE_URL": self.BASE_URL,
            "ADMIN_CHAT_ID": self.ADMIN_CHAT_ID,
            "EMAIL_SENDER": self.EMAIL_SENDER,
            "EMAIL_PASSWORD": self.EMAIL_PASSWORD,
            "HUGGINGFACE_API_KEY": self.HUGGINGFACE_API_KEY,
            "OPENWEATHERMAP_API_KEY": self.OPENWEATHERMAP_API_KEY,
        }
        missing = [k for k, v in required_vars.items() if not v]
        if missing:
            raise ValueError(f"Missing required env variables: {', '.join(missing)}")

        if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            raise ValueError(f"Invalid DATABASE_URL format: {self.DATABASE_URL}. Must start with 'postgresql+asyncpg://'")

    def setup_logging(self):
        """Setup logging configuration."""
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("studentbot")
        logger.setLevel(logging.DEBUG if self.ENVIRONMENT == "development" else logging.INFO)

        # File logging
        file_handler = RotatingFileHandler(self.LOG_FILE, maxBytes=5_000_000, backupCount=5)
        file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(name)s - %(message)s"))
        logger.addHandler(file_handler)

        # Console logging
        if self.ENVIRONMENT == "development":
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s"))
            logger.addHandler(console_handler)

        return logger

# Initialize configuration
config = Config()
config.validate()
logger = config.setup_logging()
logger.info("✅ Configuration loaded successfully")

# Export direct access variables for convenience
DATABASE_URL = config.DATABASE_URL
PORT = config.PORT
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
WEBHOOK_SECRET = config.WEBHOOK_SECRET
BASE_URL = config.BASE_URL
ADMIN_CHAT_ID = config.ADMIN_CHAT_ID
