# tools/test_query.py
# Standalone test script - run locally to simulate query handling
# Usage: python tools/test_query.py --query "patient marketing" --sender_id "27828530605" --company_id "meditest"
# Requires .env loaded, prints output instead of sending WhatsApp
import argparse
import sys
import os
from dotenv import load_dotenv
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.handlers.query_handler import QueryHandler
from src.core.logger import logger

load_dotenv()

def mock_send_whatsapp_text(recipient: str, text: str):
    print(f"[MOCK TEXT to {recipient}]: {text}")

def mock_send_whatsapp_buttons(recipient: str, text: str, buttons: list):
    print(f"[MOCK BUTTONS to {recipient}]: {text} with buttons {buttons}")

def mock_send_pdf(sender_id: str, company_id: str, json_filepath: str, caption: str = "") -> bool:
    print(f"[MOCK PDF SEND to {sender_id}]: {json_filepath} with caption '{caption}'")
    return True

def mock_set_pending_feedback(sender_id: str, company_id: str, data: dict):
    print(f"[MOCK FEEDBACK SET]: {data}")

def mock_clear_context(sender_id: str, company_id: str):
    print("[MOCK CLEAR CONTEXT]")

# Monkey patch for testing
import src.core.whatsapp_handler
src.core.whatsapp_handler.send_whatsapp_text = mock_send_whatsapp_text
src.core.whatsapp_handler.send_whatsapp_buttons = mock_send_whatsapp_buttons
import src.core.pdf_sender
src.core.pdf_sender.send_pdf = mock_send_pdf
from src.core.db_handler import set_pending_feedback, update_bot_state
set_pending_feedback = mock_set_pending_feedback
from src.handlers.query_handler import QueryHandler
QueryHandler._clear_context = mock_clear_context

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Query Handler Standalone")
    parser.add_argument("--query", required=True, help="Query string")
    parser.add_argument("--sender_id", default="27828530605", help="Sender phone")
    parser.add_argument("--company_id", default="meditest", help="Company ID")
    parser.add_argument("--only_sops", action="store_true", help="Only search SOPs")
    args = parser.parse_args()

    qh = QueryHandler()
    logger.info(f"Testing query: {args.query}")
    qh._process_query(args.sender_id, args.company_id, args.query, args.only_sops)