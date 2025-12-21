# src/handlers/menu_handler.py
import re
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_text, send_whatsapp_buttons
from src.core.db_handler import update_bot_state, get_bot_state
from src.core.logger import logger

class MenuHandler(BaseHandler):
    priority = 100  # Highest priority - greets and main menu always take precedence

    def _is_greeting(self, text: str) -> bool:
        """Fuzzy match for common greetings (case-insensitive)"""
        greetings = [
            r'\bhi\b', r'\bhello\b', r'\bhey\b', r'\bhallo\b', r'\bgreetings\b',
            r'\bgood morning\b', r'\bgood afternoon\b', r'\bgood evening\b',
            r'\bmenu\b', r'\bstart\b'
        ]
        lowered = text.lower().strip()
        return any(re.search(pattern, lowered) for pattern in greetings)

    def _send_main_menu(self, sender_id: str, company_id: str):
        buttons = [
            {"type": "reply", "reply": {"id": "docs_btn", "title": "Documents 📄"}},
            {"type": "reply", "reply": {"id": "leave_btn", "title": "Take Leave 🌴"}},
            {"type": "reply", "reply": {"id": "sop_btn", "title": "SOP Training 🎓"}}
        ]
        text = "Welcome to ProQuery HR Bot!\n\nPlease select an option:"
        success = send_whatsapp_buttons(sender_id, text, buttons)
        if success:
            logger.info(f"Main menu sent to {sender_id}")
        else:
            logger.error(f"Failed to send main menu to {sender_id}")

    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        if interactive_data.get('type') != 'button_reply':
            return False

        button_id = interactive_data['button_reply']['id']

        if button_id == "main_menu_btn":
            self._send_main_menu(sender_id, company_id)
            return True

        # We don't handle other buttons here yet - other handlers will
        return False

    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        if self._is_greeting(text):
            self._send_main_menu(sender_id, company_id)
            return True

        # Optional: explicit "menu" command
        if text.lower().strip() in ["menu", "main menu", "home"]:
            self._send_main_menu(sender_id, company_id)
            return True

        return False