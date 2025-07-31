import logging
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, text
from studentbot import config
from .models_db import User, ConsultationRequest
from datetime import datetime

logger = logging.getLogger(__name__)

engine = create_async_engine(config.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_users_table():
    """Create users table if not exists."""
    try:
        from .models_db import init_db
        init_db(engine)
        logger.info("✅ Users table initialized")
    except Exception as e:
        logger.error(f"❌ Error creating users table: {str(e)}")
        raise

async def create_consultation_requests_table():
    """Create consultation requests table if not exists."""
    try:
        from .models_db import init_db
        init_db(engine)
        logger.info("✅ Consultation requests table initialized")
    except Exception as e:
        logger.error(f"❌ Error creating consultation requests table: {str(e)}")
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

async def add_points(user_id: int, points: int) -> None:
    """Add points to a user."""
    async with AsyncSessionLocal() as session:
        try:
            async with session.begin():
                await session.execute(
                    update(User).where(User.id == user_id).values(points=User.points + points)
                )
                logger.info(f"✅ Added {points} points to user {user_id}")
        except Exception as e:
            logger.error(f"❌ Error adding points to user {user_id}: {str(e)}")
            raise

async def get_user_points(user_id: int) -> int:
    """Retrieve a user's points."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(User.points).filter_by(id=user_id))
            return result.scalar_one_or_none() or 0
        except Exception as e:
            logger.error(f"❌ Error retrieving points for user {user_id}: {str(e)}")
            return 0

async def get_user_level(user_id: int) -> str:
    """Retrieve a user's level."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(User.level).filter_by(id=user_id))
            return result.scalar_one_or_none() or "🎓 Newbie"
        except Exception as e:
            logger.error(f"❌ Error retrieving level for user {user_id}: {str(e)}")
            return "🎓 Newbie"

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
    async with AsyncSessionLocal() as session:
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

async def get_consultation_requests(user_id: int) -> List[Dict]:
    """Retrieve all consultation requests for a user."""
    async with AsyncSessionLocal() as session:
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

async def update_consultation_request_status(user_id: int, status: str) -> None:
    """Update the status of a consultation request."""
    async with AsyncSessionLocal() as session:
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

async def log_event(user_id: int, event_type: str, details: str) -> None:
    """Log an event to the database."""
    async with AsyncSessionLocal() as session:
        try:
            async with session.begin():
                await session.execute(
                    text("INSERT INTO events (user_id, event_type, details, created_at) VALUES (:user_id, :event_type, :details, :created_at)"),
                    {
                        "user_idწ
                        "user_id": user_id,
                        "event_type": event_type,
                        "details": details,
                        "created_at": datetime.utcnow()
                    }
                )
                logger.info(f"✅ Logged event for user {user_id}: {event_type}")
        except Exception as e:
            logger.error(f"❌ Error logging event for user {user_id}: {str(e)}")
            raise
