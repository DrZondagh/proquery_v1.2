# src/handlers/query_handler.py
import json
import requests
import re
import difflib
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_text, send_whatsapp_buttons
from src.core.db_handler import get_s3_client, get_bot_state, update_bot_state, set_pending_feedback
from src.core.config import S3_BUCKET_NAME, GROK_API_KEY, GROK_MODEL
from src.core.logger import logger
from src.core.pdf_sender import send_pdf  # New immutable PDF sender

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
            files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.json') and 'processed_messages.json' not in obj['Key'] and 'queries.json' not in obj['Key'] and 'bot_state.json' not in obj['Key'] and 'user.json' not in obj['Key']]
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
        return filename.capitalize()

    def _load_content_snippet(self, company_id: str, filepath: str) -> str:
        client = get_s3_client()
        if not client:
            return ""
        try:
            obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=filepath)
            data = json.loads(obj['Body'].read().decode('utf-8'))
            if not isinstance(data, dict):
                return ""
            content = data.get('content', '')
            return content[:1000]
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
                    snippet_words = set(re.findall(r'\w+', snippet.lower()))
                    common = query_words.intersection(title_words.union(snippet_words))
                    score = len(common)
                    if score == 0:
                        fuzzy_score = max(
                            difflib.SequenceMatcher(None, query.lower(), title.lower()).ratio(),
                            difflib.SequenceMatcher(None, query.lower(), snippet.lower()).ratio()
                        )
                        if fuzzy_score > 0.3:  # Lower threshold for broader matches
                            score = 1
                    if 'employees' in f:  # Prioritize personal
                        score += 5
                    if score > 0:
                        scores.append((score, f))
                except Exception:
                    pass
        scores.sort(reverse=True)
        return [f for score, f in scores[:20]]  # Limit to top 20 for efficiency

    def _is_direct_doc_request(self, text: str) -> str | None:
        lowered = text.lower().strip()
        direct_map = {
            'payslips': '💰 Payslips',
            'payslip': '💰 Payslips',
            'benefits guide': '📌 Benefits Guide',
            'benefits': '📌 Benefits Guide',
            'employee handbook': '📖 Employee Handbook',
            'handbook': '📖 Employee Handbook',
            'performance reviews': '⭐ Performance Reviews',
            'reviews': '⭐ Performance Reviews',
            'job description': '📋 Job Description',
            'warnings': '⚠️ Warning Letters',
            'warning letters': '⚠️ Warning Letters'
        }
        for key, cat in direct_map.items():
            if lowered == key or lowered.startswith(key + ' '):
                return cat
        return None

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
            doc_entries.append(f"Title: {title}\nPath: {f}\nSnippet: {snippet}")
        docs_str = "\n\n".join(doc_entries)
        prompt = f"User query: '{query}'\nDocuments (titles, paths, snippets):\n{docs_str}\n\nSelect ALL relevant files (at least 3 if possible, up to 15). Consider semantics, synonyms (e.g., 'leave' = vacation/absence/benefits/time off), misspellings (e.g., 'polciy' = policy), indirect relevance. Prioritize personal files. Output ONLY paths, one per line."
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}
        try:
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload)
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content'].strip()
                selected_paths = [line.strip() for line in answer.split('\n') if line.strip() and any(line in f for f in all_files)]
                if len(selected_paths) < 3 and len(pre_filtered) >= 3:
                    selected_paths = pre_filtered[:3]
                return selected_paths
            else:
                logger.error(f"Grok error: {response.text}")
                return pre_filtered[:5] if pre_filtered else []
        except Exception as e:
            logger.error(f"Grok call failed: {e}")
            return pre_filtered[:5] if pre_filtered else []

    def _get_summaries(self, sender_id: str, company_id: str, matched_files: list[str], query: str) -> str:
        if not matched_files:
            return "No relevant documents found."
        summaries = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {executor.submit(self._load_content, company_id, f): f for f in matched_files}
            contents = {}
            for future in as_completed(future_to_file):
                f = future_to_file[future]
                try:
                    contents[f] = future.result()
                except:
                    contents[f] = ""
        for i, f in enumerate(matched_files, 1):
            content = contents.get(f, "")
            if not content:
                continue
            title = self._get_clean_title(f)
            prompt = f"Document: {title}\nContent: {content}\n\nQuery: {query}\n\nOutput: Relevance (High/Medium/Low based on match). Plain English summary (1-2 sentences, simple for blue-collar workers). Key sections with **bold** highlights. Actionable insights if any. Format: {i}. {title} - Relevance: [level]\nSummary: [text]\nSections: [list]"
            headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}
            try:
                response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload)
                if response.status_code == 200:
                    summary = response.json()['choices'][0]['message']['content'].strip()
                    summaries.append(summary)
            except Exception as e:
                logger.error(f"Summary failed for {f}: {e}")
                summaries.append(f"{i}. {title} - Relevance: Medium\nSummary: Content loading error. Check document manually.")
        return "\n\n".join(summaries) if summaries else "Error generating summaries."

    def _process_query(self, sender_id: str, company_id: str, query: str, only_sops: bool = False):
        send_whatsapp_text(sender_id, "Searching documents... 🚀")
        matched_files = self._find_relevant_files(sender_id, company_id, query, only_sops)
        if not matched_files:
            answer = "No matches. Try rephrasing or check 'Documents' menu."
            send_whatsapp_text(sender_id, answer)
            set_pending_feedback(sender_id, company_id, {'query': query, 'answer': answer})
            self._send_feedback(sender_id, company_id)
            self._clear_context(sender_id, company_id)
            return
        answer = self._get_summaries(sender_id, company_id, matched_files, query)
        if answer:
            send_whatsapp_text(sender_id, answer)
        else:
            answer = "Error summarizing. Sending docs anyway."
            send_whatsapp_text(sender_id, answer)
        sent_count = 0
        for file in matched_files:
            caption = self._get_clean_title(file)
            if send_pdf(sender_id, company_id, file, caption):
                sent_count += 1
        if sent_count == 0:
            send_whatsapp_text(sender_id, "No PDFs sent. Contact HR.")
        set_pending_feedback(sender_id, company_id, {'query': query, 'answer': answer})
        self._send_feedback(sender_id, company_id)
        self._clear_context(sender_id, company_id)

    def _send_feedback(self, sender_id: str, company_id: str):
        buttons = [
            {"type": "reply", "reply": {"id": "feedback_yes", "title": "Yes 👍"}},
            {"type": "reply", "reply": {"id": "feedback_no", "title": "No 👎"}},
            {"type": "reply", "reply": {"id": "main_menu_btn", "title": "Main Menu ↩️"}}
        ]
        success = send_whatsapp_buttons(sender_id, "Was this helpful?", buttons)
        if success:
            logger.info(f"Feedback sent to {sender_id}")

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
        direct_cat = self._is_direct_doc_request(text)
        if direct_cat:
            from src.handlers.documents_handler import DocumentsHandler
            dh = DocumentsHandler()
            dh._send_documents_by_type(sender_id, company_id, direct_cat)
            return True
        context = state.get('context')
        only_sops = (context == 'sop_query')
        self._process_query(sender_id, company_id, text, only_sops)
        return True