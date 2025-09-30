# journal/mailer.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _smtp_config():
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASS", ""),
        "use_tls": os.getenv("SMTP_USE_TLS", "1") not in ("0", "false", "False"),
        "from_addr": os.getenv("MAIL_FROM", "no-reply@facoms.local"),
    }


def send_email(to_addr: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    """
    Sends an email via SMTP using environment variables.

    Required ENV:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_USE_TLS (0/1), MAIL_FROM
    If missing, falls back to printing the email (no exception).
    """
    cfg = _smtp_config()

    if not (cfg["host"] and cfg["user"] and cfg["password"]):
        # Dev fallback: print instead of sending
        print("\n=== EMAIL (DEV PRINT) ===")
        print("To:   ", to_addr)
        print("From: ", cfg["from_addr"])
        print("Subj: ", subject)
        print("BODY (HTML):\n", html_body)
        print("=========================\n")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from_addr"]
    msg["To"] = to_addr

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            if cfg["use_tls"]:
                server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from_addr"], [to_addr], msg.as_string())
        return True
    except Exception as e:
        print(f"[mailer] send_email failed: {e}")
        return False
