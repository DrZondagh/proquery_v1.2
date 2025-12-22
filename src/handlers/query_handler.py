# src/handlers/query_handler.py
import json
import requests
import re
import difflib
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_text, send_whatsapp_pdf, send_whatsapp_buttons
from src.core.s3_handler import get_pdf_url
from src.core.db_handler import get_s3_client, get_bot_state, update_bot_state, set_pending_feedback, get_user_info
from src.core.config import S3_BUCKET_NAME, GROK_API_KEY, GROK_MODEL
from src.core.logger import logger
class QueryHandler(BaseHandler):
    priority = 70
    _cache = {}  # company_id -> {'personal': {sender_id: list}, 'sop': list}
    def _get_personal_files(self, sender_id: str, company_id: str) -> list[str]:
        if company_id not in self._cache:
            self._cache[company_id] = {'personal': {}, 'sop': []}
        if sender_id not in self._cache[company_id]['personal']:
            client = get_s3_client()
            if not client:
                return []
            prefix = f"{company_id}/employees/{sender_id}/"
            response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
            files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.json') and 'processed_messages.json' not in obj['Key'] and 'queries.json' not in obj['Key']]
            self._cache[company_id]['personal'][sender_id] = files
        return self._cache[company_id]['personal'][sender_id]
    def _get_global_sop_files(self, company_id: str) -> list[str]:
        if company_id not in self._cache:
            self._cache[company_id] = {'personal': {}, 'sop': []}
        if not self._cache[company_id]['sop']:
            client = get_s3_client()
            if not client:
                return []
            prefix = f"{company_id}/sops/all/"
            response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
            files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.json')]
            self._cache[company_id]['sop'] = files
        return self._cache[company_id]['sop']
    def _get_clean_title(self, filepath: str) -> str:
        filename = filepath.split('/')[-1].replace('.json', '').replace('_', ' ').replace('-', ' ').strip()
        filename = re.sub(r'^(jake_zondagh_|sop-[a-z]+-\d+_)', '', filename.lower())
        return filename
    def _load_content_snippet(self, company_id: str, filepath: str) -> str:
        client = get_s3_client()
        if not client:
            return ""
        try:
            obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=filepath)
            data = json.loads(obj['Body'].read().decode('utf-8'))
            if not isinstance(data, dict):
                return ""
            return data.get('content', '')[:1000]
        except Exception as e:
            logger.error(f"Error loading snippet {filepath}: {e}")
            return ""
    def _load_content(self, company_id: str, filepath: str) -> str:
        client = get_s3_client()
        if not client:
            return ""
        try:
            obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=filepath)
            data = json.loads(obj['Body'].read().decode('utf-8'))
            return data.get('content', json.dumps(data))
        except Exception as e:
            logger.error(f"Error loading content {filepath}: {e}")
            return ""
    def _local_pre_filter(self, all_files, query: str, company_id: str) -> list[str]:
        query_words = set(re.findall(r'\w+', query.lower()))
        scores = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {executor.submit(self._load_content_snippet, company_id, f): f for f in all_files}
            for future in as_completed(future_to_file):
                f = future_to_file[future]
                try:
                    snippet = future.result()
                    title = self._get_clean_title(f)
                    title_words = set(re.findall(r'\w+', title.lower()))
                    common = query_words.intersection(title_words)
                    score = len(common)
                    if score == 0:
                        fuzzy_score = difflib.SequenceMatcher(None, query.lower(), title.lower() + snippet.lower()).ratio()
                        if fuzzy_score > 0.6:
                            score = 1
                    if 'employees' in f:
                        score += 5
                    if score > 0:
                        scores.append((score, f))
                except Exception:
                    pass
        scores.sort(reverse=True)
        return [f for score, f in scores[:20]]
    def _find_relevant_files(self, sender_id: str, company_id: str, query: str, only_sops: bool = False) -> list[str]:
        personal_files = self._get_personal_files(sender_id, company_id) if not only_sops else []
        sop_files = self._get_global_sop_files(company_id)
        all_files = personal_files + sop_files
        if not all_files:
            return []
        pre_filtered = self._local_pre_filter(all_files, query, company_id)
        if not pre_filtered:
            return []
        doc_entries = []
        for f in pre_filtered:
            title = self._get_clean_title(f)
            snippet = self._load_content_snippet(company_id, f)
            doc_entries.append(f"{title} (path: {f})\nSnippet: {snippet}")
        docs_str = "\n\n".join(doc_entries)
        prompt = f"Given the user's query: '{query}' and this list of documents with titles, paths, and content snippets:\n{docs_str}\n\nSelect up to 10 most relevant file paths based on content relevance, synonyms (e.g., 'leave' as vacation/time off/benefits), and misspellings. Prioritize personal docs if matching. Include ALL files with ANY relevance, even indirect or partial. Output only the paths, one per line, no explanations."
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": GROK_MODEL,
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
        send_whatsapp_text(sender_id, "ProQuery: AI driven efficiency. Incoming 🚀")
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
                contents.append(f"Document: {self._get_clean_title(file)}\n{content}")
        if not contents:
            answer = "Error loading document content."
            send_whatsapp_text(sender_id, answer)
            set_pending_feedback(sender_id, company_id, {'query': query, 'answer': answer})
            self._clear_context(sender_id, company_id)
            self._send_feedback(sender_id, company_id)
            return
        concat_content = "\n\n".join(contents)
        prompt = f"Based on the following documents (prioritize personal docs if any):\n{concat_content}\n\nAnswer the user's query: {query}. List documents 1 to N from most to least relevant, with relevance rating (High/Medium/Low). Give concise AI-generated summary of each (2-3 sentences max), highlighting key sections with **bold** for important parts. Include where to find info in each document. Translate complex terms to plain English. Keep friendly/direct, no intro fluff. Provide actionable insights if possible, be thorough in extracting all relevant rules."
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": GROK_MODEL,
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
                set_pending_feedback(sender_id, company_id, {'query': query, 'answer': answer})
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
        for file in matched_files:
            pdf_file = file.replace('.json', '.pdf')
            url = get_pdf_url(pdf_file)
            if url:
                filename = pdf_file.split('/')[-1]
                success = send_whatsapp_pdf(sender_id, url, filename, caption=self._get_clean_title(pdf_file).capitalize())
                if not success:
                    send_whatsapp_text(sender_id, "Error sending PDF.")
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
        self._process_query(sender_id, company_id, text)
        return True