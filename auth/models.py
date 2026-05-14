import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "genai_assistant"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "")
    )


def setup_auth_tables():
    """
    Creates users, usage_log, and token_requests tables.
    Safe to call multiple times.
    """
    conn = get_connection()
    cur  = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              SERIAL PRIMARY KEY,
            email           TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role            TEXT DEFAULT 'user',
            tokens_remaining INTEGER DEFAULT 100,
            questions_asked  INTEGER DEFAULT 0,
            is_active        BOOLEAN DEFAULT TRUE,
            created_at       TIMESTAMP DEFAULT NOW()
        );
    """)

    # Usage log — every question asked
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_log (
            id           SERIAL PRIMARY KEY,
            user_id      INTEGER REFERENCES users(id),
            question     TEXT,
            tokens_used  INTEGER DEFAULT 1,
            asked_at     TIMESTAMP DEFAULT NOW()
        );
    """)

    # Token requests — user asks admin for more tokens
    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_requests (
            id           SERIAL PRIMARY KEY,
            user_id      INTEGER REFERENCES users(id),
            message      TEXT,
            tokens_requested INTEGER DEFAULT 100,
            status       TEXT DEFAULT 'pending',
            requested_at TIMESTAMP DEFAULT NOW(),
            resolved_at  TIMESTAMP
        );
    """)

    # Create default admin account
    cur.execute("""
        INSERT INTO users (email, hashed_password, role, tokens_remaining)
        VALUES ('admin@genai.com', 'ADMIN_PLACEHOLDER', 'admin', 999999)
        ON CONFLICT (email) DO NOTHING;
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Auth tables created successfully.")


if __name__ == "__main__":
    setup_auth_tables()