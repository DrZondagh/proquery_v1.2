# src/handlers/documents_handler.py
from src.core.base_handler import BaseHandler
from src.core.whatsapp_handler import send_whatsapp_list, send_whatsapp_pdf, send_whatsapp_text
from src.core.s3_handler import get_pdf_url
from src.core.db_handler import get_s3_client
from src.core.config import S3_BUCKET_NAME
from src.core.logger import logger

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
            filename = file.split('/')[-1]
            if 'Job_Description' in filename:
                categorized['Job Description 📋'].append(file)  # Use full key for sending
            elif 'Payslip' in filename:
                categorized['Payslips 💰'].append(file)
            elif 'Handbook' in filename:
                categorized['Employee Handbook 📖'].append(file)
            elif 'Review' in filename:
                categorized['Performance Reviews ⭐'].append(file)
            elif 'Benefits' in filename:
                categorized['Benefits Guide 🎁'].append(file)
            elif 'Warning' in filename:
                categorized['Warning Letters ⚠️'].append(file)
            else:
                categorized['Other'].append(file)
        return categorized

    def _send_documents_menu(self, sender_id: str, company_id: str):
        categorized = self._get_user_documents(sender_id, company_id)
        if not any(categorized.values()):
            send_whatsapp_text(sender_id, "No documents found for you.")
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
        files = categorized.get(doc_type, [])
        if not files:
            send_whatsapp_text(sender_id, f"No {doc_type} found.")
            return

        sections = [{"title": doc_type, "rows": []}]
        for file in files:
            filename = file.split('/')[-1]
            row_id = f"doc_file_{filename}"
            sections[0]["rows"].append({
                "id": row_id,
                "title": filename[:24],  # Truncate for WhatsApp limit
                "description": "Tap to download"
            })

        success = send_whatsapp_list(
            sender_id,
            header=doc_type,
            body="Select a file:",
            footer="Back? Type 'back'",
            sections=sections
        )
        if success:
            logger.info(f"{doc_type} list sent to {sender_id}")
        else:
            logger.error(f"Failed to send {doc_type} list to {sender_id}")

    def _send_document(self, sender_id: str, company_id: str, filename: str):
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

    def try_process_interactive(self, sender_id: str, company_id: str, interactive_data: dict) -> bool:
        int_type = interactive_data.get('type')
        if int_type == 'button_reply':
            if interactive_data['button_reply']['id'] == 'docs_btn':
                self._send_documents_menu(sender_id, company_id)
                return True
        elif int_type == 'list_reply':
            reply_id = interactive_data['list_reply']['id']
            if reply_id == 'doc_policies':
                send_whatsapp_text(sender_id, "Query like 'recruitment policy' for details!")
                return True  # Routes to SOP module later
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
            files = categorized['Payslips 💰']
            if month:
                # Simple filter: assume filenames like Jake_Zondagh_Payslip_Dec.pdf
                filtered = [f for f in files if month.lower() in f.lower()]
                if not filtered:
                    send_whatsapp_text(sender_id, f"No payslips found for {month}.")
                    return True
                files = filtered
            for file in files:
                filename = file.split('/')[-1]
                url = get_pdf_url(file)
                if url:
                    send_whatsapp_pdf(sender_id, url, filename, caption=f"Your {filename}")
            return True
        # Similar for other types (expand as needed)
        return False