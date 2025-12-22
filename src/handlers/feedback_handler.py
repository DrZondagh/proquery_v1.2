# src/handlers/feedback_handler.py
from src.core.base_handler import BaseHandler
from src.core.db_handler import get_pending_feedback, set_pending_feedback, clear_pending_feedback, get_bot_state, update_bot_state
from src.core.whatsapp_handler import send_whatsapp_text
from src.core.email_handler import send_feedback_email
from src.core.logger import logger
from src.handlers.menu_handler import MenuHandler  # Import to call _send_main_menu
class FeedbackHandler(BaseHandler):
    priority = 50 # Low priority, as fallback for feedback buttons
    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        if interactive_data.get('type') != 'button_reply':
            return False
        button_id = interactive_data['button_reply']['id']
        if button_id in ['feedback_yes', 'feedback_no']:
            pending = get_pending_feedback(sender_id, company_id)
            if not pending:
                return False
            if button_id == 'feedback_yes':
                pending['helpful'] = True
                set_pending_feedback(sender_id, company_id, pending)
                send_whatsapp_text(sender_id, "Great to hear! Any suggestions for improvement or why it was helpful? Reply or type 'skip'.")
                state = get_bot_state(sender_id, company_id)
                state['context'] = 'feedback_comment'
                update_bot_state(sender_id, company_id, state)
                return True
            elif button_id == 'feedback_no':
                pending['helpful'] = False
                set_pending_feedback(sender_id, company_id, pending)
                send_whatsapp_text(sender_id, "Sorry to hear that. Please provide more details or type 'skip'.")
                state = get_bot_state(sender_id, company_id)
                state['context'] = 'feedback_comment'
                update_bot_state(sender_id, company_id, state)
                return True
        return False
    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        state = get_bot_state(sender_id, company_id)
        if state.get('context') == 'feedback_comment':
            pending = get_pending_feedback(sender_id, company_id)
            if not pending:
                return False
            comment = text.strip()
            if comment.lower() != 'skip':
                pending['comment'] = text
                set_pending_feedback(sender_id, company_id, pending)
            send_feedback_email(sender_id, pending['helpful'], pending['query'], pending['answer'], pending.get('comment'))
            send_whatsapp_text(sender_id, "Feedback noted. Thanks!")
            clear_pending_feedback(sender_id, company_id)
            if 'context' in state:
                del state['context']
            update_bot_state(sender_id, company_id, state)
            MenuHandler()._send_main_menu(sender_id, company_id)  # Auto-send main menu after feedback
            return True
        return False