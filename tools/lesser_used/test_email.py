import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()  # Load .env

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

try:
    # Setup message
    msg = MIMEText("This is a test email from ProQuery.")
    msg['Subject'] = "Test Email"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER  # Send to self

    # Connect and send
    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()  # TLS for port 587
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
    print("Test email sent successfully! Check your inbox/spam at info@proquery.live.")
except smtplib.SMTPAuthenticationError as e:
    print(f"Auth failed: Check EMAIL_USER/PASSWORD in .env. Error: {e}")
except Exception as e:
    print(f"Error: {e}")