# src/handlers/query_handler.py
import difflib
import json
import requests
import re
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_text, send_whatsapp_pdf, send_whatsapp_buttons
from src.core.s3_handler import get_pdf_url
from src.core.db_handler import get_s3_client, get_bot_state, update_bot_state
from src.core.config import S3_BUCKET_NAME, GROK_API_KEY
from src.core.logger import logger
import time  # For delay in sending PDFs

class QueryHandler(BaseHandler):
    priority = 70  # Lower than documents (80) and SOP (90)

    def _get_personal_files(self, sender_id: str, company_id: str) -> list[str]:
        client = get_s3_client()
        if not client:
            return []
        prefix = f"{company_id}/employees/{sender_id}/"
        response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        return [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.json')]

    def _get_global_sop_files(self, company_id: str) -> list[str]:
        client = get_s3_client()
        if not client:
            return []
        prefix = f"{company_id}/sops/all/"
        response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        return [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.json')]

    def _get_clean_title(self, filepath: str) -> str:
        filename = filepath.split('/')[-1].replace('.json', '').replace('_', ' ').replace('-', ' ').strip()
        # Remove common prefixes like 'Jake_Zondagh_', 'SOP-HR-001_'
        filename = re.sub(r'^(jake_zondagh_|sop-[a-z]+-\d+_)', '', filename.lower())
        return filename

    def _load_content(self, company_id: str, filepath: str) -> str:
        client = get_s3_client()
        if not client:
            return ""
        try:
            obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=filepath)
            data = json.loads(obj['Body'].read().decode('utf-8'))
            return data.get('content', '')
        except Exception as e:
            logger.error(f"Error loading content {filepath}: {e}")
            return ""

    def _process_query(self, sender_id: str, company_id: str, query: str, only_sops: bool = False):
        personal_files = self._get_personal_files(sender_id, company_id) if not only_sops else []
        sop_files = self._get_global_sop_files(company_id)
        all_files = personal_files + sop_files
        if not all_files:
            send_whatsapp_text(sender_id, "No documents found.")
            self._clear_context(sender_id, company_id)
            self._send_feedback(sender_id, company_id)
            return

        titles = [self._get_clean_title(f) for f in all_files]
        close_matches = difflib.get_close_matches(query.lower(), titles, n=5, cutoff=0.5)  # Lower cutoff for broader match

        if not close_matches:
            send_whatsapp_text(sender_id, "No relevant documents found. Try rephrasing your question.")
            self._clear_context(sender_id, company_id)
            self._send_feedback(sender_id, company_id)
            return

        contents = []
        matched_files = []
        for match in close_matches:
            idx = titles.index(match)
            file = all_files[idx]
            content = self._load_content(company_id, file)
            if content:
                contents.append(content)
                matched_files.append(file)

        if not contents:
            send_whatsapp_text(sender_id, "Error loading document content.")
            self._clear_context(sender_id, company_id)
            self._send_feedback(sender_id, company_id)
            return

        concat_content = "\n\n".join(contents)
        prompt = f"Based on the following documents (prioritize personal docs if any):\n{concat_content}\n\nAnswer the user's query: {query}. Explain in simple, easy-to-understand language for normal people, like a friendly conversation. Highlight relevant sections of interest with **bold text**. Translate any legal or complex terms into plain English."

        # Send waiting message
        send_whatsapp_text(sender_id, "Neural Nets Engaged. Incoming 🚀")

        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-beta",  # Suggested better model for improved reasoning and handling
            "messages": [
                {"role": "system", "content": "You are a helpful HR assistant answering based on company and personal documents."},
                {"role": "user", "content": prompt}
            ]
        }
        try:
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload)
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content']
                send_whatsapp_text(sender_id, answer)
                logger.info(f"Grok API answer sent to {sender_id}")
            else:
                send_whatsapp_text(sender_id, "Error getting answer from AI. Try again later.")
                logger.error(f"Grok API error: {response.text}")
        except Exception as e:
            send_whatsapp_text(sender_id, "Error processing your query.")
            logger.error(f"Grok API call failed: {e}")

        # Send all relevant PDFs after the summary
        for file in matched_files:
            pdf_file = file.replace('.json', '.pdf')
            url = get_pdf_url(pdf_file)
            if url:
                filename = pdf_file.split('/')[-1]
                send_whatsapp_text(sender_id, f"Sending full document: {self._get_clean_title(pdf_file).capitalize()}")
                success = send_whatsapp_pdf(sender_id, url, filename, caption="Full Document")
                time.sleep(2)  # Delay for sequencing
                if not success:
                    send_whatsapp_text(sender_id, "Error sending PDF.")
            else:
                send_whatsapp_text(sender_id, "PDF not found for this document.")

        self._clear_context(sender_id, company_id)
        self._send_feedback(sender_id, company_id)

    def _send_feedback(self, sender_id: str, company_id: str):
        buttons = [
            {"type": "reply", "reply": {"id": "feedback_yes", "title": "Yes 👍"}},
            {"type": "reply", "reply": {"id": "feedback_no", "title": "No 👎"}},
            {"type": "reply", "reply": {"id": "main_menu_btn", "title": "Back to Menu ↩️"}}
        ]
        text = "Was this helpful?"
        success = send_whatsapp_buttons(sender_id, text, buttons)
        if success:
            logger.info(f"Feedback buttons sent to {sender_id}")
        else:
            logger.error(f"Failed to send feedback buttons to {sender_id}")

    def _clear_context(self, sender_id: str, company_id: str):
        state = get_bot_state(sender_id, company_id)
        if 'context' in state:
            del state['context']
            update_bot_state(sender_id, company_id, state)

    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        int_type = interactive_data.get('type')
        if int_type == 'button_reply':
            button_id = interactive_data['button_reply']['id']
            # Handle sop_btn from apps menu
            if button_id == 'sop_btn':
                send_whatsapp_text(sender_id, "What would you like to know about company SOPs or your documents? Ask a question like 'What is the recruitment policy?' or 'My payslip details'.")
                state = get_bot_state(sender_id, company_id)
                state['context'] = 'query'
                update_bot_state(sender_id, company_id, state)
                return True
            # Handle feedback
            if button_id == 'feedback_yes':
                send_whatsapp_text(sender_id, "Thanks for the feedback!")
                return True
            if button_id == 'feedback_no':
                send_whatsapp_text(sender_id, "Sorry to hear that. Please provide more details or type 'skip'.")
                return True
        return False

    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        state = get_bot_state(sender_id, company_id)
        context = state.get('context')
        if context == 'query' or context == 'sop_query':
            only_sops = (context == 'sop_query')
            self._process_query(sender_id, company_id, text, only_sops=only_sops)
            return True
        # For unhandled text, treat as general query (since priority low, higher handlers missed it)
        self._process_query(sender_id, company_id, text)
        return True