"""Envío de mails vía Gmail SMTP con App Password (SSL, puerto 465)."""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from finlab import config

log = logging.getLogger(__name__)


def send(subject: str, html: str, to: str | None = None) -> bool:
    """Manda un mail HTML. Devuelve True si salió OK."""
    user = config.env("GMAIL_USER", required=True)
    pwd = config.env("GMAIL_APP_PASSWORD", required=True)
    recipient = to or config.env("MAIL_TO") or user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Finance Lab <{user}>"
    msg["To"] = recipient
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(user, pwd)
            server.sendmail(user, [recipient], msg.as_string())
        log.info("Mail enviado a %s: %s", recipient, subject)
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("Falló el envío de mail: %s", exc)
        return False
