# src/handlers/query_handler.py
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_text, send_whatsapp_buttons
from src.core.db_handler import get_bot_state, update_bot_state, set_pending_feedback, log_user_query
from src.core.query import process_query
from src.core.logger import logger

class QueryHandler(BaseHandler):
    priority = 40  # Lower priority to act as fallback

    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        return False

    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        state = get_bot_state(sender_id, company_id)
        if state.get('context') in ['feedback_comment', 'hr_query']:
            return False
        # Skip short or nonsense texts to fall back to unhandled
        stripped = text.strip()
        if len(stripped) < 5:
            return False
        # Process as query if reached here (not handled by higher priority)
        summaries, error = process_query(company_id, sender_id, stripped)
        if error:
            send_whatsapp_text(sender_id, error)
            log_user_query(sender_id, stripped, error, company_id)
            return True
        full_answer = ""
        for summary, f in summaries:
            send_whatsapp_text(sender_id, summary)
            full_answer += summary + "\n\n"
        set_pending_feedback(sender_id, company_id, {'query': stripped, 'answer': full_answer})
        self._send_feedback(sender_id)
        log_user_query(sender_id, stripped, full_answer, company_id)
        if state.get('context') == 'sop_query':
            del state['context']
            update_bot_state(sender_id, company_id, state)
        return True

    def _send_feedback(self, sender_id: str):
        buttons = [
            {"type": "reply", "reply": {"id": "feedback_yes", "title": "Yes 👍"}},
            {"type": "reply", "reply": {"id": "feedback_no", "title": "No 👎"}},
            {"type": "reply", "reply": {"id": "main_menu_btn", "title": "Back to Menu ↩️"}}
        ]
        text = "Was this helpful?"
        success = send_whatsapp_buttons(sender_id, text, buttons)
        if success:
            logger.info(f"Feedback buttons sent to {sender_id}")