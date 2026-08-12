"""Outbound email — stdlib smtplib only, no new dependency.

Configured entirely through environment variables so nothing secret lands in
the database or the repo:

  SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS, SMTP_FROM
  SMTP_STARTTLS  "0" to disable (default on)
  MAIL_DRY_RUN   "1" -> render and log the message, never send it

With no SMTP_HOST the feature is simply inactive: is_configured() is False, the
Beheer page says so, and nothing ever raises. That matters because the sync
thread calls into here — an exception would take the whole sync down with it.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage


def _env(name, default=""):
    return (os.environ.get(name) or default).strip()


def is_configured():
    return bool(_env("SMTP_HOST") and _env("SMTP_FROM"))


def is_dry_run():
    return _env("MAIL_DRY_RUN", "1") == "1"


def status():
    """(configured, dry_run, from_address) — for the Beheer page."""
    return is_configured(), is_dry_run(), _env("SMTP_FROM")


def send(to, subject, body):
    """Send one plain-text mail. Returns (ok, detail); never raises.

    Dry run is the DEFAULT: the first deploy renders the digests into the logs
    so the recipient mapping can be checked against real data before a single
    message reaches a client's inbox.
    """
    if not to:
        return False, "no recipient"
    if not is_configured():
        return False, "smtp not configured"
    if is_dry_run():
        print(f"[mail dry-run] to={to} subject={subject!r}\n{body}", flush=True)
        return True, "dry-run"

    msg = EmailMessage()
    msg["From"] = _env("SMTP_FROM")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    host, port = _env("SMTP_HOST"), int(_env("SMTP_PORT", "587") or 587)
    user, pw = _env("SMTP_USER"), _env("SMTP_PASS")
    try:
        with smtplib.SMTP(host, port, timeout=20) as s:
            if _env("SMTP_STARTTLS", "1") == "1":
                s.starttls(context=ssl.create_default_context())
            if user:
                s.login(user, pw)
            s.send_message(msg)
        return True, "sent"
    except Exception as e:                      # noqa: BLE001 - never break the sync
        return False, f"{type(e).__name__}: {e}"
