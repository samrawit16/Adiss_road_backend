import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
import pytest


def _keypair():
    sk = ec.generate_private_key(ec.SECP256R1())
    pem = sk.public_key().public_bytes(
        encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.PEM,
        format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PublicFormat"]).PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return sk, pem


def _register(client):
    import uuid
    email = f"bio{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Bio User", "email": email, "phone": "0911223344",
        "password": "Str0ngPass!x"})
    assert r.status_code == 201, r.text
    from tests.otp_capture import codes_for, otp_capture
    # fetch code from captured log
    with otp_capture() as rec:
        pass
    return email, client


def test_enroll_requires_auth(client):
    r = client.post("/api/v1/auth/biometric/enroll", json={"public_key_pem": "x"})
    assert r.status_code == 401


def test_challenge_unavailable_for_unknown(client):
    r = client.post("/api/v1/auth/biometric/challenge",
                    json={"email": "nobody@example.com"})
    assert r.status_code in (401, 422)  # avoids user enumeration
    assert r.json()["code"] == "BIOMETRIC_UNAVAILABLE"


def test_full_biometric_flow(client, user):
    email = user["email"]
    headers = user["headers"]
    sk, pem = _keypair()
    r = client.post("/api/v1/auth/biometric/enroll",
                    json={"public_key_pem": pem}, headers=headers)
    assert r.status_code == 200, r.text

    ch = client.post("/api/v1/auth/biometric/challenge", json={"email": email})
    assert ch.status_code == 200
    nonce = ch.json()["nonce"]

    sig = base64.b64encode(sk.sign(nonce.encode(), ec.ECDSA(hashes.SHA256()))).decode()
    r = client.post("/api/v1/auth/biometric/verify",
                    json={"email": email, "nonce": nonce, "signature": sig})
    assert r.status_code == 200, r.text
    tokens = r.json()
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_bad_signature_rejected(client, user):
    email = user["email"]
    headers = user["headers"]
    sk, pem = _keypair()
    client.post("/api/v1/auth/biometric/enroll", json={"public_key_pem": pem}, headers=headers)
    ch = client.post("/api/v1/auth/biometric/challenge", json={"email": email})
    nonce = ch.json()["nonce"]
    sk2, _ = _keypair()
    sig = base64.b64encode(sk2.sign(nonce.encode(), ec.ECDSA(hashes.SHA256()))).decode()
    r = client.post("/api/v1/auth/biometric/verify",
                    json={"email": email, "nonce": nonce, "signature": sig})
    assert r.status_code == 401
    assert r.json()["code"] == "BIOMETRIC_BAD_SIGNATURE"


def test_nonce_single_use(client, user):
    email = user["email"]
    headers = user["headers"]
    sk, pem = _keypair()
    client.post("/api/v1/auth/biometric/enroll", json={"public_key_pem": pem}, headers=headers)
    nonce = client.post("/api/v1/auth/biometric/challenge", json={"email": email}).json()["nonce"]
    sig = base64.b64encode(sk.sign(nonce.encode(), ec.ECDSA(hashes.SHA256()))).decode()
    assert client.post("/api/v1/auth/biometric/verify",
                       json={"email": email, "nonce": nonce, "signature": sig}).status_code == 200
    r = client.post("/api/v1/auth/biometric/verify",
                    json={"email": email, "nonce": nonce, "signature": sig})
    assert r.status_code in (400, 422)  # replay blocked
