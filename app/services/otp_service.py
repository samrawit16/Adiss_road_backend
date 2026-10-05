from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import EmailDeliveryFailed, ValidationError
from app.core.security import generate_otp, hash_otp
from app.models.otp_token import OtpToken
from app.services.email_service import EmailDeliveryError, send_otp_email

def issue_otp(db: Session, email: str, purpose: str) -> None:
    """Create a fresh code, save it, then email it.

    The code is saved BEFORE sending so it is already valid when the email arrives. If the email
    cannot be sent the code is removed again and a clear 503 error is returned to the app, unless
    OTP_CONSOLE_FALLBACK=true (local development), where the code is printed in the server console.
    """
    code = generate_otp()
    db.execute(delete(OtpToken).where(OtpToken.email == email, OtpToken.purpose == purpose))
    db.add(OtpToken(
        email=email, purpose=purpose, code_hash=hash_otp(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes),
    ))
    db.commit()

    try:
        send_otp_email(email, code, purpose)
    except EmailDeliveryError as exc:
        if settings.otp_console_fallback:
            print(
                "\n" + "=" * 70 + f"\n[DEV] EMAIL FAILED: {exc.reason}\n"
                f"[DEV] {purpose} code for {email}: {code}\n" + "=" * 70 + "\n",
                flush=True,
            )
            return
        db.execute(delete(OtpToken).where(OtpToken.email == email, OtpToken.purpose == purpose))
        db.commit()
        raise EmailDeliveryFailed() from exc

def verify_otp(db: Session, email: str, code: str, purpose: str) -> None:
    tok = db.scalar(select(OtpToken).where(OtpToken.email == email, OtpToken.purpose == purpose)
                    .order_by(OtpToken.created_at.desc()))
    if tok is None or tok.used:
        raise ValidationError("No active code found. Request a new one.", "OTP_NOT_FOUND")
    if datetime.now(timezone.utc) > tok.expires_at.replace(tzinfo=timezone.utc):
        raise ValidationError("Code expired. Request a new one.", "OTP_EXPIRED")
    if tok.attempts >= settings.otp_max_attempts:
        raise ValidationError("Too many attempts. Request a new code.", "OTP_LOCKED")
    if not verify_otp_code(code, tok.code_hash):
        tok.attempts += 1
        db.commit()
        raise ValidationError("Invalid code", "OTP_INVALID")
    tok.used = True
    db.commit()

def verify_otp_code(code: str, code_hash: str) -> bool:
    from app.core.security import verify_password
    return verify_password(code, code_hash)