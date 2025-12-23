# src/handlers/query_handler.py
# Updated to classify query type with AI before processing.
# If 'personal', send latest/relevant doc + menu buttons.
# If 'global', proceed with full search.

from src.core.base_handler import BaseHandler
from src.core.query import process_query, get_s3_client
from src.core.whatsapp_handler import send_whatsapp_text, send_whatsapp_pdf, send_whatsapp_buttons
from src.core.s3_handler import get_pdf_url
from src.core.logger import logger
import re
import requests
import time
from src.core.config import GROK_API_KEY, GROK_MODEL, S3_BUCKET_NAME


class QueryHandler(BaseHandler):
    priority = 70  # Medium priority

    def _classify_query(self, query, sender_id):
        prompt = f"Query: '{query}'\nClassify as 'personal' (e.g., payslips, my documents, benefits guide) or 'global' (e.g., policies, SOPs, general questions). Output ONLY 'personal' or 'global'."
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}
        try:
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                classification = response.json()['choices'][0]['message']['content'].strip().lower()
                if classification in ['personal', 'global']:
                    return classification
        except Exception as e:
            logger.error(f"Classification failed: {e}")
        return 'global'  # Default to global if fails

    def _handle_personal_query(self, sender_id: str, company_id: str, interpreted_query: str):
        # Example: For "payslips", find and send latest payslip
        # Adjust logic based on your doc types
        client = get_s3_client()
        personal_prefix = f"{company_id}/employees/{sender_id}/"
        response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=personal_prefix)
        payslips = sorted([obj['Key'] for obj in response.get('Contents', []) if
                           'Payslip' in obj['Key'] and obj['Key'].endswith('.pdf')], reverse=True)
        if payslips:
            latest_pdf_key = payslips[0]
            pdf_url = get_pdf_url(latest_pdf_key)
            if pdf_url:
                filename = latest_pdf_key.split('/')[-1]
                send_whatsapp_text(sender_id,
                                   f"Here's your latest payslip ({filename.replace('.pdf', '')}). For more, check Documents menu.")
                send_whatsapp_pdf(sender_id, pdf_url, filename, caption="Latest Payslip")
            else:
                send_whatsapp_text(sender_id, "Error fetching latest payslip. Check Documents menu.")
        else:
            send_whatsapp_text(sender_id, "No payslips found. Contact HR or check Documents menu.")
        # Send menu buttons
        self._send_menu_buttons(sender_id, company_id)

    def _send_menu_buttons(self, sender_id: str, company_id: str):
        buttons = [
            {"type": "reply", "reply": {"id": "docs_btn", "title": "Documents 📄"}},
            {"type": "reply", "reply": {"id": "main_menu_btn", "title": "Main Menu ↩️"}}
        ]
        text = "More options:"
        send_whatsapp_buttons(sender_id, text, buttons)

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
        classification = self._classify_query(text, sender_id)
        if classification == 'personal':
            self._handle_personal_query(sender_id, company_id, text)  # Use original query or interpreted
            return True

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