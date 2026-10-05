"""Check your SMTP settings: sends a real test email and explains any failure.

    python -m scripts.test_email you@example.com
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.email_service import EmailDeliveryError, send_email, smtp_configured


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.test_email recipient@example.com")
        return 2
    to = sys.argv[1]

    print(f"SMTP_HOST      = {settings.smtp_host}")
    print(f"SMTP_PORT      = {settings.smtp_port}")
    print(f"SMTP_USER      = {settings.smtp_user}")
    print(f"SMTP_PASSWORD  = {'(set, ' + str(len((settings.smtp_password or '').replace(' ', ''))) + ' characters)' if settings.smtp_password else '(NOT SET)'}")
    print(f"SMTP_FROM_EMAIL= {settings.smtp_from_email or '(same as SMTP_USER)'}")

    if not smtp_configured():
        print("\nSMTP is not fully configured, so emails are only printed in the server console.")
        print("Set SMTP_HOST, SMTP_USER and SMTP_PASSWORD in .env to send real emails.")
        return 1

    try:
        send_email(to, "AAGuardian test email", "If you can read this, AAGuardian can send email. Codes will arrive the same way.")
    except EmailDeliveryError as exc:
        print(f"\nFAILED: {exc.reason}")
        return 1
    print(f"\nSENT to {to}. Check the inbox (and the spam folder).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
