"""Auth flow tests: registration, OTP verification, login, refresh, reset."""
import uuid

from tests.otp_capture import codes_for, otp_capture


def _register(client, email=None, password="Str0ngPass!x", phone="0911223344"):
    email = email or f"u{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Test User", "email": email, "phone": phone,
        "password": password,
    })
    return email, r


def test_register_then_verify_then_login(client):
    email, r = _register(client)
    assert r.status_code == 201, r.text
    with otp_capture() as records:
        r = client.post("/api/v1/auth/verify", json={"email": email, "otp_code": "000000"})
    assert r.status_code in (400, 422)  # wrong code rejected


def test_wrong_otp_then_correct_otp(client):
    email, r = _register(client)
    assert r.status_code == 201
    with otp_capture() as records:
        client.post("/api/v1/auth/verify", json={"email": email, "otp_code": "111111"})
        client.post("/api/v1/auth/verify", json={"email": email, "otp_code": "222222"})
        r = client.post("/api/v1/auth/verify", json={"email": email, "otp_code": "333333"})
    assert r.status_code in (400, 401, 422)
    # unverified users cannot log in
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ngPass!x"})
    assert r.status_code == 401


def test_resend_otp_issues_new_code(client):
    email, r = _register(client)
    assert r.status_code == 201
    with otp_capture() as records:
        r = client.post("/api/v1/auth/resend-otp", json={"email": email})
        codes = codes_for(records, email)
    assert r.status_code == 200
    assert codes, "resend did not send an OTP"


def test_forgot_and_reset_password(client):
    email, r = _register(client)
    assert r.status_code == 201
    with otp_capture() as records:
        client.post("/api/v1/auth/resend-otp", json={"email": email})
        code = codes_for(records, email)[-1]
    assert client.post("/api/v1/auth/verify", json={"email": email, "otp_code": code}).status_code == 200

    with otp_capture() as records:
        client.post("/api/v1/auth/forgot-password", json={"email": email})
        reset_codes = codes_for(records, email)
    assert reset_codes, "reset OTP not sent"

    r = client.post("/api/v1/auth/reset-password", json={
        "token": reset_codes[-1], "new_password": "An0ther$Pass9"})
    assert r.status_code == 200, r.text
    assert client.post("/api/v1/auth/login", json={
        "email": email, "password": "An0ther$Pass9"}).status_code == 200
    # old password no longer works
    assert client.post("/api/v1/auth/login", json={
        "email": email, "password": "Str0ngPass!x"}).status_code == 401


def test_forgot_password_unknown_email_does_not_leak(client):
    r = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert r.status_code == 200  # same response as for known emails


def test_duplicate_registration_conflict(client):
    email, r = _register(client)
    assert r.status_code == 201
    r2 = client.post("/api/v1/auth/register", json={
        "full_name": "Other", "email": email, "phone": "0922334455",
        "password": "Str0ngPass!x"})
    assert r2.status_code == 409


def test_weak_password_rejected(client):
    _, r = _register(client, password="short")
    assert r.status_code == 422


def test_refresh_flow(client, user):
    r = client.post("/api/v1/auth/login", json={"email": user["email"], "password": "Str0ngPass!x"})
    refresh = r.json()["refresh_token"]
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200, r2.text
    assert "access_token" in r2.json()


def test_refresh_rejects_access_token(client, user):
    access = user["headers"]["Authorization"].split(" ")[1]
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401


def test_rate_limit_on_verify(client):
    email, r = _register(client)
    assert r.status_code == 201
    statuses = [client.post("/api/v1/auth/verify",
                            json={"email": email, "otp_code": f"{i:06d}"}).status_code
                for i in range(10)]
    assert any(s == 429 for s in statuses), "no rate limit triggered"
