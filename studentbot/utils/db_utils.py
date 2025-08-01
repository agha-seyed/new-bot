import logging
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, text, func
from studentbot import config
from .models_db import (
    User, ConsultationRequest, CostCalculation, Document, Feedback,
    Question, MigrationStatus, SearchHistory, Event, init_db
)
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize database engine
try:
    engine = create_async_engine(config.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
except Exception as e:
    logger.error(f"❌ Failed to initialize database engine: {str(e)}")
    raise ValueError(f"Failed to initialize database engine: {str(e)}")

async def test_db_connection():
    """Test the database connection."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False

async def create_users_table():
    """Create users table if not exists."""
    try:
        await init_db(engine)
        logger.info("✅ Users table initialized")
    except Exception as e:
        logger.error(f"❌ Error creating users table: {str(e)}")
        raise

async def create_consultation_requests_table():
    """Create consultation requests table if not exists."""
    try:
        await init_db(engine)
        logger.info("✅ Consultation requests table initialized")
    except Exception as e:
        logger.error(f"❌ Error creating consultation requests table: {str(e)}")
        raise

async def create_user(
    session: AsyncSession,
    user_id: int,
    first_name: str,
    last_name: str,
    age: int,
    email: str,
    country: str,
    field_of_study: str
) -> None:
    """Create a new user."""
    try:
        async with session.begin():
            user = User(
                id=user_id,
                first_name=first_name,
                last_name=last_name,
                age=age,
                email=email,
                country=country,
                field_of_study=field_of_study
            )
            session.add(user)
            await session.commit()
            logger.info(f"✅ Created user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error creating user {user_id}: {str(e)}")
        raise

async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Retrieve a user by ID."""
    try:
        result = await session.execute(select(User).filter_by(id=user_id))
        user = result.scalars().first()
        return user
    except Exception as e:
        logger.error(f"❌ Error retrieving user {user_id}: {str(e)}")
        return None

async def delete_user(session: AsyncSession, user_id: int) -> None:
    """Delete a user by ID."""
    try:
        async with session.begin():
            await session.execute(update(User).where(User.id == user_id).values(deleted_at=datetime.utcnow()))
            logger.info(f"✅ Deleted user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error deleting user {user_id}: {str(e)}")
        raise

async def add_points(session: AsyncSession, user_id: int, points: int) -> None:
    """Add points to a user."""
    try:
        async with session.begin():
            await session.execute(
                update(User).where(User.id == user_id).values(points=User.points + points)
            )
            logger.info(f"✅ Added {points} points to user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error adding points to user {user_id}: {str(e)}")
        raise

async def get_user_points(session: AsyncSession, user_id: int) -> int:
    """Retrieve a user's points."""
    try:
        result = await session.execute(select(User.points).filter_by(id=user_id))
        return result.scalar_one_or_none() or 0
    except Exception as e:
        logger.error(f"❌ Error retrieving points for user {user_id}: {str(e)}")
        return 0

async def get_user_level(session: AsyncSession, user_id: int) -> str:
    """Retrieve a user's level."""
    try:
        result = await session.execute(select(User.level).filter_by(id=user_id))
        return result.scalar_one_or_none() or "🎓 Newbie"
    except Exception as e:
        logger.error(f"❌ Error retrieving level for user {user_id}: {str(e)}")
        return "🎓 Newbie"

async def update_user_level(session: AsyncSession, user_id: int) -> None:
    """Update a user's level based on points."""
    try:
        points = await get_user_points(session, user_id)
        level = "🎓 Newbie"
        if points >= 100:
            level = "🥉 Bronze"
        elif points >= 50:
            level = "🧱 Beginner"
        async with session.begin():
            await session.execute(
                update(User).where(User.id == user_id).values(level=level)
            )
            logger.info(f"✅ Updated level for user {user_id} to {level}")
    except Exception as e:
        logger.error(f"❌ Error updating level for user {user_id}: {str(e)}")
        raise

async def get_leaderboard() -> List[Dict]:
    """Retrieve the top 10 users by points."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(User.id, User.first_name, User.last_name, User.points, User.level)
                .order_by(User.points.desc())
                .limit(10)
            )
            return [
                {
                    "id": row.id,
                    "first_name": row.first_name,
                    "last_name": row.last_name or "",
                    "points": row.points,
                    "level": row.level
                }
                for row in result.scalars().all()
            ]
        except Exception as e:
            logger.error(f"❌ Error retrieving leaderboard: {str(e)}")
            return []

async def create_consultation_request(
    session: AsyncSession,
    user_id: int,
    name: str,
    field_of_study: str,
    level: str,
    gpa: float,
    destination_country: str,
    language_level: str,
    budget: str,
    work_experience: str,
    special_needs: str,
    status: str,
    file_id: str
) -> None:
    """Create a consultation request."""
    try:
        async with session.begin():
            request = ConsultationRequest(
                user_id=user_id,
                name=name,
                field_of_study=field_of_study,
                level=level,
                gpa=gpa,
                destination_country=destination_country,
                language_level=language_level,
                budget=budget,
                work_experience=work_experience,
                special_needs=special_needs,
                status=status,
                file_id=file_id
            )
            session.add(request)
            logger.info(f"✅ Created consultation request for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error creating consultation request for user {user_id}: {str(e)}")
        raise

async def get_consultation_requests(session: AsyncSession, user_id: int) -> List[Dict]:
    """Retrieve all consultation requests for a user."""
    try:
        result = await session.execute(
            select(ConsultationRequest).filter_by(user_id=user_id)
        )
        return [
            {
                "id": row.id,
                "user_id": row.user_id,
                "field_of_study": row.field_of_study,
                "destination_country": row.destination_country,
                "status": row.status,
                "file_id": row.file_id,
                "created_at": row.created_at
            }
            for row in result.scalars().all()
        ]
    except Exception as e:
        logger.error(f"❌ Error retrieving consultation requests for user {user_id}: {str(e)}")
        return []

async def update_consultation_request_status(session: AsyncSession, user_id: int, status: str) -> None:
    """Update the status of a consultation request."""
    try:
        async with session.begin():
            await session.execute(
                update(ConsultationRequest)
                .where(ConsultationRequest.user_id == user_id)
                .values(status=status)
            )
            logger.info(f"✅ Updated consultation request status to {status} for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error updating consultation request status for user {user_id}: {str(e)}")
        raise

async def get_user_migration_status(session: AsyncSession, user_id: int) -> int:
    """Get the user's migration status from the database."""
    try:
        result = await session.execute(select(MigrationStatus).where(MigrationStatus.user_id == user_id))
        migration = result.scalars().first()
        return migration.status if migration else 0
    except Exception as e:
        logger.error(f"❌ Error retrieving migration status for user {user_id}: {str(e)}")
        return 0

async def update_user_migration_status(session: AsyncSession, user_id: int, status: int) -> None:
    """Update the user's migration status in the database."""
    try:
        async with session.begin():
            result = await session.execute(select(MigrationStatus).where(MigrationStatus.user_id == user_id))
            migration = result.scalars().first()
            if migration:
                await session.execute(
                    update(MigrationStatus).where(MigrationStatus.user_id == user_id).values(status=status)
                )
            else:
                session.add(MigrationStatus(user_id=user_id, status=status))
            logger.info(f"✅ Updated migration status for user {user_id} to {status}")
    except Exception as e:
        logger.error(f"❌ Error updating migration status for user {user_id}: {str(e)}")
        raise

async def get_user_activity_stats(session: AsyncSession, user_id: int) -> Dict:
    """Retrieve activity statistics for a user."""
    try:
        questions_asked = (await session.execute(
            select(func.count(Question.id)).where(Question.user_id == user_id)
        )).scalar_one_or_none() or 0
        answers_received = (await session.execute(
            select(func.count(Question.id)).where(Question.user_id == user_id, Question.answer != None)
        )).scalar_one_or_none() or 0
        return {
            "questions_asked": questions_asked,
            "answers_received": answers_received
        }
    except Exception as e:
        logger.error(f"❌ Error retrieving activity stats for user {user_id}: {str(e)}")
        return {"questions_asked": 0, "answers_received": 0}

async def log_event(session: AsyncSession, user_id: int, event_type: str, details: str) -> None:
    """Log an event to the database."""
    try:
        async with session.begin():
            event = Event(
                user_id=user_id,
                event_type=event_type,
                details=details
            )
            session.add(event)
            logger.info(f"✅ Logged event for user {user_id}: {event_type}")
    except Exception as e:
        logger.error(f"❌ Error logging event for user {user_id}: {str(e)}")
        raise
