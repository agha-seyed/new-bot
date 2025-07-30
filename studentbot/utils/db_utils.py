import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config import config
import re

logger = logging.getLogger(__name__)

# Initialize database engine
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    pool_size=5,          # Limit connections for Render's 512MB
    max_overflow=10,
    pool_timeout=30,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    """Provide a database session."""
    async with AsyncSessionLocal() as session:
        yield session

# ------------------------ Schema Creation ------------------------

async def create_users_table():
    """Create the users table with indexes and constraints."""
    async with engine.begin() as conn:
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
        logger.info("✅ Users table created or verified.")

async def create_consultation_requests_table():
    """Create the consultation_requests table with indexes and constraints."""
    async with engine.begin() as conn:
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
        logger.info("✅ Consultation requests table created or verified.")

async def create_events_table():
    """Create the events table for logging user activities."""
    async with engine.begin() as conn:
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
        logger.info("✅ Events table created or verified.")

async def create_isee_results_table():
    """Create the isee_results table for storing ISEE calculations."""
    async with engine.begin() as conn:
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
        logger.info("✅ ISEE results table created or verified.")

# ------------------------ Validation Helpers ------------------------

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def validate_positive_integer(value: Any, field_name: str) -> None:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a positive integer.")

# ------------------------ Users ------------------------

async def create_user(
    user_id: int, first_name: str, last_name: str, age: int, email: str,
    country: str, field_of_study: str, lang: str = "fa"
) -> None:
    """Create a new user in the database."""
    validate_positive_integer(user_id, "user_id")
    validate_positive_integer(age, "age")
    if not validate_email(email):
        raise ValueError("Invalid email format.")
    if not first_name or not last_name:
        raise ValueError("First name and last name cannot be empty.")
    
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(text("""
                    INSERT INTO users (id, first_name, last_name, age, email, country, field_of_study, lang)
                    VALUES (:id, :first_name, :last_name, :age, :email, :country, :field_of_study, :lang)
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": user_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "age": age,
                    "email": email,
                    "country": country,
                    "field_of_study": field_of_study,
                    "lang": lang,
                })
                logger.info(f"✅ Created user with ID: {user_id}")
    except Exception as e:
        logger.error(f"❌ Error creating user {user_id}: {str(e)}")
        raise

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user details by user_id."""
    validate_positive_integer(user_id, "user_id")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            )
            user = result.mappings().one_or_none()
            return dict(user) if user else None
    except Exception as e:
        logger.error(f"❌ Error getting user {user_id}: {str(e)}")
        return None

async def get_all_users() -> List[Dict[str, Any]]:
    """Get all users from the database."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT * FROM users"))
            return [dict(row) for row in result.mappings().all()]
    except Exception as e:
        logger.error(f"❌ Error getting all users: {str(e)}")
        return []

async def update_user(
    user_id: int, first_name: str, last_name: str, age: int, email: str,
    country: str, field_of_study: str
) -> None:
    """Update user details."""
    validate_positive_integer(user_id, "user_id")
    validate_positive_integer(age, "age")
    if not validate_email(email):
        raise ValueError("Invalid email format.")
    if not first_name or not last_name:
        raise ValueError("First name and last name cannot be empty.")
    
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(text("""
                    UPDATE users
                    SET first_name = :first_name, last_name = :last_name, age = :age,
                        email = :email, country = :country, field_of_study = :field_of_study
                    WHERE id = :user_id
                """), {
                    "user_id": user_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "age": age,
                    "email": email,
                    "country": country,
                    "field_of_study": field_of_study
                })
                logger.info(f"✅ Updated user with ID: {user_id}")
    except Exception as e:
        logger.error(f"❌ Error updating user {user_id}: {str(e)}")
        raise

async def delete_user(user_id: int) -> None:
    """Delete a user by user_id."""
    validate_positive_integer(user_id, "user_id")
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("DELETE FROM users WHERE id = :user_id"),
                    {"user_id": user_id},
                )
                logger.info(f"✅ Deleted user with ID: {user_id}")
    except Exception as e:
        logger.error(f"❌ Error deleting user {user_id}: {str(e)}")
        raise

# ------------------------ Points & Score ------------------------

async def add_points(user_id: int, points: int) -> None:
    """Add points to a user's account."""
    validate_positive_integer(user_id, "user_id")
    validate_positive_integer(points, "points")
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("UPDATE users SET points = points + :points WHERE id = :user_id"),
                    {"points": points, "user_id": user_id},
                )
                logger.info(f"✅ Added {points} points to user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error adding points for user {user_id}: {str(e)}")
        raise

async def get_user_points(user_id: int) -> int:
    """Get a user's points."""
    validate_positive_integer(user_id, "user_id")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT points FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            )
            points = result.scalar_one_or_none()
            return points if points is not None else 0
    except Exception as e:
        logger.error(f"❌ Error getting points for user {user_id}: {str(e)}")
        return 0

async def add_score(user_id: int, score: int) -> None:
    """Add score to a user's account and update their level."""
    validate_positive_integer(user_id, "user_id")
    validate_positive_integer(score, "score")
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("UPDATE users SET score = score + :score WHERE id = :user_id"),
                    {"score": score, "user_id": user_id},
                )
                logger.info(f"✅ Added {score} score to user {user_id}")
            await update_user_level(user_id)
    except Exception as e:
        logger.error(f"❌ Error adding score for user {user_id}: {str(e)}")
        raise

async def update_user_level(user_id: int) -> None:
    """Update a user's level based on their score."""
    validate_positive_integer(user_id, "user_id")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT score FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            )
            score = result.scalar_one_or_none() or 0

            if score < 10:
                level = "🎓 Newbie"
            elif score < 30:
                level = "🧑‍🎓 Active Student"
            elif score < 60:
                level = "👨‍🏫 Mentor"
            else:
                level = "👑 Ambassador"

            async with session.begin():
                await session.execute(
                    text("UPDATE users SET level = :level WHERE id = :user_id"),
                    {"level": level, "user_id": user_id},
                )
                logger.info(f"✅ Updated level for user {user_id} to {level}")
    except Exception as e:
        logger.error(f"❌ Error updating level for user {user_id}: {str(e)}")
        raise

async def get_user_level(user_id: int) -> str:
    """Get a user's level."""
    validate_positive_integer(user_id, "user_id")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT level FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            )
            return result.scalar_one_or_none() or "🎓 Newbie"
    except Exception as e:
        logger.error(f"❌ Error getting level for user {user_id}: {str(e)}")
        return "🎓 Newbie"

async def get_leaderboard() -> List[Dict[str, Any]]:
    """Get the top 10 users by points."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT first_name, last_name, points, level FROM users ORDER BY points DESC LIMIT 10")
            )
            return [dict(row) for row in result.mappings().all()]
    except Exception as e:
        logger.error(f"❌ Error getting leaderboard: {str(e)}")
        return []

# ------------------------ Migration Status ------------------------

async def get_user_migration_status(user_id: int) -> int:
    """Get a user's migration status."""
    validate_positive_integer(user_id, "user_id")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT migration_status FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            )
            return result.scalar_one_or_none() or 0
    except Exception as e:
        logger.error(f"❌ Error getting migration status for user {user_id}: {str(e)}")
        return 0

async def update_user_migration_status(user_id: int, status: int) -> None:
    """Update a user's migration status."""
    validate_positive_integer(user_id, "user_id")
    validate_positive_integer(status, "status")
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("UPDATE users SET migration_status = :status WHERE id = :user_id"),
                    {"status": status, "user_id": user_id},
                )
                logger.info(f"✅ Updated migration status for user {user_id} to {status}")
    except Exception as e:
        logger.error(f"❌ Error updating migration status for user {user_id}: {str(e)}")
        raise

# ------------------------ Consultation ------------------------

async def create_consultation_request(
    user_id: int, name: str, field_of_study: str, level: str,
    gpa: float, destination_country: str, language_level: str,
    budget: str, work_experience: str, special_needs: str,
    status: str = "pending", file_id: Optional[str] = None
) -> None:
    """Create a new consultation request."""
    validate_positive_integer(user_id, "user_id")
    if not name:
        raise ValueError("Name cannot be empty.")
    if gpa is not None and (gpa < 0 or gpa > 20):
        raise ValueError("GPA must be between 0 and 20.")
    if status not in ["pending", "responded", "archived"]:
        raise ValueError("Invalid status value.")
    
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(text("""
                    INSERT INTO consultation_requests
                    (user_id, name, field_of_study, level, gpa, destination_country,
                     language_level, budget, work_experience, special_needs, status, file_id)
                    VALUES
                    (:user_id, :name, :field_of_study, :level, :gpa, :destination_country,
                     :language_level, :budget, :work_experience, :special_needs, :status, :file_id)
                """), {
                    "user_id": user_id,
                    "name": name,
                    "field_of_study": field_of_study,
                    "level": level,
                    "gpa": gpa,
                    "destination_country": destination_country,
                    "language_level": language_level,
                    "budget": budget,
                    "work_experience": work_experience,
                    "special_needs": special_needs,
                    "status": status,
                    "file_id": file_id,
                })
                logger.info(f"✅ Created consultation request for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error creating consultation request for user {user_id}: {str(e)}")
        raise

async def get_consultation_requests(user_id: int) -> List[Dict[str, Any]]:
    """Get all consultation requests for a user."""
    validate_positive_integer(user_id, "user_id")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM consultation_requests WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            return [dict(row) for row in result.mappings().all()]
    except Exception as e:
        logger.error(f"❌ Error getting consultation requests for user {user_id}: {str(e)}")
        return []

async def get_all_consultation_requests() -> List[Dict[str, Any]]:
    """Get all consultation requests."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT * FROM consultation_requests"))
            return [dict(row) for row in result.mappings().all()]
    except Exception as e:
        logger.error(f"❌ Error getting all consultation requests: {str(e)}")
        return []

async def update_consultation_request_status(request_id: int, status: str) -> None:
    """Update the status of a consultation request."""
    validate_positive_integer(request_id, "request_id")
    if status not in ["pending", "responded", "archived"]:
        raise ValueError("Invalid status value.")
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("UPDATE consultation_requests SET status = :status WHERE id = :request_id"),
                    {"status": status, "request_id": request_id},
                )
                logger.info(f"✅ Updated consultation request {request_id} to status {status}")
    except Exception as e:
        logger.error(f"❌ Error updating consultation request {request_id}: {str(e)}")
        raise

# ------------------------ Events ------------------------

async def log_event(user_id: int, event_type: str, details: Optional[str] = None) -> None:
    """Log a user event in the events table."""
    validate_positive_integer(user_id, "user_id")
    if not event_type:
        raise ValueError("Event type cannot be empty.")
    
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(text("""
                    INSERT INTO events (user_id, event_type, details)
                    VALUES (:user_id, :event_type, :details)
                """), {
                    "user_id": user_id,
                    "event_type": event_type,
                    "details": details,
                })
                logger.info(f"✅ Logged event '{event_type}' for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error logging event for user {user_id}: {str(e)}")
        raise

# ------------------------ ISEE Results ------------------------

async def store_isee_result(
    user_id: int, family_members: int, annual_income: float, 
    property_value: float, isee: float, status: str
) -> None:
    """Store ISEE calculation result in the database."""
    validate_positive_integer(user_id, "user_id")
    validate_positive_integer(family_members, "family_members")
    if annual_income < 0:
        raise ValueError("Annual income cannot be negative.")
    if property_value < 0:
        raise ValueError("Property value cannot be negative.")
    
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(text("""
                    INSERT INTO isee_results (user_id, family_members, annual_income, property_value, isee, status)
                    VALUES (:user_id, :family_members, :annual_income, :property_value, :isee, :status)
                """), {
                    "user_id": user_id,
                    "family_members": family_members,
                    "annual_income": annual_income,
                    "property_value": property_value,
                    "isee": isee,
                    "status": status,
                })
                logger.info(f"✅ Stored ISEE result for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error storing ISEE result for user {user_id}: {str(e)}")
        raise
        
