"""SMTP email delivery for AAGuardian verification and password-reset codes."""
import logging
import os
import smtplib
import socket
import ssl

import httpx
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from app.core.config import settings

log = logging.getLogger("otp")


class EmailDeliveryError(RuntimeError):
    """SMTP failed. `.reason` explains why in plain words (for the server console, not the app)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


# ---------------------------------------------------------------- Resend ----

def _describe_resend_error(resp: httpx.Response) -> str:
    try:
        detail = str(resp.json().get("message", ""))[:200]
    except Exception:  # noqa: BLE001
        detail = resp.text[:200]
    if resp.status_code == 401:
        return ("Resend rejected the API key. Create an API key in the Resend dashboard "
                "(API Keys > Create API Key) and set RESEND_API_KEY in Render's environment.")
    if resp.status_code == 403:
        return (f"Resend refused the sender: {detail}. On the free plan you must send from "
                "'onboarding@resend.dev' and only to the email address you signed up with, "
                "until you verify your own domain in Resend (Domains).")
    if resp.status_code == 422:
        return (f"Resend rejected the message: {detail}. On the free plan the recipient must be "
                "the address you signed up to Resend with.")
    return f"Resend answered HTTP {resp.status_code}: {detail}"


def _send_resend(to: str, subject: str, body: str) -> None:
    """Send through Resend's HTTPS API. Works on hosts that block SMTP ports."""
    api_key = getattr(settings, "resend_api_key", None) or os.environ.get("RESEND_API_KEY") or ""
    payload = {
        "from": "AAGuardian <onboarding@resend.dev>",
        "to": [to],
        "subject": subject,
        "text": body,
    }
    headers = {"Authorization": f"Bearer {api_key}", "content-type": "application/json"}
    last = "unknown error"
    for attempt in (1, 2):
        try:
            resp = httpx.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=15)
        except httpx.HTTPError as exc:
            last = f"Could not reach Resend ({exc.__class__.__name__}). Check the server's internet connection."
            log.warning("Resend attempt %d/2 failed: %s", attempt, exc)
            continue
        if resp.status_code in (200, 201, 202):
            return
        last = _describe_resend_error(resp)
        if resp.status_code in (401, 403, 422):  # retrying cannot help
            break
        log.warning("Resend attempt %d/2 failed: HTTP %s", attempt, resp.status_code)
    log.error("EMAIL NOT SENT to %s: %s", to, last)
    raise EmailDeliveryError(last)


# ---------------------------------------------------------------- Brevo ----

def brevo_configured() -> bool:
    return bool(settings.brevo_api_key)


def resend_configured() -> bool:
    return bool(getattr(settings, "resend_api_key", None) or os.environ.get("RESEND_API_KEY"))


def _sender_address() -> str | None:
    return settings.email_from or settings.smtp_from_email or settings.smtp_user


def _describe_brevo_error(resp: httpx.Response) -> str:
    try:
        detail = str(resp.json().get("message", ""))[:200]
    except Exception:  # noqa: BLE001
        detail = resp.text[:200]
    if resp.status_code == 401:
        return ("Brevo rejected the API key. Create a v3 API key in Brevo (SMTP & API > API Keys) "
                "and set BREVO_API_KEY.")
    if resp.status_code in (400, 403):
        return (f"Brevo refused the message: {detail}. The sender (EMAIL_FROM) must be a verified sender in Brevo "
                "(Senders, Domains & Dedicated IPs > Senders).")
    return f"Brevo answered HTTP {resp.status_code}: {detail}"


def _send_brevo(to: str, subject: str, body: str) -> None:
    """Send through Brevo's HTTPS API. Works on hosts that block SMTP ports (Render's free tier)."""
    sender = _sender_address()
    if not sender:
        raise EmailDeliveryError("EMAIL_FROM is not set. Set it to the sender address you verified in Brevo.")
    payload = {
        "sender": {"name": settings.email_from_name, "email": sender},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body,
    }
    headers = {"api-key": settings.brevo_api_key or "", "accept": "application/json", "content-type": "application/json"}
    last = "unknown error"
    for attempt in (1, 2):
        try:
            resp = httpx.post(settings.brevo_api_url, json=payload, headers=headers, timeout=15)
        except httpx.HTTPError as exc:
            last = f"Could not reach Brevo ({exc.__class__.__name__}). Check the internet connection of the server."
            log.warning("Brevo attempt %d/2 failed: %s", attempt, exc)
            continue
        if resp.status_code in (200, 201, 202):
            return
        last = _describe_brevo_error(resp)
        if resp.status_code in (400, 401, 403):  # retrying cannot help
            break
        log.warning("Brevo attempt %d/2 failed: HTTP %s", attempt, resp.status_code)
    log.error("EMAIL NOT SENT to %s: %s", to, last)
    raise EmailDeliveryError(last)


def webhook_configured() -> bool:
    return bool(settings.email_webhook_url and settings.email_webhook_secret)


def _send_webhook(to: str, subject: str, body: str) -> None:
    """Send through a Google Apps Script web app (it sends from your own Gmail with MailApp)."""
    payload = {
        "secret": settings.email_webhook_secret,
        "to": to,
        "subject": subject,
        "body": body,
        "name": settings.email_from_name,
    }
    last = "unknown error"
    for attempt in (1, 2):
        try:
            # Apps Script answers a POST with a redirect to the result, so redirects must be followed.
            resp = httpx.post(settings.email_webhook_url, json=payload, timeout=30, follow_redirects=True)
        except httpx.HTTPError as exc:
            last = f"Could not reach the email relay ({exc.__class__.__name__}). Check EMAIL_WEBHOOK_URL."
            log.warning("Email relay attempt %d/2 failed: %s", attempt, exc)
            continue
        try:
            data = resp.json()
        except ValueError:
            last = ("The email relay did not answer with JSON. In Google Apps Script, redeploy it as a Web app with "
                    "Execute as 'Me' and Who has access 'Anyone', then copy the new /exec address.")
            break
        if resp.status_code == 200 and isinstance(data, dict) and data.get("ok") is True:
            return
        error = str(data.get("error", "") if isinstance(data, dict) else "")[:200]
        if error == "unauthorized":
            last = "The email relay rejected the secret. EMAIL_WEBHOOK_SECRET must equal SECRET in the Apps Script."
        else:
            last = f"The email relay failed: {error or 'HTTP ' + str(resp.status_code)}"
        break
    log.error("EMAIL NOT SENT to %s: %s", to, last)
    raise EmailDeliveryError(last)


def _password() -> str:
    # Google shows app passwords as "abcd efgh ijkl mnop"; the spaces are not part of it.
    return (settings.smtp_password or "").replace(" ", "")


def describe_smtp_error(exc: Exception) -> str:
    host, port = settings.smtp_host, settings.smtp_port
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return (
            f"The mail server rejected the login for {settings.smtp_user}. For Gmail you must use a 16-character "
            "App Password (Google Account > Security > 2-Step Verification > App passwords), not your normal "
            "password. Paste it into SMTP_PASSWORD (spaces are ignored). If you changed or revoked it, create a new one."
        )
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return f"The server refused the sender address. Set SMTP_FROM_EMAIL to {settings.smtp_user} (or leave it empty)."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "The server refused the recipient address."
    if isinstance(exc, (socket.gaierror,)):
        return f"Could not find the mail server '{host}'. Check SMTP_HOST and your internet connection."
    if isinstance(exc, (TimeoutError, socket.timeout, ConnectionRefusedError, OSError, smtplib.SMTPServerDisconnected,
                        smtplib.SMTPConnectError)):
        return (
            f"Could not connect to {host}:{port} ({exc.__class__.__name__}). Check your internet/firewall; "
            "use port 587 (STARTTLS) or 465 (SSL)."
        )
    if isinstance(exc, ssl.SSLError):
        return f"TLS/SSL error talking to {host}:{port}. Try SMTP_PORT=587, or SMTP_PORT=465 with SMTP_USE_SSL=true."
    return f"{exc.__class__.__name__}: {exc}"


def _build_message(to: str, subject: str, body: str) -> EmailMessage:
    sender = settings.smtp_from_email or settings.smtp_user
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("AAGuardian", sender))
    msg["To"] = to
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain=(sender.split("@")[-1] if sender and "@" in sender else None))
    msg.set_content(body)
    return msg


def _send_once(msg: EmailMessage) -> None:
    host, port = settings.smtp_host, settings.smtp_port
    use_ssl = settings.smtp_use_ssl if settings.smtp_use_ssl is not None else port == 465
    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=15, context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(host, port, timeout=15)
    with server:
        server.ehlo()
        if not use_ssl and server.has_extn("starttls"):
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
        server.login(settings.smtp_user, _password())
        server.send_message(msg)


def send_email(to: str, subject: str, body: str) -> None:
    """Send an email through the configured SMTP server.

    Raises EmailDeliveryError (with a plain-language reason) on failure.
    When SMTP is not configured at all (local dev / tests) the message, including any OTP code,
    is printed to the console instead.
    """
    if webhook_configured():
        _send_webhook(to, subject, body)
        log.info("Email sent to %s (%s) via the Google Apps Script relay", to, subject)
        return

    if resend_configured():
        _send_resend(to, subject, body)
        log.info("Email sent to %s (%s) via Resend", to, subject)
        return

    if brevo_configured():
        _send_brevo(to, subject, body)
        log.info("Email sent to %s (%s) via Brevo", to, subject)
        return

    if not smtp_configured():
        log.info("[DEV FALLBACK - SMTP not configured] Email to %s | subject: %s\n%s", to, subject, body)
        print(f"\n[DEV] Email to {to}: {subject}\n{body}\n", flush=True)
        return

    msg = _build_message(to, subject, body)
    last: Exception | None = None
    for attempt in (1, 2):
        try:
            _send_once(msg)
            log.info("Email sent to %s (%s)", to, subject)
            return
        except smtplib.SMTPAuthenticationError as exc:  # retrying cannot help
            last = exc
            break
        except Exception as exc:  # noqa: BLE001
            last = exc
            log.warning("SMTP attempt %d/2 failed: %s", attempt, exc)
    reason = describe_smtp_error(last) if last else "unknown error"
    log.error("EMAIL NOT SENT to %s: %s", to, reason)
    raise EmailDeliveryError(reason) from last


def send_otp_email(to: str, code: str, purpose: str = "verify") -> None:
    """Send an OTP code by email. purpose: "verify" (registration) or "reset" (password reset)."""
    if purpose == "reset":
        subject = "AAGuardian password reset code"
        body = (
            "Hello,\n\n"
            f"Your AAGuardian password reset code is: {code}\n\n"
            "The code expires in 10 minutes. If you did not request a password reset, "
            "you can ignore this email; your password will not change.\n\n"
            "- The AAGuardian team"
        )
    else:
        subject = "Your AAGuardian verification code"
        body = (
            "Hello,\n\n"
            f"Your AAGuardian verification code is: {code}\n\n"
            "The code expires in 10 minutes.\n\n"
            "- The AAGuardian team"
        )
    send_email(to, subject, body)