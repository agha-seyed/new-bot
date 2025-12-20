import os
import sys
from typing import List, Dict, Optional
from pydantic_settings import BaseSettings
from pydantic import ValidationError

class Settings(BaseSettings):
    # Bot Core
    TELEGRAM_BOT_TOKEN: str
    BOT_ID: str = "perugia"
    CITY_NAME: str = "Perugia"
    WEBHOOK_HOST: str
    WEBHOOK_SECRET: str
    ADMIN_IDS: List[int] = []  # Comma separated list from env

    # Security
    X_TELEGRAM_BOT_API_SECRET_TOKEN: str
    ALLOWED_IPS: List[str] = ["149.154.160.0/20", "91.108.4.0/22"]

    # Database & Storage
    DATABASE_URL: str
    REDIS_URL: str

    # External APIs
    OPENAI_API_KEY: Optional[str] = None # Fallback if we switch to API
    GOOGLE_CREDENTIALS_JSON: Optional[str] = None # Base64 encoded json
    OPENWEATHERMAP_API_KEY: Optional[str] = None
    EXCHANGERATE_API_KEY: Optional[str] = None

    # Feature Flags
    FEATURE_AI_ENABLED: bool = True
    FEATURE_VOICE_TRANSCRIPTION: bool = True
    FEATURE_LIVE_CHAT: bool = True

    # RBAC (JSON string or comma separated in env)
    ROLES_OWNER: List[int] = []
    ROLES_ADMIN: List[int] = []
    ROLES_EDITOR: List[int] = []
    ROLES_MODERATOR: List[int] = []

    # App Config
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    WORKERS: int = 1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @property
    def webhook_path(self) -> str:
        return f"/{self.BOT_ID}/{self.WEBHOOK_SECRET}"

    @property
    def webhook_url(self) -> str:
        return f"{self.WEBHOOK_HOST}{self.webhook_path}"

try:
    settings = Settings()
except ValidationError as e:
    print(f"Configuration Error: {e}")
    # In production, we might want to fail hard, but for now lets print
    sys.exit(1)
