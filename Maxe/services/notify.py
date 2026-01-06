import os
import smtplib
from email.message import EmailMessage
from typing import List

def send_coach_email(
    to_email: str,
    subject: str,
    body: str,
    reasons: List[str]
):
    """
    Simple SMTP email sender.
    Requires env vars:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass, smtp_from]):
        raise RuntimeError("SMTP env vars not set. Set SMTP_HOST/USER/PASS/FROM/PORT.")

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body + f"\n\nEscalation reasons: {', '.join(reasons)}")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
