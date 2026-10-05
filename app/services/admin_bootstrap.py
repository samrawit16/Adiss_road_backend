"""Creates the default police-dashboard admin account on startup."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


def ensure_default_admin(db: Session, *, reset_password: bool = False) -> User | None:
    email = settings.default_admin_email.strip().lower()
    password = settings.default_admin_password
    if not email or not password:
        return None

    user = db.scalar(select(User).where(User.email == email))

    if user is None:
        user = User(
            full_name=settings.default_admin_name,
            email=email,
            phone=settings.default_admin_phone,
            hashed_password=hash_password(password),
            is_verified=True,
            is_active=True,
            auth_provider="password",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created default admin account %s", email)
        return user

    changed = False
    # An account for this email that never completed OTP verification was not proven
    # to belong to the admin (anyone could have pre-registered it), so its password is
    # replaced. A verified account keeps its own password unless reset_password=True.
    if reset_password or not user.is_verified:
        user.hashed_password = hash_password(password)
        changed = True
    if not user.is_verified:
        user.is_verified = True
        changed = True
    if not user.is_active:
        user.is_active = True
        changed = True
    if changed:
        db.commit()
        logger.info("Updated default admin account %s", email)
    return user
