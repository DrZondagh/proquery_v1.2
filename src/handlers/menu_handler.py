# src/handlers/menu_handler.py
import re
import difflib
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_text, send_whatsapp_buttons
from src.core.db_handler import update_bot_state, get_bot_state
from src.core.logger import logger

class MenuHandler(BaseHandler):
    priority = 100  # Highest priority - greets and main menu always take precedence

    def _is_greeting(self, text: str) -> bool:
        """Fuzzy match for common greetings and misspellings (case-insensitive)"""
        known_greetings = [
            'hi', 'hello', 'hey', 'hallo', 'greetings',
            'good morning', 'good afternoon', 'good evening',
            'menu', 'start'
        ]
        lowered = text.lower().strip()

        # Exact regex matches first
        exact_patterns = [
            r'\bhi\b', r'\bhello\b', r'\bhey\b', r'\bhallo\b', r'\bgreetings\b',
            r'\bgood morning\b', r'\bgood afternoon\b', r'\bgood evening\b',
            r'\bmenu\b', r'\bstart\b'
        ]
        if any(re.search(pattern, lowered) for pattern in exact_patterns):
            return True

        # Fuzzy match for misspellings using difflib (standard lib, no extra deps)
        # Check if close to any known greeting (ratio > 0.7 for short words)
        words = lowered.split()
        for word in words:
            matches = difflib.get_close_matches(word, known_greetings, n=1, cutoff=0.7)
            if matches:
                return True

        return False

    def _send_main_menu(self, sender_id: str, company_id: str):
        buttons = [
            {"type": "reply", "reply": {"id": "docs_btn", "title": "Documents 📄"}},
            {"type": "reply", "reply": {"id": "apps_btn", "title": "Tools 🛠️"}},
            {"type": "reply", "reply": {"id": "hr_btn", "title": " Talk to HR 🤝"}}
        ]
        text = "Main Menu (づ๑•ᴗ•๑)づ✨"
        success = send_whatsapp_buttons(sender_id, text, buttons)
        if success:
            logger.info(f"Main menu sent to {sender_id}")
        else:
            logger.error(f"Failed to send main menu to {sender_id}")

    def _send_apps_menu(self, sender_id: str, company_id: str):
        buttons = [
            {"type": "reply", "reply": {"id": "leave_btn", "title": "Take Leave 🌴"}},
            {"type": "reply", "reply": {"id": "sop_btn", "title": "Train SOP 🎓"}},
            {"type": "reply", "reply": {"id": "placeholder_btn", "title": "Coming Soon 🚀"}}
        ]
        text = "Tools"
        success = send_whatsapp_buttons(sender_id, text, buttons)
        if success:
            logger.info(f"Apps menu sent to {sender_id}")
        else:
            logger.error(f"Failed to send apps menu to {sender_id}")

    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        if interactive_data.get('type') != 'button_reply':
            return False
        button_id = interactive_data['button_reply']['id']
        if button_id == "main_menu_btn":
            self._send_main_menu(sender_id, company_id)
            return True
        if button_id == "apps_btn":
            self._send_apps_menu(sender_id, company_id)
            return True
        if button_id == "hr_btn":
            send_whatsapp_text(sender_id, "Talk to HR coming soon!")
            return True
        if button_id == "placeholder_btn":
            send_whatsapp_text(sender_id, "More Apps coming soon!")
            return True
        # We don't handle other buttons here yet - other handlers will
        return False

    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        if self._is_greeting(text):
            self._send_main_menu(sender_id, company_id)
            return True
        # Optional: explicit "menu" command (already covered in fuzzy)
        if text.lower().strip() in ["menu", "main menu", "home"]:
            self._send_main_menu(sender_id, company_id)
            return True
        return False