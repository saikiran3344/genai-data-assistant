import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import psycopg2
from auth.models import get_connection
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY   = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this")
ALGORITHM    = "HS256"
TOKEN_EXPIRE = 60 * 24  # 24 hours in minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ─────────────────────────────────────────

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── User DB helpers ─────────────────────────────────────

def get_user_by_email(email: str) -> dict | None:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, email, hashed_password, role,
               tokens_remaining, questions_asked, is_active
        FROM users WHERE email = %s
    """, (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "id":                row[0],
        "email":             row[1],
        "hashed_password":   row[2],
        "role":              row[3],
        "tokens_remaining":  row[4],
        "questions_asked":   row[5],
        "is_active":         row[6]
    }


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, email, role, tokens_remaining,
               questions_asked, is_active, created_at
        FROM users WHERE id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "id":               row[0],
        "email":            row[1],
        "role":             row[2],
        "tokens_remaining": row[3],
        "questions_asked":  row[4],
        "is_active":        row[5],
        "created_at":       str(row[6])
    }


def register_user(email: str, password: str) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        hashed = hash_password(password)
        cur.execute("""
            INSERT INTO users (email, hashed_password)
            VALUES (%s, %s)
            RETURNING id, email, role, tokens_remaining
        """, (email, hashed))
        row = cur.fetchone()
        conn.commit()
        return {
            "id":               row[0],
            "email":            row[1],
            "role":             row[2],
            "tokens_remaining": row[3]
        }
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise ValueError("Email already registered")
    finally:
        cur.close()
        conn.close()


def deduct_token(user_id: int, question: str, tokens_used: int = 1):
    conn = get_connection()
    cur  = conn.cursor()

    # Deduct tokens and increment question count
    cur.execute("""
        UPDATE users
        SET tokens_remaining = tokens_remaining - %s,
            questions_asked  = questions_asked + 1
        WHERE id = %s
    """, (tokens_used, user_id))

    # Log the usage
    cur.execute("""
        INSERT INTO usage_log (user_id, question, tokens_used)
        VALUES (%s, %s, %s)
    """, (user_id, question, tokens_used))

    conn.commit()
    cur.close()
    conn.close()


def has_tokens(user_id: int) -> bool:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT tokens_remaining FROM users WHERE id = %s",
        (user_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row and row[0] > 0


# ── Token request helpers ───────────────────────────────

def submit_token_request(user_id: int,
                          message: str,
                          tokens_requested: int = 100):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO token_requests
            (user_id, message, tokens_requested)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (user_id, message, tokens_requested))
    req_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return req_id


# ── Admin helpers ───────────────────────────────────────

def get_all_users() -> list[dict]:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, email, role, tokens_remaining,
               questions_asked, is_active, created_at
        FROM users
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id":               r[0],
            "email":            r[1],
            "role":             r[2],
            "tokens_remaining": r[3],
            "questions_asked":  r[4],
            "is_active":        r[5],
            "created_at":       str(r[6])
        }
        for r in rows
    ]


def get_pending_requests() -> list[dict]:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT tr.id, u.email, tr.message,
               tr.tokens_requested, tr.requested_at
        FROM token_requests tr
        JOIN users u ON u.id = tr.user_id
        WHERE tr.status = 'pending'
        ORDER BY tr.requested_at ASC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id":               r[0],
            "email":            r[1],
            "message":          r[2],
            "tokens_requested": r[3],
            "requested_at":     str(r[4])
        }
        for r in rows
    ]


def approve_token_request(request_id: int, tokens_to_add: int):
    conn = get_connection()
    cur  = conn.cursor()

    # Get user_id from request
    cur.execute(
        "SELECT user_id FROM token_requests WHERE id = %s",
        (request_id,)
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("Request not found")

    user_id = row[0]

    # Add tokens to user
    cur.execute("""
        UPDATE users
        SET tokens_remaining = tokens_remaining + %s
        WHERE id = %s
    """, (tokens_to_add, user_id))

    # Mark request resolved
    cur.execute("""
        UPDATE token_requests
        SET status = 'approved', resolved_at = NOW()
        WHERE id = %s
    """, (request_id,))

    conn.commit()
    cur.close()
    conn.close()


def reject_token_request(request_id: int):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE token_requests
        SET status = 'rejected', resolved_at = NOW()
        WHERE id = %s
    """, (request_id,))
    conn.commit()
    cur.close()
    conn.close()


def allocate_tokens_directly(user_id: int, tokens: int):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE users
        SET tokens_remaining = tokens_remaining + %s
        WHERE id = %s
    """, (tokens, user_id))
    conn.commit()
    cur.close()
    conn.close()