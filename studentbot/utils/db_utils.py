import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config import config

logger = logging.getLogger(__name__)

# Initialize database engine
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    pool_size=3,  # Reduced for Render's 512MB plan
    max_overflow=5,
    pool_timeout=30,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    """Provide a database session."""
    async with AsyncSessionLocal() as session:
        yield session

async def test_db_connection():
    """Test database connection on startup."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        raise

# Table creation (to be moved to models.py)
async def create_tables():
    """Create database tables with indexes and constraints."""
    async with engine.begin() as conn:
        # Users table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                first_name VARCHAR(255) NOT NULL,
                last_name VARCHAR(255) NOT NULL,
                age INTEGER CHECK (age >= 0),
                email VARCHAR(255) UNIQUE NOT NULL,
                country VARCHAR(255),
                field_of_study VARCHAR(255),
                lang VARCHAR(10) DEFAULT 'fa',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                points INTEGER DEFAULT 0 CHECK (points >= 0),
                score INTEGER DEFAULT 0 CHECK (score >= 0),
                level VARCHAR(255) DEFAULT '🎓 Newbie',
                migration_status INTEGER DEFAULT 0 CHECK (migration_status >= 0)
            );
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """))
        # Consultation requests table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS consultation_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id),
                name VARCHAR(255) NOT NULL,
                field_of_study VARCHAR(255),
                level VARCHAR(255),
                gpa FLOAT,
                destination_country VARCHAR(255),
                language_level VARCHAR(255),
                budget VARCHAR(255),
                work_experience TEXT,
                special_needs TEXT,
                status VARCHAR(255) DEFAULT 'pending' CHECK (status IN ('pending', 'responded', 'archived')),
                file_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_consultations_user_id ON consultation_requests(user_id);
        """))
        # Events table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id),
                event_type VARCHAR(255) NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
            CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
        """))
        # ISEE results table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS isee_results (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id),
                family_members INTEGER NOT NULL CHECK (family_members > 0),
                annual_income FLOAT NOT NULL CHECK (annual_income >= 0),
                property_value FLOAT NOT NULL CHECK (property_value >= 0),
                isee FLOAT NOT NULL,
                status VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_isee_results_user_id ON isee_results(user_id);
        """))
        logger.info("✅ All database tables created or verified.")
