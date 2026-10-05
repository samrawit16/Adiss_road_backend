from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, ConflictError, ValidationError
from app.core.security import (create_access_token, create_refresh_token, hash_password,
                               verify_password, needs_password_rehash)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.otp_service import issue_otp, verify_otp

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, full_name: str, email: str, phone: str, password: str) -> User:
        if self.users.get_by_email(email):
            raise ConflictError("This email is already registered. Try logging in instead.", "EMAIL_EXISTS")
        user = self.users.create(full_name, email, phone, hash_password(password))
        try:
            issue_otp(self.db, user.email, "verify")
        except Exception as exc:
            # Do not leave an unverified account behind when email delivery fails.
            self.db.delete(user)
            self.db.commit()
            raise ValidationError(
                "We could not send the verification email. Please check the server email configuration and try again.",
                "EMAIL_DELIVERY_FAILED",
            ) from exc
        return user

    def verify_registration(self, email: str, code: str) -> None:
        # Normalize the same way registration/login do.
        email = email.strip().lower()
        code = code.strip()
        verify_otp(self.db, email, code, "verify")
        user = self.users.get_by_email(email)
        if user is None:
            raise ValidationError("No account found for this email", "USER_NOT_FOUND")
        user.is_verified = True
        self.db.commit()

    def resend_otp(self, email: str) -> None:
        email = email.strip().lower()
        user = self.users.get_by_email(email)
        if user is None:
            raise ValidationError("No account found for this email", "USER_NOT_FOUND")
        if user.is_verified:
            raise ValidationError("This account is already verified. Try logging in.", "ALREADY_VERIFIED")
        issue_otp(self.db, email, "verify")

    def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError()
        if needs_password_rehash(user.hashed_password):
            user.hashed_password = hash_password(password)
            self.db.commit()
        if not user.is_verified:
            issue_otp(self.db, user.email, "verify")
            raise AuthenticationError("Account not verified. A new code was sent to your email.", "NOT_VERIFIED")
        if not user.is_active:
            raise AuthenticationError("Account disabled", "ACCOUNT_DISABLED")
        access, _ = create_access_token(user.id)
        refresh, _ = create_refresh_token(user.id)
        return user, access, refresh

    def forgot_password(self, email: str) -> None:
        email = email.strip().lower()
        user = self.users.get_by_email(email)
        if user is None:
            # The app is told "if the account exists, a code was sent" so addresses cannot be
            # probed, but the developer console says what really happened.
            import logging
            logging.getLogger("otp").info("Password reset requested for %s: no account with this email, nothing sent.", email)
            return
        issue_otp(self.db, email, "reset")

    def reset_password(self, token: str, new_password: str, email: str | None = None) -> None:
        # With an email, only that account's code can match (a 6-digit code could otherwise
        # collide with somebody else's). Without one, fall back to searching active codes.
        from app.models.otp_token import OtpToken
        query = select(OtpToken).where(
            OtpToken.purpose == "reset", OtpToken.used == False,  # noqa: E712
        )
        if email:
            query = query.where(OtpToken.email == email.strip().lower())
        rows = self.db.scalars(query).all()
        target = None
        now = datetime.now(timezone.utc)
        for t in rows:
            if now > t.expires_at.replace(tzinfo=timezone.utc):
                continue
            if verify_password(token, t.code_hash):
                target = t
                break
        if target is None:
            raise ValidationError("Invalid or expired code. Request a new one.", "OTP_INVALID")
        target.used = True
        email = target.email
        self.db.commit()
        user = self.users.get_by_email(email)
        if user is None:
            raise ValidationError("No account found for this email", "USER_NOT_FOUND")
        user.hashed_password = hash_password(new_password)
        self.db.commit()

    def login_refresh(self, user_id: int) -> tuple[User, str, str]:
        user = self.db.get(User, user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User not found")
        access, _ = create_access_token(user.id)
        refresh, _ = create_refresh_token(user.id)
        return user, access, refresh
