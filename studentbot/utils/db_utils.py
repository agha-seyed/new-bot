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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
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
