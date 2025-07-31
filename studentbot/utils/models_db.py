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
