import base64
import json
import time

import pytest

from app.services import oauth_service as osvc
from app.services.oauth_service import OAuthService, _state_store

def _register_state(monkeypatch=None):
    if monkeypatch is not None:
        monkeypatch.setattr("app.core.settings.Settings.google_client_id", "test-id", raising=False)
        monkeypatch.setattr("app.core.settings.Settings.google_client_secret", "test-secret", raising=False)
    svc = OAuthService("google")
    if not svc._client_id():
        return None
    svc.authorize_url()
    return max(_state_store, key=_state_store.get)


def test_unknown_provider_rejected(client):
    r = client.get("/api/v1/auth/oauth/github/url")
    assert r.status_code == 422
    assert r.json()["code"] == "OAUTH_PROVIDER"


def test_authorize_url_google_and_microsoft(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.google_client_id", "g-id", raising=False)
    monkeypatch.setattr("app.core.config.settings.microsoft_client_id", "m-id", raising=False)
    r = client.get("/api/v1/auth/oauth/google/url")
    assert r.status_code == 200
    assert r.json()["authorization_url"].startswith("https://accounts.google.com")
    r = client.get("/api/v1/auth/oauth/microsoft/url")
    assert r.json()["authorization_url"].startswith("https://login.microsoftonline.com")


def test_not_configured_returns_503(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.google_client_id", "", raising=False)
    r = client.get("/api/v1/auth/oauth/google/url")
    assert r.status_code == 503
    assert r.json()["code"] == "OAUTH_NOT_CONFIGURED"


def test_callback_rejects_bad_state(client):
    r = client.post("/api/v1/auth/oauth/google/callback",
                    json={"code": "abc", "state": "not-a-real-state"})
    assert r.status_code == 422
    assert r.json()["code"] == "OAUTH_STATE"


def test_expired_state_rejected(client):
    state = _register_state()
    _state_store[state] = time.time() - osvc._state_ttl - 1
    r = client.post("/api/v1/auth/oauth/google/callback",
                    json={"code": "abc", "state": state})
    assert r.status_code == 422


def test_google_signin_creates_verified_user(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.google_client_id", "g-id", raising=False)
    monkeypatch.setattr("app.core.config.settings.google_client_secret", "g-sec", raising=False)
    state = _register_state()

    id_claims = {"email": "new.user@gmail.com", "name": "New User",
                 "aud": "g-id", "iss": "https://accounts.google.com",
                 "exp": int(time.time()) + 600, "iat": int(time.time())}
    fake_id_token = "x." + base64.urlsafe_b64encode(json.dumps(id_claims).encode()).decode().rstrip("=") + ".y"

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"id_token": fake_id_token}

    monkeypatch.setattr("app.services.oauth_service.httpx.post", lambda *a, **k: FakeResp())
    monkeypatch.setattr("app.services.oauth_service.httpx.get", lambda *a, **k: type("R", (), {"json": lambda s: {"keys": []}})())

    # monkeypatch _decode_id_token to skip real crypto; assert the flow end-to-end
    monkeypatch.setattr(OAuthService, "_decode_id_token", lambda self, t: {"email": id_claims["email"], "name": id_claims["name"]})

    r = client.post("/api/v1/auth/oauth/google/callback",
                    json={"code": "good", "state": state})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"] and body["refresh_token"]

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new.user@gmail.com"
    assert me.json()["is_verified"] is True
