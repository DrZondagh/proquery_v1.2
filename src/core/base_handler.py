# src/core/base_handler.py
from abc import ABC, abstractmethod

class BaseHandler(ABC):
    priority: int = 0  # Default priority, higher numbers processed first

    @abstractmethod
    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        """Process interactive messages (buttons, lists). Return True if handled."""
        pass

    @abstractmethod
    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        """Process text messages. Return True if handled."""
        pass

    def check_context(self, sender_id: str, company_id: str, msg_type: str, data: any) -> bool:
        """Stub: Override in subclasses to validate if action is user-prompted and contextually valid.
        Prevents ghost messaging by ensuring no unprompted sends."""
        # Default: Always true; subclasses should implement strict checks, e.g., via bot_state
        return True