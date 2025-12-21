# src/core/whatsapp_handler.py
import requests
import json
from src.core.config import WHATSAPP_API_URL, WHATSAPP_AUTH_TOKEN, BOT_PHONE_NUMBER
from src.core.logger import logger

def send_whatsapp_text(recipient: str, text: str) -> bool:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"body": text}
    }
    return _send_whatsapp(payload)

def send_whatsapp_buttons(recipient: str, text: str, buttons: list[dict]) -> bool:
    # buttons example: [{"type": "reply", "reply": {"id": "btn_id", "title": "Button Text"}}]
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {"buttons": buttons}
        }
    }
    return _send_whatsapp(payload)

def send_whatsapp_list(recipient: str, header: str, body: str, footer: str, sections: list[dict]) -> bool:
    # sections example: [{"title": "Section Title", "rows": [{"id": "row_id", "title": "Row Title", "description": "Desc"}]}]
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": header},
            "body": {"text": body},
            "footer": {"text": footer},
            "action": {"button": "Select", "sections": sections}
        }
    }
    return _send_whatsapp(payload)

def send_whatsapp_pdf(recipient: str, pdf_url: str, filename: str, caption: str = "") -> bool:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "document",
        "document": {
            "link": pdf_url,
            "caption": caption,
            "filename": filename
        }
    }
    return _send_whatsapp(payload)

def _send_whatsapp(payload: dict) -> bool:
    headers = {
        "Authorization": f"Bearer {WHATSAPP_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            logger.info(f"WhatsApp message sent to {payload['to']}: {payload}")
            return True
        else:
            logger.error(f"Failed to send WhatsApp message: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        return False