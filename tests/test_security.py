"""Security behaviour: auth required, token tampering, password hashing, secrets."""
import uuid

from fastapi.testclient import TestClient


def test_protected_endpoint_requires_token(client):
    r = client.get("/api/v1/users/me")
    assert r.status_code in (401, 403)


def test_tampered_token_rejected(client, user):
    r = client.get("/api/v1/users/me",
                   headers={"Authorization": "Bearer " + user["headers"]["Authorization"][7:-4] + "xxxx"})
    assert r.status_code == 401


def test_jwt_has_exp(client, user):
    import base64, json
    token = user["headers"]["Authorization"].split(" ")[1]
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    assert "exp" in claims and claims["exp"] > 0


def test_passwords_never_stored_in_plain(client, user):
    import sqlite3
    from app.core.config import settings
    path = settings.database_url.replace("sqlite:///", "")
    conn = sqlite3.connect(path)
    rows = conn.execute("SELECT hashed_password FROM users").fetchall()
    conn.close()
    assert rows
    for (h,) in rows:
        assert "Str0ngPass!x" not in (h or "")
        if h:
            assert h.startswith(("$2", "$argon", "pbkdf2", "scrypt"))


def test_otp_stored_hashed(client):
    email = f"s{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={
        "full_name": "Sam", "email": email, "phone": "0911223344", "password": "Str0ngPass!x"})
    import sqlite3
    from app.core.config import settings
    path = settings.database_url.replace("sqlite:///", "")
    rows = sqlite3.connect(path).execute(
        "SELECT code_hash FROM otp_tokens WHERE email=?", (email,)).fetchall()
    assert rows and all(not r[0].isdigit() for r in rows)


def test_error_responses_do_not_leak_stack(client):
    r = client.post("/api/v1/auth/verify", json={"email": "not-an-email", "otp_code": "bad!"})
    body = r.text.lower()
    assert "traceback" not in body
