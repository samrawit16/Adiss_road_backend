from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (BiometricChallengeRequest, BiometricEnrollRequest,
                              BiometricVerifyRequest, TokenResponse)
from app.services.biometric_service import BiometricService

router = APIRouter(prefix="/auth/biometric", tags=["biometric"])


@router.post("/enroll")
def enroll(body: BiometricEnrollRequest, current: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    return BiometricService(db).enroll(current, body.public_key_pem)


@router.delete("/enroll")
def disable(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return BiometricService(db).disable(current)


@router.post("/challenge")
def challenge(body: BiometricChallengeRequest, db: Session = Depends(get_db)):
    return BiometricService(db).challenge(body.email)


@router.post("/verify", response_model=TokenResponse)
def verify(body: BiometricVerifyRequest, db: Session = Depends(get_db)):
    user, access, refresh = BiometricService(db).verify(body.email, body.nonce, body.signature)
    return TokenResponse(access_token=access, refresh_token=refresh)
