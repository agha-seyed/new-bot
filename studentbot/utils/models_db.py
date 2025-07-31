from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100), nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    lang = Column(String(10), default="en")
    points = Column(Integer, default=0)
    level = Column(String(50), default="🎓 Newbie")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, name={self.first_name} {self.last_name}, email={self.email})>"

class ConsultationRequest(Base):
    __tablename__ = "consultation_requests"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    name = Column(String(100))
    field_of_study = Column(String(100))
    level = Column(String(50))
    gpa = Column(Float)
    destination_country = Column(String(100))
    language_level = Column(String(10))
    budget = Column(String(50))
    work_experience = Column(Text, nullable=True)
    special_needs = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    file_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ConsultationRequest(id={self.id}, user_id={self.user_id}, status={self.status})>"

def init_db(engine):
    """Initialize database tables."""
    Base.metadata.create_all(engine)
