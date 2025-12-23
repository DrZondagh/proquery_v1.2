# src/core/pdf_sender.py
import time
from src.core.s3_handler import get_pdf_url
from src.core.whatsapp_handler import send_whatsapp_pdf, send_whatsapp_text
from src.core.logger import logger
from botocore.exceptions import ClientError

def send_pdf(sender_id: str, company_id: str, json_filepath: str, caption: str = "") -> bool:
    """
    Immutable function to send a PDF based on JSON filepath.
    - Replaces .json with .pdf
    - Checks existence via head_object
    - Generates presigned URL with attachment disposition
    - Sends "Sending [name]..." text
    - Sends PDF with caption
    - Delays 2s for sequencing
    - Returns True if sent, False otherwise (sends error text)
    """
    pdf_filepath = json_filepath.replace('.json', '.pdf')
    filename = pdf_filepath.split('/')[-1]
    nice_name = filename.replace('.pdf', '').replace('_', ' ').capitalize()

    from src.core.db_handler import get_s3_client
    client = get_s3_client()
    if not client:
        send_whatsapp_text(sender_id, "Error: Unable to connect to storage.")
        return False

    # Existence check
    try:
        client.head_object(Bucket=src.core.config.S3_BUCKET_NAME, Key=pdf_filepath)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            logger.warning(f"PDF not found: {pdf_filepath}")
            send_whatsapp_text(sender_id, f"{nice_name} PDF not available.")
            return False
        else:
            logger.error(f"Error checking PDF: {e}")
            send_whatsapp_text(sender_id, "Error checking file availability.")
            return False

    url = get_pdf_url(pdf_filepath)
    if not url:
        send_whatsapp_text(sender_id, f"Error generating link for {nice_name}.")
        return False

    send_whatsapp_text(sender_id, f"Sending {nice_name}...")
    success = send_whatsapp_pdf(sender_id, url, filename, caption=caption)
    if success:
        logger.info(f"Sent PDF {pdf_filepath} to {sender_id}")
        time.sleep(2)  # Delay for sequencing
        return True
    else:
        logger.error(f"Failed to send PDF {pdf_filepath} to {sender_id}")
        send_whatsapp_text(sender_id, f"Error sending {nice_name}. Try again.")
        return False