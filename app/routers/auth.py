import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.schemas.auth import (ForgotPasswordRequest, LoginRequest, RegisterRequest,
                              ResetPasswordRequest, TokenResponse, VerifyOtpRequest)
from app.schemas.user import UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_VERIFY_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)
_RESET_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)
_VERIFY_LIMIT = 5
_VERIFY_WINDOW = 600  # seconds

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    user = AuthService(db).register(body.full_name, body.email, body.phone, body.password)
    return user

@router.post("/verify", status_code=status.HTTP_200_OK)
def verify(body: VerifyOtpRequest, db: Session = Depends(get_db)):
    now = time.monotonic()
    attempts = _VERIFY_ATTEMPTS[body.email.lower()]
    while attempts and now - attempts[0] > _VERIFY_WINDOW:
        attempts.popleft()
    if len(attempts) >= _VERIFY_LIMIT:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 10 minutes.")
    attempts.append(now)

    AuthService(db).verify_registration(body.email, body.otp_code)
    return {"message": "Email verified. You can now log in."}

@router.post("/resend-otp", status_code=status.HTTP_200_OK)
def resend(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    AuthService(db).resend_otp(body.email)
    return {"message": "A new code was sent."}

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user, access, refresh = AuthService(db).login(body.email, body.password)
    return TokenResponse(access_token=access, refresh_token=refresh)

@router.post("/refresh", response_model=TokenResponse)
def refresh(body: dict, db: Session = Depends(get_db)):
    from app.core.security import decode_token
    payload = decode_token(body.get("refresh_token", ""))
    if payload.get("type") != "refresh":
        raise AppError("Invalid refresh token", "INVALID_TOKEN", 401)
    user, access, refresh = AuthService(db).login_refresh(int(payload["sub"]))
    return TokenResponse(access_token=access, refresh_token=refresh)

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    AuthService(db).forgot_password(body.email)
    return {"message": "If that email is registered, a reset code has been sent."}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    key = (body.email or "any").lower()
    now = time.monotonic()
    attempts = _RESET_ATTEMPTS[key]
    while attempts and now - attempts[0] > _VERIFY_WINDOW:
        attempts.popleft()
    if len(attempts) >= _VERIFY_LIMIT:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 10 minutes.")
    attempts.append(now)

    AuthService(db).reset_password(body.token, body.new_password, body.email)
    return {"message": "Password updated. Log in with your new password."}


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(body: dict | None = None):
    """Tokens are stateless JWTs, so there is nothing to revoke server-side; the app
    discards them. The endpoint exists so clients can call it without a 404."""
    return {"message": "Logged out."}
