import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def create_users_table():
    async with engine.begin() as conn:
        await conn.run_sync(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                age INTEGER,
                email VARCHAR(255),
                country VARCHAR(255),
                field_of_study VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                points INTEGER DEFAULT 0,
                migration_status INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,
                level VARCHAR(255) DEFAULT 'Newbie'
            )
            """
        )


async def create_consultation_requests_table():
    async with engine.begin() as conn:
        await conn.run_sync(
            """
            CREATE TABLE IF NOT EXISTS consultation_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                name VARCHAR(255),
                field_of_study VARCHAR(255),
                level VARCHAR(255),
                gpa VARCHAR(255),
                destination_country VARCHAR(255),
                language_level VARCHAR(255),
                budget VARCHAR(255),
                work_experience TEXT,
                special_needs TEXT,
                status VARCHAR(255) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

async def add_score(user_id, score):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("UPDATE users SET score = score + :score WHERE id = :user_id"),
                {"score": score, "user_id": user_id},
            )

async def get_user_level(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT level FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        level = result.scalar_one_or_none()
        return level if level else "Newbie"

async def update_user_level(user_id):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                text("SELECT score FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            )
            score = result.scalar_one()
            if score < 10:
                level = "🎓 Newbie"
            elif score < 30:
                level = "🧑‍🎓 Active Student"
            elif score < 60:
                level = "👨‍🏫 Mentor"
            else:
                level = "👑 Ambassador"
            await session.execute(
                text("UPDATE users SET level = :level WHERE id = :user_id"),
                {"level": level, "user_id": user_id},
            )

async def get_consultation_requests(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM consultation_requests WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        return result.all()

async def get_all_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT * FROM users"))
        return result.all()

async def get_all_consultation_requests():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT * FROM consultation_requests"))
        return result.all()

async def update_consultation_request_status(request_id, status):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("UPDATE consultation_requests SET status = :status WHERE id = :request_id"),
                {"status": status, "request_id": request_id},
            )

async def create_consultation_request(user_id, name, field_of_study, level, gpa, destination_country, language_level, budget, work_experience, special_needs):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text(
                    """
                    INSERT INTO consultation_requests (user_id, name, field_of_study, level, gpa, destination_country, language_level, budget, work_experience, special_needs)
                    VALUES (:user_id, :name, :field_of_study, :level, :gpa, :destination_country, :language_level, :budget, :work_experience, :special_needs)
                    """
                ),
                {
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
                },
            )

async def add_points(user_id, points):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("UPDATE users SET points = points + :points WHERE id = :user_id"),
                {"points": points, "user_id": user_id},
            )

async def get_user_points(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT points FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        points = result.scalar_one_or_none()
        return points if points else 0

async def get_leaderboard():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT first_name, points FROM users ORDER BY points DESC LIMIT 10")
        )
        return result.all()

async def get_user_migration_status(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT migration_status FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        status = result.scalar_one_or_none()
        return status if status else 0

async def update_user_migration_status(user_id, status):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("UPDATE users SET migration_status = :status WHERE id = :user_id"),
                {"status": status, "user_id": user_id},
            )

async def get_user(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        return result.one_or_none()

async def update_user(user_id, first_name, last_name, age, email, country, field_of_study):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text(
                    """
                    UPDATE users
                    SET first_name = :first_name, last_name = :last_name, age = :age, email = :email, country = :country, field_of_study = :field_of_study
                    WHERE id = :user_id
                    """
                ),
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "age": age,
                    "email": email,
                    "country": country,
                    "field_of_study": field_of_study,
                    "user_id": user_id,
                },
            )

async def delete_user(user_id):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("DELETE FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            )

async def create_user(user_id, first_name, last_name, age, email, country, field_of_study):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text(
                    """
                    INSERT INTO users (id, first_name, last_name, age, email, country, field_of_study)
                    VALUES (:user_id, :first_name, :last_name, :age, :email, :country, :field_of_study)
                    """
                ),
                {
                    "user_id": user_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "age": age,
                    "email": email,
                    "country": country,
                    "field_of_study": field_of_study,
                },
            )
