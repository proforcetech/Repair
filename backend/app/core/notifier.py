# backend/app/core/notifier.py

## This file handles email notifications for the application.
# It uses the aiosmtplib library to send emails asynchronously.
# It constructs an email message with the specified recipient, subject, and body.
# Make sure to set the SMTP configuration in your environment variables.
from dotenv import load_dotenv
import aiosmtplib
from email.message import EmailMessage
import os
import smtplib
from email.mime.text import MIMEText
load_dotenv()


# This module handles email notifications for the application.
async def send_email(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = os.getenv("EMAIL_FROM")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname=os.getenv("SMTP_HOST"),
        port=int(os.getenv("SMTP_PORT", 587)),
        username=os.getenv("SMTP_USER"),
        password=os.getenv("SMTP_PASS"),
        start_tls=True,
    )


# Placeholder SMS sender used throughout the application.
async def send_sms(phone: str, body: str) -> None:
    """Send an SMS notification (stub implementation)."""

    # Real implementation should integrate with Twilio or similar.
    # The async signature is kept for compatibility with callers and tests can
    # monkeypatch this coroutine to capture messages without performing network IO.
    return None


# This function sends a notification email to the user.
# It uses the smtplib library to send an email with the specified subject and body.
# The email is sent from a predefined "noreply" address.
# Make sure to replace the SMTP configuration with your actual settings.
async def notify_user(email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "noreply@repairshop.com"
    msg["To"] = email

    # Replace with actual SMTP config
    smtp = smtplib.SMTP("localhost")
    smtp.send_message(msg)
    smtp.quit()

