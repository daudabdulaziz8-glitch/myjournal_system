# journal/mailer.py
import os
from datetime import datetime
from flask import current_app, render_template
from flask_mail import Message
from . import mail_ext

def _write_fallback(to: str, subject: str, html: str) -> str:
    """
    If SMTP fails or is blocked, write the rendered email to instance/outbox/*.html
    so you can open it in a browser (great for defense demos).
    """
    inst = current_app.instance_path
    outbox = os.path.join(inst, "outbox")
    os.makedirs(outbox, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    safe_subj = "".join(c for c in subject if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_") or "email"
    path = os.path.join(outbox, f"{ts}__{safe_subj}.html")

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!-- To: {to} -->\n")
        f.write(html or "")

    return path

def send_email(to: str, subject: str, template_name: str, **context) -> bool:
    """
    Render a Jinja template and try to send via Flask-Mail.
    If sending fails (network timeout, SMTP block), write an HTML file to instance/outbox.
    Returns True if sent; False if written to outbox (fallback).
    """
    msg = Message(
        subject=subject,
        recipients=[to],
        sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
    )
    msg.html = render_template(template_name, **context)

    try:
        mail_ext.send(msg)
        current_app.logger.info(f"[MAIL] Sent to {to}: {subject}")
        return True
    except Exception as e:
        path = _write_fallback(to, subject, msg.html)
        current_app.logger.warning(f"[MAIL] SEND FAILED ({e}); wrote fallback: {path}")
        return False
