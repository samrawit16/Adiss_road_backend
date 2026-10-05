"""OAuth2 (Google / Microsoft Entra ID) sign-in for AAGuardian.

Google:  https://developers.google.com/identity/protocols/oauth2
Micro:   https://learn.microsoft.com/entra/identity-platform/v2-protocols-oidc

Config (env or .env):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
  MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET
  OAUTH_REDIRECT_URL  (defaults to the Flutter deep link)
"""
import base64
import json
import time
import secrets
from urllib.parse import urlencode

import httpx
from jose import jwt as jose_jwt
from jose.exceptions import JWTError

from app.core.config import settings
from app.core.errors import AppError, ValidationError

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}

MS_AUTH = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MS_TOKEN = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MS_JWKS = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
MS_ISSUERS = (  
    "https://login.microsoftonline.com/{tid}/v2.0",
    "https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0",
)
MS_ORG = "https://login.microsoftonline.com/organizations/v2.0"

_state_ttl = 600  
_state_store: dict[str, float] = {}

PROVIDERS = ("google", "microsoft")


class OAuthService:
    def __init__(self, provider: str):
        if provider not in PROVIDERS:
            raise ValidationError("Unknown OAuth provider", "OAUTH_PROVIDER")
        self.provider = provider

   
    def _client_id(self) -> str:
        return (settings.google_client_id if self.provider == "google"
                else settings.microsoft_client_id)

    def _client_secret(self) -> str:
        return (settings.google_client_secret if self.provider == "google"
                else settings.microsoft_client_secret)

    def _redirect(self) -> str:
        return settings.oauth_redirect_url

    
    def authorize_url(self) -> str:
        cid = self._client_id()
        if not cid:
            raise AppError(
                f"{self.provider.capitalize()} sign-in is not configured on this server",
                "OAUTH_NOT_CONFIGURED", 503)
        state = secrets.token_urlsafe(24)
        _state_store[state] = time.time()
        # opportunistic cleanup
        cutoff = time.time() - _state_ttl
        for s in [k for k, ts in _state_store.items() if ts < cutoff]:
            _state_store.pop(s, None)

        if self.provider == "google":
            qs = urlencode({
                "client_id": cid, "redirect_uri": self._redirect(),
                "response_type": "code", "scope": "openid email profile",
                "state": state, "access_type": "offline", "prompt": "select_account",
            })
            return f"{GOOGLE_AUTH}?{qs}"
        qs = urlencode({
            "client_id": cid, "redirect_uri": self._redirect(),
            "response_type": "code",
            "scope": "openid email profile offline_access",
            "state": state, "response_mode": "form_post",
        })
        return f"{MS_AUTH}?{qs}"

    
    def exchange_code(self, code: str, state: str | None) -> dict:
        ts = _state_store.pop(state, None) if state else None
        if ts is None:
            raise ValidationError("Invalid or expired OAuth state. Restart sign-in.", "OAUTH_STATE")
        if time.time() - ts > _state_ttl:
            raise ValidationError("OAuth state expired. Restart sign-in.", "OAUTH_STATE")

        cid, csec = self._client_id(), self._client_secret()
        if not cid or not csec:
            raise AppError("OAuth provider is not configured", "OAUTH_NOT_CONFIGURED", 503)
        token_url = GOOGLE_TOKEN if self.provider == "google" else MS_TOKEN
        try:
            r = httpx.post(token_url, data={
                "client_id": cid, "client_secret": csec, "code": code,
                "grant_type": "authorization_code", "redirect_uri": self._redirect(),
            }, timeout=15)
            r.raise_for_status()
            id_token = r.json().get("id_token")
        except (httpx.HTTPError, ValueError):
            raise AppError("Could not verify your sign-in with the provider. Try again.",
                           "OAUTH_EXCHANGE", 502)
        if not id_token:
            raise AppError("Provider did not return an identity token", "OAUTH_NO_ID_TOKEN", 502)
        return self._decode_id_token(id_token)

    def _decode_id_token(self, id_token: str) -> dict:
        unverified = jose_jwt.get_unverified_header(id_token)
        kid = unverified.get("kid")
        jwks_url = GOOGLE_JWKS if self.provider == "google" else MS_JWKS
        try:
            keys = httpx.get(jwks_url, timeout=15).json().get("keys", [])
        except (httpx.HTTPError, ValueError):
            raise AppError("Could not reach the identity provider", "OAUTH_JWKS", 502)
        key = next((k for k in keys if k.get("kid") == kid), None)
        if key is None:
            raise ValidationError("Unknown signing key. Retry sign-in.", "OAUTH_KID")
        try:
            claims = jose_jwt.decode(
                id_token, key,
                algorithms=[unverified.get("alg", "RS256")],
                audience=self._client_id(),
                options={"verify_at_hash": False, "require": ["exp", "iat", "aud"]},
            )
        except JWTError:
            raise ValidationError("Identity token could not be verified", "OAUTH_TOKEN")

        if self.provider == "google":
            if claims.get("iss") not in GOOGLE_ISSUERS:
                raise ValidationError("Unexpected token issuer", "OAUTH_ISSUER")
        else:
            iss = claims.get("iss", "")
            tid = claims.get("tid", "")
            ok = iss == MS_ORG or iss in (
                f"https://login.microsoftonline.com/{tid}/v2.0",) or (
                tid == "9188040d-6c67-4c5b-b112-36a304b66dad")
            if not ok:
                raise ValidationError("Unexpected token issuer", "OAUTH_ISSUER")

        email = (claims.get("email") or "").lower()
        if not email:
            raise ValidationError("Provider account has no email. Use another account.",
                                  "OAUTH_NO_EMAIL")
        return {"email": email, "name": claims.get("name") or email.split("@")[0]}


    @staticmethod
    def _b64pad(part: str) -> bytes:
        return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))

    @staticmethod
    def _state_valid(state: str) -> bool:
        return state in _state_store
