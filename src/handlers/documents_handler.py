# src/handlers/query_handler.py
import json
import requests
import re
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_text, send_whatsapp_pdf, send_whatsapp_buttons
from src.core.s3_handler import get_pdf_url
from src.core.db_handler import get_s3_client, get_bot_state, update_bot_state, set_pending_feedback
from src.core.config import S3_BUCKET_NAME, GROK_API_KEY
from src.core.logger import logger
import time # For delay in sending PDFs
class QueryHandler(BaseHandler):
    priority = 70 # Lower than documents (80) and SOP (90)
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
        filename = re.sub(r'^(jake_zondagh_|sop-[a-z]+-\d+_)', '', filename.lower())
        return filename
    def _load_content(self, company_id: str, filepath: str) -> str:
        client = get_s3_client()
        if not client:
            return ""
        try:
            obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=filepath)
            data = json.loads(obj['Body'].read().decode('utf-8'))
            content = data.get('content')
            if content:
                return content
            else:
                return json.dumps(data)
        except Exception as e:
            logger.error(f"Error loading content {filepath}: {e}")
            return ""
    def _find_relevant_files(self, sender_id: str, company_id: str, query: str, only_sops: bool = False) -> list[str]:
        personal_files = self._get_personal_files(sender_id, company_id) if not only_sops else []
        sop_files = self._get_global_sop_files(company_id)
        all_files = personal_files + sop_files
        if not all_files:
            return []
        titles = [self._get_clean_title(f) + f" (path: {f})" for f in all_files] # Include path for uniqueness
        titles_str = "\n".join(titles)
        prompt = f"Given the user's query: '{query}' and this list of document titles and paths:\n{titles_str}\n\nSelect up to 5 most relevant file paths. Output only the paths, one per line, no explanations."
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "grok-3-mini",
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload)
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content'].strip()
                selected_paths = [line.strip() for line in answer.split('\n') if line.strip() and any(f.endswith(line) for f in all_files)]
                return selected_paths
            else:
                logger.error(f"Grok API error for matching: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Grok API call for matching failed: {e}")
            return []
    def _process_query(self, sender_id: str, company_id: str, query: str, only_sops: bool = False):
        send_whatsapp_text(sender_id, "Neural Nets Engaged. Incoming 🚀")
        matched_files = self._find_relevant_files(sender_id, company_id, query, only_sops)
        if not matched_files:
            answer = "No relevant documents found. Try rephrasing your question."
            send_whatsapp_text(sender_id, answer)
            set_pending_feedback(sender_id, company_id, {'query': query, 'answer': answer})
            self._clear_context(sender_id, company_id)
            self._send_feedback(sender_id, company_id)
            return
        contents = []
        for file in matched_files:
            content = self._load_content(company_id, file)
            if content:
                contents.append(content)
        if not contents:
            answer = "Error loading document content."
            send_whatsapp_text(sender_id, answer)
            set_pending_feedback(sender_id, company_id, {'query': query, 'answer': answer})
            self._clear_context(sender_id, company_id)
            self._send_feedback(sender_id, company_id)
            return
        concat_content = "\n\n".join(contents)
        prompt = f"Based on the following documents (prioritize personal docs if any):\n{concat_content}\n\nFirst, determine if the documents are relevant to the query '{query}'. If yes, start your response with 'RELEVANT:' followed by the explanation. If not, start with 'NOT_RELEVANT:' and suggest rephrasing or contacting the appropriate department. If relevant, explain in simple, easy-to-understand language for normal people, like a friendly conversation. Highlight relevant sections of interest with **bold text**. Translate any legal or complex terms into plain English."
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-3-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful HR assistant answering based on company and personal documents."},
                {"role": "user", "content": prompt}
            ]
        }
        try:
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload)
            if response.status_code == 200:
                full_answer = response.json()['choices'][0]['message']['content']
                logger.info(f"Grok API full answer: {full_answer}")
                if full_answer.startswith('NOT_RELEVANT:'):
                    answer = full_answer[len('NOT_RELEVANT:'):].strip()
                    send_whatsapp_text(sender_id, answer)
                    set_pending_feedback(sender_id, company_id, {'query': query, 'answer': answer})
                else:
                    answer = full_answer[len('RELEVANT:'):].strip() if full_answer.startswith('RELEVANT:') else full_answer
                    send_whatsapp_text(sender_id, answer)
                    set_pending_feedback(sender_id, company_id, {'query': query, 'answer': answer})
                    # Send all relevant PDFs after the summary
                    for file in matched_files:
                        pdf_file = file.replace('.json', '.pdf')
                        url = get_pdf_url(pdf_file)
                        if url:
                            filename = pdf_file.split('/')[-1]
                            send_whatsapp_text(sender_id, f"Sending full document: {self._get_clean_title(pdf_file).capitalize()}")
                            success = send_whatsapp_pdf(sender_id, url, filename, caption="Full Document")
                            time.sleep(2) # Delay for sequencing
                            if not success:
                                send_whatsapp_text(sender_id, "Error sending PDF.")
                        else:
                            send_whatsapp_text(sender_id, "PDF not found for this document.")
                logger.info(f"Grok API answer sent to {sender_id}")
            else:
                answer = "Error getting answer from AI. Try again later."
                send_whatsapp_text(sender_id, answer)
                logger.error(f"Grok API error: {response.text}")
                set_pending_feedback(sender_id, company_id, {'query': query, 'answer': answer})
        except Exception as e:
            answer = "Error processing your query."
            send_whatsapp_text(sender_id, answer)
            logger.error(f"Grok API call failed: {e}")
            set_pending_feedback(sender_id, company_id, {'query': query, 'answer': answer})
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
        return False
    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        state = get_bot_state(sender_id, company_id)
        if state.get('context') == 'feedback_comment':
            return False
        context = state.get('context')
        if context == 'query' or context == 'sop_query':
            only_sops = (context == 'sop_query')
            self._process_query(sender_id, company_id, text, only_sops=only_sops)
            return True
        # For unhandled text, treat as general query (since priority low, higher handlers missed it)
        self._process_query(sender_id, company_id, text)
        return True