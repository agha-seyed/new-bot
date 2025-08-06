from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    BigInteger,
    Enum,
    Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncEngine
from datetime import datetime
import enum

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    age = Column(Integer)
    email = Column(String)
    country = Column(String)
    field_of_study = Column(String)
    points = Column(Integer, default=0)
    level = Column(String, default="🎓 Newbie")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    last_active = Column(DateTime, default=datetime.utcnow)

class ConsultationRequest(Base):
    __tablename__ = "consultation_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    name = Column(String)
    field_of_study = Column(String)
    level = Column(String)
    gpa = Column(Float)
    destination_country = Column(String)
    language_level = Column(String)
    budget = Column(String)
    work_experience = Column(Text)
    special_needs = Column(Text)
    status = Column(String, default="pending")
    file_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User")

class CostCalculation(Base):
    __tablename__ = "cost_calculations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    rent = Column(Float)
    food = Column(Float)
    transportation = Column(Float)
    compared_city = Column(String)
    user_total = Column(Float)
    city_total = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    file_id = Column(String)
    file_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    rating = Column(Integer)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    question = Column(Text)
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

class MigrationStatus(Base):
    __tablename__ = "migration_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), unique=True)
    status = Column(Integer, default=0)
    user = relationship("User")

class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    query = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    event_type = Column(String)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

async def init_db(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
