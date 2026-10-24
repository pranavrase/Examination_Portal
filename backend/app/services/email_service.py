import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """
    Send an email using SMTP configuration.
    Returns True if successful, False otherwise.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP configuration not set. Email not sent.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
        msg["To"] = to_email

        if text_content:
            part_text = MIMEText(text_content, "plain")
            msg.attach(part_text)

        part_html = MIMEText(html_content, "html")
        msg.attach(part_html)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


def send_otp_email(to_email: str, otp: str, expiry_minutes: int) -> bool:
    """
    Send OTP email for password reset.
    """
    subject = "Examination Portal - Password Reset OTP"

    text_content = f"""Your password reset OTP is: {otp}

This OTP will expire in {expiry_minutes} minutes.
If you did not request a password reset, you can ignore this email."""

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c3e50;">Password Reset OTP</h2>
            <p>Your password reset OTP is:</p>
            <div style="background: #f8f9fa; padding: 20px; text-align: center; border-radius: 5px; margin: 20px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #007bff;">{otp}</span>
            </div>
            <p>This OTP will expire in <strong>{expiry_minutes} minutes</strong>.</p>
            <p>If you did not request a password reset, you can ignore this email.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="font-size: 12px; color: #777;">This is an automated message from Examination Portal. Please do not reply.</p>
        </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, html_content, text_content)
