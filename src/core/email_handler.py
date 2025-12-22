# src/core/email_handler.py
import smtplib
from email.mime.text import MIMEText
from src.core.config import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FEEDBACK_TO, EMAIL_HR_TO
from src.core.db_handler import get_user_info
from src.core.logger import logger
def send_feedback_email(sender_id: str, helpful: bool, query: str, answer: str, comment: str = None) -> bool:
    company_id, role, person_name, _ = get_user_info(sender_id)
    person_name = person_name or "Unknown User"
    status = "Helpful" if helpful else "Not Helpful"
    subject = f"Feedback: {status} - Query: {query[:50]}..." if len(
        query) > 50 else f"Feedback: {status} - Query: {query}"
    body = f"User: {person_name} ({sender_id})\n"
    body += f"Role: {role}\n"
    body += f"Company: {company_id}\n\n"
    body += f"Query: {query}\n\n"
    body += f"Answer: {answer}\n\n"
    body += f"Helpful: {'Yes' if helpful else 'No'}\n\n"
    if comment:
        body += f"Comment: {comment}\n"
    else:
        body += "Comment: None\n"
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_FEEDBACK_TO
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, EMAIL_FEEDBACK_TO, msg.as_string())
        logger.info(f"Feedback email sent for {sender_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending feedback email: {e}")
        return False
def send_hr_email(sender_id: str, query: str, urgency: str = "Standard") -> bool:
    company_id, role, person_name, _ = get_user_info(sender_id)
    person_name = person_name or "Unknown User"
    subject = f"HR Query from {person_name} ({sender_id}) - Urgency: {urgency}"
    body = f"User: {person_name} ({sender_id})\nRole: {role}\nCompany: {company_id}\nUrgency: {urgency}\n\nQuery: {query}"
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_HR_TO
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, EMAIL_HR_TO, msg.as_string())
        logger.info(f"HR email sent for {sender_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending HR email: {e}")
        return False