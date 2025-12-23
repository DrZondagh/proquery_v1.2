# src/handlers/query_handler.py
# Updated to combine summaries into one message, remove "Sending PDF..." texts,
# send PDFs silently at the end in priority order, then send feedback buttons.

from src.core.base_handler import BaseHandler
from src.core.query import process_query
from src.core.whatsapp_handler import send_whatsapp_text, send_whatsapp_pdf, send_whatsapp_buttons
from src.core.s3_handler import get_pdf_url
from src.core.logger import logger
import re
import time


class QueryHandler(BaseHandler):
    priority = 70  # Medium priority

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

    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        # Check if this is a general query (not handled by other specific handlers)
        # For example, if text doesn't match greetings, docs, etc.
        summaries, error = process_query(company_id, sender_id, text)
        if error:
            send_whatsapp_text(sender_id, error)
            self._send_feedback(sender_id)
            return True

        # Combine all summaries into one message
        combined_summary = "\n\n".join(summary for summary, _ in summaries)
        send_whatsapp_text(sender_id, combined_summary)

        # Collect and send PDFs in priority order (same as summaries)
        for _, f in summaries:  # summaries is list of (summary, f)
            # Main PDF
            pdf_key = f.replace('.json', '.pdf')
            pdf_url = get_pdf_url(pdf_key)
            if pdf_url:
                filename = pdf_key.split('/')[-1]
                send_whatsapp_pdf(sender_id, pdf_url, filename, caption="Relevant PDF")
                time.sleep(1)  # Slight delay to ensure order

            # Parse summary for mentioned SOPs/docs and send those
            mentioned_docs = re.findall(r'SOP-[A-Z0-9-]+', combined_summary)  # Parse from combined to catch all
            for doc in set(mentioned_docs):
                pdf_key = f"{company_id}/sops/all/{doc}.pdf"  # Adjust naming as needed
                pdf_url = get_pdf_url(pdf_key)
                if pdf_url:
                    filename = pdf_key.split('/')[-1]
                    send_whatsapp_pdf(sender_id, pdf_url, filename, caption=f"Mentioned: {doc}")
                    time.sleep(1)

        # Send feedback buttons after all PDFs
        self._send_feedback(sender_id)
        return True

    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        # If any interactive for queries, handle here
        return False