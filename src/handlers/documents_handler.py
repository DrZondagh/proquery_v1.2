# src/handlers/documents_handler.py
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_list, send_whatsapp_pdf, send_whatsapp_text, send_whatsapp_buttons
from src.core.s3_handler import get_pdf_url
from src.core.db_handler import get_s3_client, set_pending_feedback, get_bot_state, update_bot_state
from src.core.config import S3_BUCKET_NAME
from src.core.logger import logger
import re
from datetime import datetime
import time

class DocumentsHandler(BaseHandler):
    priority = 80

    def _get_user_documents(self, sender_id: str, company_id: str):
        client = get_s3_client()
        if not client:
            return {}
        prefix = f"{company_id}/employees/{sender_id}/"
        response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.pdf')]
        categorized = {
            '📋 Job Description': [],
            '💰 Payslips': [],
            '📖 Employee Handbook': [],
            '⭐ Performance Reviews': [],
            '📌 Benefits Guide': [],
            '⚠️ Warning Letters': [],
            'Other': []
        }
        for file in files:
            filename = file.split('/')[-1].lower()
            if 'job_description' in filename or 'jobdescription' in filename:
                categorized['📋 Job Description'].append(file)
            elif 'payslip' in filename:
                categorized['💰 Payslips'].append(file)
            elif 'handbook' in filename:
                categorized['📖 Employee Handbook'].append(file)
            elif 'review' in filename or 'performance' in filename:
                categorized['⭐ Performance Reviews'].append(file)
            elif 'benefits' in filename or 'benefit' in filename:
                categorized['📌 Benefits Guide'].append(file)
            elif 'warning' in filename:
                categorized['⚠️ Warning Letters'].append(file)
            else:
                categorized['Other'].append(file)
        return categorized

    def _sort_files_by_date(self, files):
        def extract_date(filename):
            match = re.search(r'(\bjan\b|\bfeb\b|\bmar\b|\bapr\b|\bmay\b|\bjun\b|\bjul\b|\baug\b|\bsep\b|\boct\b|\bnov\b|\bdec\b|january|february|march|april|may|june|july|august|september|october|november|december)[\s_-]*(\d{4})?', filename.lower())
            if match:
                month_str = match.group(1)[:3]
                year = match.group(2) or str(datetime.now().year)
                month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                month = month_map.get(month_str, 1)
                return datetime(int(year), month, 1)
            return datetime.min
        return sorted(files, key=lambda f: extract_date(f.split('/')[-1]), reverse=True)

    def _get_nice_label(self, filename: str, category: str) -> str:
        base = filename.replace('.pdf', '').replace('jake_zondagh_', '', 1).replace('_', ' ').strip()[:24]
        if 'payslip' in category.lower():
            match = re.search(r'(\bjan\b|\bfeb\b|\bmar\b|\bapr\b|\bmay\b|\bjun\b|\bjul\b|\baug\b|\bsep\b|\boct\b|\bnov\b|\bdec\b|january|february|march|april|may|june|july|august|september|october|november|december)[\s_-]*(\d{4})?', filename.lower())
            if match:
                month_str = match.group(1)[:3].capitalize()
                year = match.group(2) or str(datetime.now().year)
                return f"{month_str} {year}"
        elif 'review' in category.lower() or 'performance' in category.lower():
            match = re.search(r'(q[1-4])[\s_-]*(\d{4})?', filename.lower())
            if match:
                quarter = match.group(1).upper()
                year = match.group(2) or str(datetime.now().year)
                return f"{quarter} {year} Review"
            return base
        return base.capitalize()

    def _send_documents_menu(self, sender_id: str, company_id: str):
        categorized = self._get_user_documents(sender_id, company_id)
        if not any(categorized.values()):
            answer = "No documents found for you."
            send_whatsapp_text(sender_id, answer)
            set_pending_feedback(sender_id, company_id, {'query': "Requested documents", 'answer': answer})
            self._send_feedback(sender_id, company_id)
            return
        sections = [{"title": "Document Types", "rows": []}]
        for category, files in categorized.items():
            if files:
                text_parts = ' '.join(word for word in category.split() if not re.match(r'^\W+$', word))
                row_id_base = '_'.join(text_parts.lower().split())
                row_id = f"doc_type_{row_id_base}"
                sections[0]["rows"].append({
                    "id": row_id,
                    "title": category,
                    "description": f"{len(files)} available"
                })
        sections[0]["rows"].append({
            "id": "doc_policies",
            "title": "📜 Company Policies/SOPs",
            "description": "Query company policies"
        })
        success = send_whatsapp_list(
            sender_id,
            header="📄 Documents",
            body="Select a document type:",
            footer="Back to menu? Type 'menu'",
            sections=sections
        )
        if success:
            logger.info(f"Documents menu sent to {sender_id}")

    def _send_documents_by_type(self, sender_id: str, company_id: str, doc_type: str):
        categorized = self._get_user_documents(sender_id, company_id)
        files = self._sort_files_by_date(categorized.get(doc_type, []))
        if not files:
            answer = f"No {doc_type} found."
            send_whatsapp_text(sender_id, answer)
            set_pending_feedback(sender_id, company_id, {'query': f"Requested {doc_type}", 'answer': answer})
            self._send_feedback(sender_id, company_id)
            return
        if len(files) == 1:
            filename = files[0].split('/')[-1]
            self._send_document(sender_id, company_id, filename)
            return
        sections = []
        chunk_size = 10
        text_parts = ' '.join(word for word in doc_type.split() if not re.match(r'^\W+$', word))
        short_type = text_parts
        for i in range(0, len(files), chunk_size):
            chunk = files[i:i + chunk_size]
            section_title = f"{short_type} ({i+1}-{i+len(chunk)})" if len(files) > chunk_size else short_type
            section = {"title": section_title, "rows": []}
            for file in chunk:
                filename = file.split('/')[-1]
                row_id = f"doc_file_{filename}"
                nice_label = self._get_nice_label(filename, doc_type)
                section["rows"].append({
                    "id": row_id,
                    "title": nice_label,
                    "description": "Tap to download"
                })
            sections.append(section)
        success = send_whatsapp_list(
            sender_id,
            header=doc_type,
            body="Select a file (latest first):",
            footer="Back? Type 'back'",
            sections=sections
        )
        if success:
            logger.info(f"{doc_type} list sent to {sender_id}")

    def _send_document(self, sender_id: str, company_id: str, filename: str):
        key = f"{company_id}/employees/{sender_id}/{filename}"
        url = get_pdf_url(key)
        answer = f"Sent {filename}"
        if url:
            send_whatsapp_text(sender_id, f"Sending your {filename.replace('.pdf', '')}...")
            success = send_whatsapp_pdf(sender_id, url, filename, caption=f"Your {filename}")
            if success:
                logger.info(f"Sent PDF {filename} to {sender_id}")
            else:
                logger.error(f"Failed to send PDF {filename} to {sender_id}")
                send_whatsapp_text(sender_id, "Error sending file. Try again.")
                answer = "Error sending file. Try again."
            time.sleep(2)
        else:
            error_msg = "File not found. Contact HR."
            send_whatsapp_text(sender_id, error_msg)
            answer = error_msg
        set_pending_feedback(sender_id, company_id, {'query': f"Requested {filename}", 'answer': answer})
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

    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        int_type = interactive_data.get('type')
        if int_type == 'button_reply':
            button_id = interactive_data['button_reply']['id']
            if button_id == 'docs_btn':
                self._send_documents_menu(sender_id, company_id)
                return True
        elif int_type == 'list_reply':
            reply_id = interactive_data['list_reply']['id']
            if reply_id == 'doc_policies':
                send_whatsapp_text(sender_id, "Query like 'recruitment policy' for details!")
                state = get_bot_state(sender_id, company_id)
                state['context'] = 'sop_query'
                update_bot_state(sender_id, company_id, state)
                return True
            elif reply_id.startswith('doc_type_'):
                doc_type_key = interactive_data['list_reply']['title']
                self._send_documents_by_type(sender_id, company_id, doc_type_key)
                return True
            elif reply_id.startswith('doc_file_'):
                filename = reply_id[9:]
                self._send_document(sender_id, company_id, filename)
                return True
        return False

    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        state = get_bot_state(sender_id, company_id)
        if state.get('context') == 'feedback_comment':
            return False
        lowered = text.lower().strip()
        if 'documents' in lowered or 'docs' in lowered:
            self._send_documents_menu(sender_id, company_id)
            return True
        category_map = {
            'payslips': '💰 Payslips',
            'benefits': '📌 Benefits Guide',
            'handbook': '📖 Employee Handbook',
            'reviews': '⭐ Performance Reviews',
            'job description': '📋 Job Description',
            'warnings': '⚠️ Warning Letters'
        }
        for key, cat in category_map.items():
            if key in lowered:
                filter_term = lowered.replace(key, '').strip()
                if filter_term:
                    categorized = self._get_user_documents(sender_id, company_id)
                    files = self._sort_files_by_date(categorized[cat])
                    filtered = [f for f in files if filter_term.lower() in f.lower()]
                    if not filtered:
                        answer = f"No {key} found for {filter_term}."
                        send_whatsapp_text(sender_id, answer)
                        set_pending_feedback(sender_id, company_id, {'query': lowered, 'answer': answer})
                        self._send_feedback(sender_id, company_id)
                        return True
                    sent_count = 0
                    sent_files = []
                    for file in filtered:
                        filename = file.split('/')[-1]
                        send_whatsapp_text(sender_id, f"Sending your {filename.replace('.pdf', '')}...")
                        url = get_pdf_url(file)
                        if url:
                            send_whatsapp_pdf(sender_id, url, filename, caption=f"Your {filename}")
                            time.sleep(2)
                            sent_count += 1
                            sent_files.append(filename)
                    answer = f"Sent {sent_count} files: {', '.join(sent_files)}" if sent_count > 0 else "Error sending files."
                    set_pending_feedback(sender_id, company_id, {'query': lowered, 'answer': answer})
                    if sent_count > 0:
                        self._send_feedback(sender_id, company_id)
                    return True
                else:
                    self._send_documents_by_type(sender_id, company_id, cat)
                    return True
        return False