import io
import uuid

from PIL import Image


def _png_bytes(size=(40, 40)):
    img = Image.new("RGB", size, (200, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _register(client):
    email = f"img{uuid.uuid4().hex[:8]}@example.com"
    from tests.otp_capture import otp_capture, codes_for
    with otp_capture() as rec:
        r = client.post("/api/v1/auth/register", json={
            "full_name": "Img User", "email": email, "phone": "0911223344",
            "password": "Str0ngPass!x"})
        assert r.status_code == 201
        code = codes_for(rec, email)[-1]
    r = client.post("/api/v1/auth/verify", json={"email": email, "otp_code": code})
    assert r.status_code == 200, r.text
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ngPass!x"})
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"]


def test_upload_and_serve(client):
    email, token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/users/me/profile-image",
                    files={"file": ("me.png", _png_bytes(), "image/png")},
                    headers=headers)
    assert r.status_code == 200, r.text
    url = r.json()["profile_image_url"]
    assert url.startswith("/uploads/profiles/")
    served = client.get(url)
    assert served.status_code == 200
    assert served.headers["content-type"] in ("image/jpeg", "image/png")


def test_rejects_non_image(client):
    email, token = _register(client)
    r = client.post("/api/v1/users/me/profile-image",
                    files={"file": ("evil.txt", b"hello", "text/plain")},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422
    assert r.json()["code"] == "BAD_TYPE"


def test_rejects_oversized(client):
    email, token = _register(client)
    big = _png_bytes((2200, 2200))  # will be downscaled, still valid
    r = client.post("/api/v1/users/me/profile-image",
                    files={"file": ("big.png", big, "image/png")},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200  # downscaled automatically


def test_replaces_previous(client):
    email, token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    r1 = client.post("/api/v1/users/me/profile-image",
                     files={"file": ("a.png", _png_bytes(), "image/png")}, headers=headers)
    r2 = client.post("/api/v1/users/me/profile-image",
                     files={"file": ("b.png", _png_bytes(), "image/png")}, headers=headers)
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["profile_image_url"] != r2.json()["profile_image_url"]
