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