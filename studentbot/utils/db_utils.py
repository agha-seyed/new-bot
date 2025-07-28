import os
import psycopg2
from psycopg2 import sql

def get_db_connection():
    """Establishes a connection to the database."""
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

def create_users_table():
    """Creates the users table if it doesn't already exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
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
    conn.commit()
    cur.close()
    conn.close()

def add_score(user_id, score):
    """Adds score to a user's profile."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET score = score + %s WHERE id = %s", (score, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_user_level(user_id):
    """Retrieves a user's level from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT level FROM users WHERE id = %s", (user_id,))
    level = cur.fetchone()
    cur.close()
    conn.close()
    return level[0] if level else "Newbie"

def update_user_level(user_id):
    """Updates a user's level based on their score."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT score FROM users WHERE id = %s", (user_id,))
    score = cur.fetchone()[0]
    if score < 10:
        level = "🎓 Newbie"
    elif score < 30:
        level = "🧑‍🎓 Active Student"
    elif score < 60:
        level = "👨‍🏫 Mentor"
    else:
        level = "👑 Ambassador"
    cur.execute("UPDATE users SET level = %s WHERE id = %s", (level, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_consultation_requests(user_id):
    """Retrieves a user's consultation requests from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM consultation_requests WHERE user_id = %s", (user_id,))
    requests = cur.fetchall()
    cur.close()
    conn.close()
    return requests

def get_all_users():
    """Retrieves all users from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users

def get_all_consultation_requests():
    """Retrieves all consultation requests from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM consultation_requests")
    requests = cur.fetchall()
    cur.close()
    conn.close()
    return requests

def update_consultation_request_status(request_id, status):
    """Updates the status of a consultation request."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE consultation_requests SET status = %s WHERE id = %s", (status, request_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def create_consultation_request(user_id, name, field_of_study, level, gpa, destination_country, language_level, budget, work_experience, special_needs):
    """Creates a new consultation request in the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO consultation_requests (user_id, name, field_of_study, level, gpa, destination_country, language_level, budget, work_experience, special_needs)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (user_id, name, field_of_study, level, gpa, destination_country, language_level, budget, work_experience, special_needs),
    )
    conn.commit()
    cur.close()
    conn.close()

def create_consultation_requests_table():
    """Creates the consultation_requests table if it doesn't already exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
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
    conn.commit()
    cur.close()
    conn.close()

def add_points(user_id, points):
    """Adds points to a user's profile."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET points = points + %s WHERE id = %s", (points, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_user_points(user_id):
    """Retrieves a user's points from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT points FROM users WHERE id = %s", (user_id,))
    points = cur.fetchone()
    cur.close()
    conn.close()
    return points[0] if points else 0

def get_leaderboard():
    """Retrieves the leaderboard from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT first_name, points FROM users ORDER BY points DESC LIMIT 10")
    leaderboard = cur.fetchall()
    cur.close()
    conn.close()
    return leaderboard

def get_user_migration_status(user_id):
    """Retrieves a user's migration status from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT migration_status FROM users WHERE id = %s", (user_id,))
    status = cur.fetchone()
    cur.close()
    conn.close()
    return status[0] if status else 0

def update_user_migration_status(user_id, status):
    """Updates a user's migration status in the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET migration_status = %s WHERE id = %s", (status, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_user(user_id):
    """Retrieves a user's profile from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def update_user(user_id, first_name, last_name, age, email, country, field_of_study):
    """Updates a user's profile in the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users
        SET first_name = %s, last_name = %s, age = %s, email = %s, country = %s, field_of_study = %s
        WHERE id = %s
        """,
        (first_name, last_name, age, email, country, field_of_study, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()

def delete_user(user_id):
    """Deletes a user's profile from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

def create_user(user_id, first_name, last_name, age, email, country, field_of_study):
    """Creates a new user in the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (id, first_name, last_name, age, email, country, field_of_study)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (user_id, first_name, last_name, age, email, country, field_of_study),
    )
    conn.commit()
    cur.close()
    conn.close()
