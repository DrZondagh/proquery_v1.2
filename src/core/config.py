# src/core/config.py
import os
from dotenv import load_dotenv
load_dotenv()  # Load once here
# Required envs (expand as needed)
REQUIRED_ENVS = [
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "S3_BUCKET_NAME",
    "WHATSAPP_API_URL", "WHATSAPP_AUTH_TOKEN", "VERIFY_TOKEN_META", "GROK_API_KEY",
    "EMAIL_HOST", "EMAIL_PORT", "EMAIL_USER", "EMAIL_PASSWORD", "BOT_PHONE_NUMBER"
]
# Check and raise early
missing = [env for env in REQUIRED_ENVS if not os.getenv(env)]
if missing:
    raise ValueError(f"Missing env vars: {', '.join(missing)}")
# Export as constants (immutable)
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
WHATSAPP_AUTH_TOKEN = os.getenv("WHATSAPP_AUTH_TOKEN")  # Matches your .env name
VERIFY_TOKEN_META = os.getenv("VERIFY_TOKEN_META")
GROK_API_KEY = os.getenv("GROK_API_KEY")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
BOT_PHONE_NUMBER = os.getenv("BOT_PHONE_NUMBER")