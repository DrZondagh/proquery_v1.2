# FILE 2: src\core\db_handler.py
# src/core/db_handler.py
# FILE: src/db_handler.py
# Updated: Added password_hash to get_user_info for auth. Retained all, no break.
# Added validate_sender_id, validate_query, validate_doc_type, validate_filename for security.
import boto3
import json # For safe parsing if needed
from src.core.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME
from src.core.logger import logger
import re
from datetime import datetime, timedelta
def get_s3_client():
    try:
        client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        return client
    except Exception as e:
        logger.error(f"Error creating S3 client: {e}")
        return None
def get_bot_state(sender_id: str, company_id: str) -> dict:
    client = get_s3_client()
    key = f"{company_id}/employees/{sender_id}/bot_state.json"
    try:
        obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        return json.loads(obj['Body'].read().decode('utf-8'))
    except client.exceptions.NoSuchKey:
        return {}
    except Exception as e:
        logger.error(f"Get bot_state failed: {e}")
        return {}
def update_bot_state(sender_id: str, company_id: str, state: dict):
    client = get_s3_client()
    key = f"{company_id}/employees/{sender_id}/bot_state.json"
    try:
        client.put_object(Body=json.dumps(state), Bucket=S3_BUCKET_NAME, Key=key)
    except Exception as e:
        logger.error(f"Update bot_state failed: {e}")
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
    client = get_s3_client()
    if not client:
        logger.error("No S3 client")
        return None, None, None, None
    key = f"meditest/employees/{sender_id}/user.json"
    logger.info(f"Fetching user.json for {sender_id} at key: {key}")
    try:
        obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        data = json.loads(obj['Body'].read().decode('utf-8'))
        logger.info(f"User data for {sender_id}: {data}")
        return data.get('company_id'), data.get('role'), data.get('person_name'), data.get('password_hash')
    except client.exceptions.NoSuchKey:
        logger.error(f"No user.json found for {sender_id} at {key}")
        return None, None, None, None
    except Exception as e:
        logger.error(f"Error fetching/parsing user.json for {sender_id}: {e}")
        return None, None, None, None
def log_user_query(sender_id: str, query: str, answer: str, company_id: str) -> bool: # Added company_id param
    client = get_s3_client()
    if not client:
        return False
    key = f"{company_id}/employees/{sender_id}/queries.json" # Adjusted to match structure
    try:
        # Fetch existing data if exists
        try:
            obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
            data = json.loads(obj['Body'].read().decode('utf-8'))
        except client.exceptions.NoSuchKey:
            data = []
        # Append new query
        data.append({"query": query, "answer": answer})
        # Upload back
        client.put_object(Body=json.dumps(data), Bucket=S3_BUCKET_NAME, Key=key)
        return True
    except Exception as e:
        logger.error(f"Error logging query to S3: {e}")
        return False
def is_message_processed(sender_id: str, message_id: str, company_id: str) -> bool:
    client = get_s3_client()
    if not client:
        return False
    key = f"{company_id}/employees/{sender_id}/processed_messages.json"
    try:
        obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        data = json.loads(obj['Body'].read().decode('utf-8'))
        return message_id in data
    except client.exceptions.NoSuchKey:
        return False
    except Exception as e:
        logger.error(f"Error checking processed message {message_id}: {e}")
        return False
def mark_message_processed(sender_id: str, message_id: str, company_id: str) -> bool:
    client = get_s3_client()
    if not client:
        return False
    key = f"{company_id}/employees/{sender_id}/processed_messages.json"
    try:
        try:
            obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
            data = json.loads(obj['Body'].read().decode('utf-8'))
        except client.exceptions.NoSuchKey:
            data = []
        if message_id not in data:
            data.append(message_id)
            client.put_object(Body=json.dumps(data), Bucket=S3_BUCKET_NAME, Key=key)
        return True
    except Exception as e:
        logger.error(f"Error marking processed message {message_id}: {e}")
        return False
# Validation functions
def validate_sender_id(sender_id: str) -> bool:
    return bool(re.match(r'^\d{10,15}$', sender_id)) # Phone numbers: 10-15 digits
def validate_query(query: str) -> bool:
    return len(query) <= 1000 and bool(re.match(r'^[\w\s\?!\.,-]*$', query)) # Alphanum, spaces, basic punct; no <>
def validate_doc_type(doc_type: str) -> bool:
    allowed = ['sop', 'payslip', 'handbook', 'review', 'benefits', 'warning'] # Expand as needed
    return doc_type.lower() in allowed
def validate_filename(filename: str) -> bool:
    return bool(re.match(r'^[\w\.-]+\.pdf$', filename)) # Alphanum, _, -, .pdf
def get_last_response_time(sender_id: str, company_id: str) -> datetime | None:
    state = get_bot_state(sender_id, company_id)
    ts = state.get('last_response_time')
    return datetime.fromisoformat(ts) if ts else None
def update_last_response_time(sender_id: str, company_id: str):
    state = get_bot_state(sender_id, company_id)
    state['last_response_time'] = datetime.now().isoformat()
    update_bot_state(sender_id, company_id, state)