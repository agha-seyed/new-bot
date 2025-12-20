from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, EmailStr, Field

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    EDITOR = "editor"
    MODERATOR = "moderator"
    OWNER = "owner"

class UserProfile(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    full_name: str
    language: str = "en"
    role: UserRole = UserRole.USER
    registered_at: datetime = Field(default_factory=datetime.utcnow)

class NewsItem(BaseModel):
    title: str
    content: str
    author_id: int
    media_url: Optional[str] = None
    media_type: Optional[str] = None # photo, video, document
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_published: bool = False

class ISEEData(BaseModel):
    family_income: float
    assets: float
    family_members: int
    # Add other needed fields for calculation
