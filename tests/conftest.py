import os
import tempfile

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
# Tests always use the dev-console email transport (never real SMTP):
for _v in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
    os.environ[_v] = ""

from app.main import app  # noqa: E402
from app.db.session import get_db, SessionLocal  # noqa: E402


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _override():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def user(client):
    import uuid
    email = f"u{uuid.uuid4().hex[:8]}@example.com"
    from tests.otp_capture import otp_capture, codes_for
    with otp_capture() as records:
        r = client.post("/api/v1/auth/register", json={
            "full_name": "Test User", "email": email, "phone": "0911223344",
            "password": "Str0ngPass!x",
        })
        assert r.status_code == 201, r.text
        codes = codes_for(records, email)
    assert codes, "no OTP email was emitted"
    code = codes[-1]
    r = client.post("/api/v1/auth/verify", json={"email": email, "otp_code": code})
    assert r.status_code == 200, r.text
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ngPass!x"})
    assert r.status_code == 200, r.text
    return {"email": email, "headers": {"Authorization": f"Bearer {r.json()['access_token']}"}}
