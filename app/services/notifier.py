from __future__ import annotations

import smtplib
from email.message import EmailMessage


def send_email(
    smtp_host: str | None,
    smtp_port: int,
    smtp_username: str | None,
    smtp_password: str | None,
    mail_from: str | None,
    mail_to: str | None,
    subject: str,
    body: str,
) -> bool:
    if not (smtp_host and mail_from and mail_to):
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)
        server.send_message(msg)
    return True
