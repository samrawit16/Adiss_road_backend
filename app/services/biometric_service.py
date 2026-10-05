"""Biometric device enrollment & verification for AAGuardian.

The Flutter app generates a device keypair (platform keystore / secure enclave),
enrolls the PUBLIC key here, and later signs a server nonce to prove
possession of the device. The private key never leaves the device.
"""
import base64
import hashlib
import secrets

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from sqlalchemy import select

from app.core.errors import AuthenticationError, ValidationError
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

_nonces: dict[str, int] = {}
NONCE_TTL = 300  # seconds


class BiometricService:
    def __init__(self, db):
        self.db = db
        self.users = UserRepository(db)

    # ---- enrollment ------------------------------------------------------
    def enroll(self, user: User, public_key_pem: str) -> dict:
        self._load_public_key(public_key_pem)  # validates the key
        user.biometric_public_key = public_key_pem
        user.biometric_enabled = True
        self.db.commit()
        return {"biometric_enabled": True,
                "message": "Biometric unlock enabled on this device."}

    def disable(self, user: User) -> dict:
        user.biometric_enabled = False
        user.biometric_public_key = None
        self.db.commit()
        return {"biometric_enabled": False,
                "message": "Biometric unlock disabled."}

    # ---- challenge / verify ----------------------------------------------
    def challenge(self, email: str) -> dict:
        user = self.users.get_by_email(email)
        # Do not reveal whether the account exists or has biometrics on.
        if user and user.biometric_enabled:
            nonce = secrets.token_urlsafe(32)
            _nonces[nonce] = _now()
            for n in [k for k, t in _nonces.items() if _now() - t > NONCE_TTL]:
                _nonces.pop(n, None)
            return {"nonce": nonce, "algorithm": "ECDSA_P256_SHA256"}
        raise ValidationError("Biometric sign-in is not available for this account",
                              "BIOMETRIC_UNAVAILABLE")

    def verify(self, email: str, nonce: str, signature_b64: str):
        user = self.users.get_by_email(email)
        if user is None or not user.biometric_enabled:
            raise AuthenticationError("Biometric sign-in not available", "BIOMETRIC_UNAVAILABLE")
        issued = _nonces.pop(nonce, None)
        if issued is None or _now() - issued > NONCE_TTL:
            raise ValidationError("Nonce expired or unknown. Request a new challenge.",
                                  "NONCE_INVALID")
        if _now() - issued > NONCE_TTL:
            raise ValidationError("Nonce expired. Request a new challenge.", "NONCE_INVALID")
        key = self._load_public_key(user.biometric_public_key)
        sig = _b64decode(signature_b64, "signature")
        data = nonce.encode()
        try:
            if isinstance(key, ec.EllipticCurvePublicKey):
                key.verify(sig, data, ec.ECDSA(hashes.SHA256()))
            elif isinstance(key, ed25519.Ed25519PublicKey):
                key.verify(sig, data)
            elif isinstance(key, rsa.RSAPublicKey):
                key.verify(sig, data, padding.PKCS1v15(), hashes.SHA256())
            else:
                raise ValidationError("Unsupported key type", "BIOMETRIC_KEY")
        except InvalidSignature:
            raise AuthenticationError("Signature did not verify", "BIOMETRIC_BAD_SIGNATURE")
        access, _ = create_access_token(user.id)
        refresh, _ = create_refresh_token(user.id)
        return user, access, refresh

    @staticmethod
    def _load_public_key(pem: str | None):
        if not pem:
            raise ValidationError("No biometric key enrolled", "BIOMETRIC_KEY")
        try:
            return serialization.load_pem_public_key(pem.encode())
        except (ValueError, TypeError):
            raise ValidationError("Stored biometric key is invalid", "BIOMETRIC_KEY")


def _now() -> int:
    import time
    return int(time.time())


def _b64decode(value: str, what: str) -> bytes:
    try:
        return base64.b64decode(value)
    except Exception:
        raise ValidationError(f"Invalid {what} encoding", "BIOMETRIC_BAD_SIGNATURE")
