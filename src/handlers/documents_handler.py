# src/handlers/documents_handler.py
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_list, send_whatsapp_pdf, send_whatsapp_text, send_whatsapp_buttons
from src.core.s3_handler import get_pdf_url
from src.core.db_handler import get_s3_client
from src.core.config import S3_BUCKET_NAME
from src.core.logger import logger
import re
from datetime import datetime

class DocumentsHandler(BaseHandler):
    priority = 80  # Lower than menu (100), but higher than others

    def _get_user_documents(self, sender_id: str, company_id: str):
        client = get_s3_client()
        if not client:
            return []

        prefix = f"{company_id}/employees/{sender_id}/"
        response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.pdf')]
        categorized = {
            'Job Description 📋': [],
            'Payslips 💰': [],
            'Employee Handbook 📖': [],
            'Performance Reviews ⭐': [],
            'Benefits Guide 🎁': [],
            'Warning Letters ⚠️': [],
            'Other': []
        }
        for file in files:
            filename = file.split('/')[-1].lower()  # Lower for case-insensitive match
            if 'job_description' in filename or 'jobdescription' in filename:
                categorized['Job Description 📋'].append(file)
            elif 'payslip' in filename:
                categorized['Payslips 💰'].append(file)
            elif 'handbook' in filename:
                categorized['Employee Handbook 📖'].append(file)
            elif 'review' in filename or 'performance' in filename:
                categorized['Performance Reviews ⭐'].append(file)
            elif 'benefits' in filename or 'benefit' in filename:
                categorized['Benefits Guide 🎁'].append(file)
            elif 'warning' in filename:
                categorized['Warning Letters ⚠️'].append(file)
            else:
                categorized['Other'].append(file)
        return categorized

    def _sort_files_by_date(self, files):
        def extract_date(filename):
            # Assume format like "Payslip - Month YYYY.pdf" or "Payslip_Dec_2025.pdf"
            match = re.search(r'(\bjan\b|\bfeb\b|\bmar\b|\bapr\b|\bmay\b|\bjun\b|\bjul\b|\baug\b|\bsep\b|\boct\b|\bnov\b|\bdec\b|january|february|march|april|may|june|july|august|september|october|november|december)[\s_-]*(\d{4})?', filename.lower())
            if match:
                month_str = match.group(1)[:3]  # Shorten to 3 letters
                year = match.group(2) or str(datetime.now().year)  # Default current year
                month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                month = month_map.get(month_str, 1)
                return datetime(int(year), month, 1)
            return datetime.min  # Oldest if no date

        return sorted(files, key=lambda f: extract_date(f.split('/')[-1]), reverse=True)  # Latest first

    def _send_documents_menu(self, sender_id: str, company_id: str):
        categorized = self._get_user_documents(sender_id, company_id)
        if not any(categorized.values()):
            send_whatsapp_text(sender_id, "No documents found for you.")
            self._send_feedback(sender_id, company_id)
            return

        sections = [{"title": "Document Types", "rows": []}]
        for category, files in categorized.items():
            if files:
                row_id = f"doc_type_{category.split(' ')[0].lower()}"  # e.g., doc_type_payslips
                sections[0]["rows"].append({
                    "id": row_id,
                    "title": category,
                    "description": f"{len(files)} available"
                })

        # Add global policies
        sections[0]["rows"].append({
            "id": "doc_policies",
            "title": "Company Policies/SOPs 📜",
            "description": "Query company policies"
        })

        success = send_whatsapp_list(
            sender_id,
            header="Documents 📄",
            body="Select a document type:",
            footer="Back to menu? Type 'menu'",
            sections=sections
        )
        if success:
            logger.info(f"Documents menu sent to {sender_id}")
        else:
            logger.error(f"Failed to send documents menu to {sender_id}")

    def _send_documents_by_type(self, sender_id: str, company_id: str, doc_type: str):
        categorized = self._get_user_documents(sender_id, company_id)
        files = self._sort_files_by_date(categorized.get(doc_type, []))
        if not files:
            send_whatsapp_text(sender_id, f"No {doc_type} found.")
            self._send_feedback(sender_id, company_id)
            return

        # Split into multiple sections if >10 files (WhatsApp max 10 rows/section, up to 10 sections)
        sections = []
        chunk_size = 10
        short_type = doc_type.split(' ')[0]  # Shorten for title, e.g., "Payslips" instead of "Payslips 💰"
        for i in range(0, len(files), chunk_size):
            chunk = files[i:i + chunk_size]
            section_title = f"{short_type} ({i+1}-{i+len(chunk)})"  # Keep under 24 chars
            section = {"title": section_title, "rows": []}
            for file in chunk:
                filename = file.split('/')[-1]
                row_id = f"doc_file_{filename}"
                row_title = filename.replace('.pdf', '')[:24]  # Truncate, remove extension
                section["rows"].append({
                    "id": row_id,
                    "title": row_title,
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
        else:
            logger.error(f"Failed to send {doc_type} list to {sender_id}")

    def _send_document(self, sender_id: str, company_id: str, filename: str):
        send_whatsapp_text(sender_id, f"Sending your {filename.replace('.pdf', '')}...")
        key = f"{company_id}/employees/{sender_id}/{filename}"
        url = get_pdf_url(key)
        if url:
            success = send_whatsapp_pdf(sender_id, url, filename, caption=f"Your {filename}")
            if success:
                logger.info(f"Sent PDF {filename} to {sender_id}")
            else:
                logger.error(f"Failed to send PDF {filename} to {sender_id}")
                send_whatsapp_text(sender_id, "Error sending file. Try again.")
        else:
            send_whatsapp_text(sender_id, "File not found. Contact HR.")
        # Send feedback after action complete
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

    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        int_type = interactive_data.get('type')
        if int_type == 'button_reply':
            button_id = interactive_data['button_reply']['id']
            if button_id == 'docs_btn':
                self._send_documents_menu(sender_id, company_id)
                return True
            # Handle feedback buttons (for now, just placeholders; email later)
            if button_id == 'feedback_yes':
                send_whatsapp_text(sender_id, "Thanks for the feedback!")
                return True
            if button_id == 'feedback_no':
                send_whatsapp_text(sender_id, "Sorry to hear that. Please provide more details or type 'skip'.")
                # Future: Set state for pending comment
                return True
        elif int_type == 'list_reply':
            reply_id = interactive_data['list_reply']['id']
            if reply_id == 'doc_policies':
                send_whatsapp_text(sender_id, "Query like 'recruitment policy' for details!")
                self._send_feedback(sender_id, company_id)
                return True
            elif reply_id.startswith('doc_type_'):
                doc_type_key = interactive_data['list_reply']['title']  # Use the full title directly, e.g., 'Payslips 💰'
                self._send_documents_by_type(sender_id, company_id, doc_type_key)
                return True
            elif reply_id.startswith('doc_file_'):
                filename = reply_id[9:]
                self._send_document(sender_id, company_id, filename)
                return True
        return False

    def try_process_text(self, sender_id: str, company_id: str, text: str) -> bool:
        lowered = text.lower().strip()
        if 'documents' in lowered or 'docs' in lowered:
            self._send_documents_menu(sender_id, company_id)
            return True
        # Handle specific queries like "payslips dec"
        if 'payslips' in lowered:
            month = lowered.split('payslips')[-1].strip()  # e.g., "dec"
            categorized = self._get_user_documents(sender_id, company_id)
            files = self._sort_files_by_date(categorized['Payslips 💰'])
            if month:
                # Simple filter: assume filenames like Jake_Zondagh_Payslip_Dec.pdf
                filtered = [f for f in files if month.lower() in f.lower()]
                if not filtered:
                    send_whatsapp_text(sender_id, f"No payslips found for {month}.")
                    self._send_feedback(sender_id, company_id)
                    return True
                files = filtered
            sent_count = 0
            for file in files:
                filename = file.split('/')[-1]
                send_whatsapp_text(sender_id, f"Sending your {filename.replace('.pdf', '')}...")
                url = get_pdf_url(file)
                if url:
                    send_whatsapp_pdf(sender_id, url, filename, caption=f"Your {filename}")
                    sent_count += 1
            if sent_count > 0:
                self._send_feedback(sender_id, company_id)
            return True
        # Similar for other types (expand as needed)
        # Future: Handle feedback comments here if state pending
        return False