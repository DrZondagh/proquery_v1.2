# src/webhook_handler.py
import os
import importlib
import inspect
from datetime import datetime, timedelta
from src.core.base_handler import BaseHandler
from src.core.db_handler import (
    validate_sender_id, is_message_processed, mark_message_processed,
    get_last_response_time, update_last_response_time, get_user_info
)
from src.core.whatsapp_handler import send_whatsapp_text
from src.core.logger import logger
from src.core.config import BOT_PHONE_NUMBER

def discover_handlers():
    handlers_dir = os.path.join(os.path.dirname(__file__), 'handlers')
    handlers = []
    if os.path.exists(handlers_dir):
        for filename in os.listdir(handlers_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]
                module = importlib.import_module(f'src.handlers.{module_name}')
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BaseHandler) and obj != BaseHandler:
                        handlers.append(obj())
    handlers.sort(key=lambda h: h.priority, reverse=True)  # Higher priority first
    return handlers

def process_incoming_message(data: dict) -> bool:
    # Extract relevant fields from WhatsApp webhook payload
    try:
        entry = data['entry'][0]
        change = entry['changes'][0]
        value = change['value']
        if 'messages' not in value:
            # Skip status updates (sent/delivered/read) silently
            return True
        message = value['messages'][0]
        sender_id = message['from']
        message_id = message['id']
        msg_type = message['type']
        timestamp = datetime.fromtimestamp(int(message['timestamp']))
    except (KeyError, IndexError):
        logger.error("Invalid webhook payload structure")
        return False
    # Ignore if from bot's number
    if sender_id == BOT_PHONE_NUMBER:
        logger.info(f"Ignoring message from bot: {message_id}")
        return True
    # Validate sender_id
    if not validate_sender_id(sender_id):
        logger.warning(f"Invalid sender_id: {sender_id}")
        return False
    # Get user info
    company_id, role, person_name, password_hash = get_user_info(sender_id)
    if not company_id:
        send_whatsapp_text(sender_id, "Unauthorized access. Please contact HR.")
        return False
    # Check duplicates
    if is_message_processed(sender_id, message_id, company_id):
        logger.info(f"Duplicate message ignored: {message_id}")
        return True
    mark_message_processed(sender_id, message_id, company_id)
    # Rate limit for text messages (5s cooldown to prevent ghosts from rapid retries)
    if msg_type == 'text':
        last_time = get_last_response_time(sender_id, company_id)
        if last_time and (datetime.now() - last_time) < timedelta(seconds=5):
            logger.warning(f"Rate limit hit for {sender_id}")
            return False
        update_last_response_time(sender_id, company_id)
    # Discover and sort handlers
    handlers = discover_handlers()
    # Process based on type
    handled = False
    if msg_type == 'interactive':
        interactive_data = message['interactive']  # button_reply or list_reply
        for handler in handlers:
            if handler.check_context(sender_id, company_id, msg_type, interactive_data):
                if handler.try_process_interactive(sender_id, company_id, interactive_data):
                    handled = True
                    break
    elif msg_type == 'text':
        text = message['text']['body']
        for handler in handlers:
            if handler.check_context(sender_id, company_id, msg_type, text):
                if handler.try_process_text(sender_id, company_id, text):
                    handled = True
                    break
    if not handled:
        send_whatsapp_text(sender_id, "Sorry, I didn't understand that. Try saying 'Hi' for the menu!")
    return handled