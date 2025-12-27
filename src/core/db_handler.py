# src/core/db_handler.py
import psycopg2
from psycopg2.extras import Json
from src.core.config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from src.core.logger import logger
import re
from datetime import datetime, timedelta

def get_pg_conn():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"Error creating PG connection: {e}")
        return None

def get_user_id(sender_id: str) -> int | None:
    conn = get_pg_conn()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE phone_number = %s", (sender_id,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Error getting user_id for {sender_id}: {e}")
        return None
    finally:
        conn.close()

def get_bot_state(sender_id: str, company_id: str) -> dict:
    user_id = get_user_id(sender_id)
    if not user_id:
        return {}
    conn = get_pg_conn()
    if not conn:
        return {}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM sessions WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                return row[0] or {}
            else:
                cur.execute(
                    "INSERT INTO sessions (user_id, state, data) VALUES (%s, %s, %s)",
                    (user_id, 'active', Json({}))
                )
                conn.commit()
                return {}
    except Exception as e:
        logger.error(f"Get bot_state failed for {sender_id}: {e}")
        return {}
    finally:
        conn.close()

def update_bot_state(sender_id: str, company_id: str, state: dict):
    user_id = get_user_id(sender_id)
    if not user_id:
        return
    conn = get_pg_conn()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET data = %s, last_updated = CURRENT_TIMESTAMP WHERE user_id = %s",
                (Json(state), user_id)
            )
            if cur.rowcount == 0:
                cur.execute(
                    "INSERT INTO sessions (user_id, state, data, last_updated) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
                    (user_id, 'active', Json(state))
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Update bot_state failed for {sender_id}: {e}")
    finally:
        conn.close()

def get_pending_feedback(sender_id: str, company_id: str) -> dict | None:
    state = get_bot_state(sender_id, company_id)
    return state.get('pending_feedback')

def set_pending_feedback(sender_id: str, company_id: str, feedback_data: dict):
    state = get_bot_state(sender_id, company_id)
    state['pending_feedback'] = feedback_data
    update_bot_state(sender_id, company_id, state)

def clear_pending_feedback(sender_id: str, company_id: str):
    state = get_bot_state(sender_id, company_id)
    if 'pending_feedback' in state:
        del state['pending_feedback']
        update_bot_state(sender_id, company_id, state)

def get_user_info(sender_id: str):
    conn = get_pg_conn()
    if not conn:
        logger.error("No PG connection")
        return None, None, None, None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT company_id, role_id, full_name, NULL FROM users WHERE phone_number = %s",
                (sender_id,)
            )
            row = cur.fetchone()
            if row:
                return row
            else:
                return None, None, None, None
    except Exception as e:
        logger.error(f"Error fetching user info for {sender_id}: {e}")
        return None, None, None, None
    finally:
        conn.close()

def log_user_query(sender_id: str, query: str, answer: str, company_id: str) -> bool:
    user_id = get_user_id(sender_id)
    if not user_id:
        return False
    conn = get_pg_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO queries (user_id, query_text, answer_text, timestamp) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
                (user_id, query, answer)
            )
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging query: {e}")
        return False
    finally:
        conn.close()

def is_message_processed(sender_id: str, message_id: str, company_id: str) -> bool:
    user_id = get_user_id(sender_id)
    if not user_id:
        return False
    conn = get_pg_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM audit_logs WHERE user_id = %s AND action = 'processed_message' AND details->>'message_id' = %s",
                (user_id, message_id)
            )
            return bool(cur.fetchone())
    except Exception as e:
        logger.error(f"Error checking processed message {message_id}: {e}")
        return False
    finally:
        conn.close()

def mark_message_processed(sender_id: str, message_id: str, company_id: str) -> bool:
    user_id = get_user_id(sender_id)
    if not user_id:
        return False
    conn = get_pg_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit_logs (user_id, action, details, timestamp) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
                (user_id, 'processed_message', Json({'message_id': message_id}))
            )
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error marking processed message {message_id}: {e}")
        return False
    finally:
        conn.close()

# Validation functions
def validate_sender_id(sender_id: str) -> bool:
    return bool(re.match(r'^\d{10,15}$', sender_id))  # Phone numbers: 10-15 digits

def validate_query(query: str) -> bool:
    return len(query) <= 1000 and bool(re.match(r'^[\w\s\?!\.,-]*$', query))  # Alphanum, spaces, basic punct; no <>

def validate_doc_type(doc_type: str) -> bool:
    allowed = ['sop', 'payslip', 'handbook', 'review', 'benefits', 'warning']  # Expand as needed
    return doc_type.lower() in allowed

def validate_filename(filename: str) -> bool:
    return bool(re.match(r'^[\w\.-]+\.pdf$', filename))  # Alphanum, _, -, .pdf

def get_last_response_time(sender_id: str, company_id: str) -> datetime | None:
    state = get_bot_state(sender_id, company_id)
    ts = state.get('last_response_time')
    return datetime.fromisoformat(ts) if ts else None

def update_last_response_time(sender_id: str, company_id: str):
    state = get_bot_state(sender_id, company_id)
    state['last_response_time'] = datetime.now().isoformat()
    update_bot_state(sender_id, company_id, state)