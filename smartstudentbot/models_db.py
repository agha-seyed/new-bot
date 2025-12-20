from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Enum, BigInteger
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    EDITOR = "editor"
    MODERATOR = "moderator"
    OWNER = "owner"

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True) # Telegram ID
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=False)
    language = Column(String, default="en")
    role = Column(Enum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    media_file_id = Column(String, nullable=True) # Telegram File ID
    media_type = Column(String, nullable=True)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
