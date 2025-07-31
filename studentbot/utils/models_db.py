from sqlalchemy import Column, Integer, BigInteger, Float, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    email = Column(String, nullable=True)
    field_of_study = Column(String, nullable=True)
    country = Column(String, nullable=True)
    lang = Column(String, default="en")
    points = Column(Integer, default=0)  # Added for gamification
    level = Column(String, default="🎓 Newbie")  # Added for gamification
    created_at = Column(DateTime, default=datetime.utcnow)

class ISEEResult(Base):
    __tablename__ = "isee_results"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    family_members = Column(Integer, nullable=False)
    annual_income = Column(Float, nullable=False)
    property_value = Column(Float, nullable=False)
    isee = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ConsultationRequest(Base):
    __tablename__ = "consultation_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    field_of_study = Column(String, nullable=False)
    level = Column(String, nullable=False)
    gpa = Column(Float, nullable=False)
    destination_country = Column(String, nullable=False)
    language_level = Column(String, nullable=False)
    budget = Column(String, nullable=False)
    work_experience = Column(String, nullable=True)
    special_needs = Column(String, nullable=True)
    file_id = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class CostCalculation(Base):
    __tablename__ = "cost_calculations"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    rent = Column(Float, nullable=False)
    food = Column(Float, nullable=False)
    transportation = Column(Float, nullable=False)
    compared_city = Column(String, nullable=False)
    user_total = Column(Float, nullable=False)
    city_total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_id = Column(String, nullable=False)
    drive_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=True)  # Added for optional feedback comments
    created_at = Column(DateTime, default=datetime.utcnow)

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    answer = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class MigrationStatus(Base):
    __tablename__ = "migration_status"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    status = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    query = Column(String, nullable=False)
    answer = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    event_type = Column(String, nullable=False)
    details = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db(engine):
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(engine)
