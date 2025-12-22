# src/handlers/hr_contact_handler.py
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_text, send_whatsapp_buttons
from src.core.db_handler import get_bot_state, update_bot_state, log_user_query
from src.core.email_handler import send_hr_email
from src.core.logger import logger
class HrContactHandler(BaseHandler):
    priority = 75  # Higher than query (70) to process context-specific text first
    def _send_urgency_menu(self, sender_id: str, company_id: str):
        buttons = [
            {"type": "reply", "reply": {"id": "urgency_high", "title": "🔥 High Priority"}},
            {"type": "reply", "reply": {"id": "urgency_standard", "title": "❓ Standard Query"}}
        ]
        text = "How urgent is your HR issue?"
        success = send_whatsapp_buttons(sender_id, text, buttons)
        if success:
            logger.info(f"Urgency menu sent to {sender_id}")
        state = get_bot_state(sender_id, company_id)
        state['context'] = 'hr_urgency'
        update_bot_state(sender_id, company_id, state)
    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        if interactive_data.get('type') != 'button_reply':
            return False
        button_id = interactive_data['button_reply']['id']
        if button_id == "hr_btn":
            self._send_urgency_menu(sender_id, company_id)
            return True
        elif button_id.startswith("urgency_"):
            urgency_map = {
                "urgency_high": "High Priority",
                "urgency_standard": "Standard"
            }
            urgency = urgency_map.get(button_id, "Standard")
            send_whatsapp_text(sender_id, f"Selected: {urgency}. Now, what's your query or issue? Reply with details or type 'skip' to cancel.")
            state = get_bot_state(sender_id, company_id)
            state['context'] = 'hr_query'
            state['urgency'] = urgency
            update_bot_state(sender_id, company_id, state)
            return True
        return False
    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        state = get_bot_state(sender_id, company_id)
        if state.get('context') == 'hr_query':
            if text.lower().strip() == 'skip':
                send_whatsapp_text(sender_id, "HR contact cancelled. Type 'menu' for main options.")
            else:
                urgency = state.get('urgency', "Standard")
                success = send_hr_email(sender_id, text, urgency)
                if success:
                    send_whatsapp_text(sender_id, "Your query has been sent to HR! They'll contact you soon.")
                    log_user_query(sender_id, text, "Sent to HR (Urgency: " + urgency + ")", company_id)
                else:
                    send_whatsapp_text(sender_id, "Error sending your query. Please try again or contact HR directly.")
            if 'context' in state:
                del state['context']
            if 'urgency' in state:
                del state['urgency']
            update_bot_state(sender_id, company_id, state)
            return True
        return False