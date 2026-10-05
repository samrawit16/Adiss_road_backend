import hashlib
import hmac
import os
import random
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from app.core.config import settings

PBKDF2_ITERATIONS = 390_000
PREFIX = "pbkdf2_sha256$390000$"

# ---- Password hashing ----
# New passwords use Argon2id. Existing PBKDF2 hashes from older builds remain
# verifiable so upgrading the backend does not lock existing users out.
_PASSWORD_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)
PBKDF2_ITERATIONS = 390_000
PREFIX = "pbkdf2_sha256$390000$"


def hash_password(plain: str) -> str:
    return _PASSWORD_HASHER.hash(plain)


def _verify_legacy_pbkdf2(plain: str, hashed: str) -> bool:
    try:
        _, iters, salt_hex, dk_hex = hashed.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", plain.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, TypeError):
        return False


def verify_password(plain: str, hashed: str) -> bool:
    if hashed.startswith("$argon2id$"):
        try:
            return _PASSWORD_HASHER.verify(hashed, plain)
        except (VerifyMismatchError, VerificationError, ValueError):
            return False
    if hashed.startswith("pbkdf2_sha256$"):
        return _verify_legacy_pbkdf2(plain, hashed)
    return False


def needs_password_rehash(hashed: str) -> bool:
    return not hashed.startswith("$argon2id$")


# ---- Password strength ----

PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")

def validate_password_strength(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Za-z]", password):
        return "Password must contain at least one letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one number"
    return None

# ---- JWT ----

def _create_token(sub: str, type_: str, expires_delta: timedelta) -> tuple[str, str]:
    jti = uuid4().hex
    payload = {"sub": sub, "type": type_, "jti": jti,
               "exp": datetime.now(timezone.utc) + expires_delta}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), jti

def create_access_token(user_id: int) -> tuple[str, str]:
    return _create_token(str(user_id), "access", timedelta(minutes=settings.access_token_expire_minutes))

def create_refresh_token(user_id: int) -> tuple[str, str]:
    return _create_token(str(user_id), "refresh", timedelta(days=settings.refresh_token_expire_days))

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        from app.core.errors import AuthenticationError
        raise AuthenticationError("Invalid or expired token")

# ---- OTP ----

def generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"

def hash_otp(code: str) -> str:
    return hash_password(code)
