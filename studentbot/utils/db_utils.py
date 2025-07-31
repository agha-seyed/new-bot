import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from studentbot import config

logger = logging.getLogger(__name__)

# Initialize database engine
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    pool_size=3,  # Optimized for Render's 512MB plan
    max_overflow=5,
    pool_timeout=30,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database session error: {str(e)}")
            raise

async def test_db_connection():
    """Test database connection on startup."""
    async with engine.connect() as conn:
        try:
            await conn.execute("SELECT 1")
            logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            raise

async def create_users_table():
    """Create users table with indexes and constraints."""
    async with engine.begin() as conn:
        await conn.execute("""
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
        """)
        logger.info("✅ Users table created or verified")

async def create_consultation_requests_table():
    """Create consultation_requests table with indexes and constraints."""
    async with engine.begin() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS consultation_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                field_of_study VARCHAR(255),
                level VARCHAR(255),
                gpa FLOAT,
                destination_country VARCHAR(255),
                language_level VARCHAR(255),
                budget VARCHAR(255),
                work_experience TEXT,
                special_needs TEXT,
                status VARCHAR(255) DEFAULT 'pending' CHECK (
                    status IN ('pending', 'responded', 'archived')
                ),
                file_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_consultations_user_id ON consultation_requests(user_id);
        """)
        logger.info("✅ Consultation_requests table created or verified")

async def create_events_table():
    """Create events table with indexes."""
    async with engine.begin() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                event_type VARCHAR(255) NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
            CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
        """)
        logger.info("✅ Events table created or verified")

async def create_isee_results_table():
    """Create isee_results table with indexes."""
    async with engine.begin() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS isee_results (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                family_members INTEGER NOT NULL CHECK (family_members > 0),
                annual_income FLOAT NOT NULL CHECK (annual_income >= 0),
                property_value FLOAT NOT NULL CHECK (property_value >= 0),
                isee FLOAT NOT NULL,
                status VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_isee_results_user_id ON isee_results(user_id);
        """)
        logger.info("✅ ISEE_results table created or verified")

async def create_tables():
    """Create all database tables."""
    await create_users_table()
    await create_consultation_requests_table()
    await create_events_table()
    await create_isee_results_table()
    logger.info("✅ All database tables created or verified")
