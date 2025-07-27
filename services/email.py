import os
from fastapi_mail import ConnectionConfig
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD"),
    MAIL_FROM = os.getenv("MAIL_FROM"),
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER = os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", 'True').lower() in ('true', '1', 't'),
    MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", 'False').lower() in ('true', '1', 't'),
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True,
    TEMPLATE_FOLDER = Path(__file__).parent.parent / 'templates'
)