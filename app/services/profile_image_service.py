"""Profile image upload with validation and dedup."""
import io
import os
import secrets
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import ValidationError
from app.services import file_store
from PIL import Image, UnidentifiedImageError

ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_DIMENSION = 1024


async def save_profile_image(user_id: int, file: UploadFile, db=None) -> str:
    if not file:
        raise ValidationError("No image supplied", "NO_FILE")
    # Clients often send application/octet-stream; the real check is the PIL decode below.
    if (file.content_type or "") not in {*ALLOWED_TYPES, "application/octet-stream", ""}:
        raise ValidationError("Only JPEG, PNG or WebP images are allowed", "BAD_TYPE")
    data = await file.read()
    if len(data) > settings.max_profile_image_bytes:
        raise ValidationError("Image is larger than 5 MB", "IMAGE_TOO_LARGE")
    if not data:
        raise ValidationError("Empty file", "IMAGE_EMPTY")
    try:
        img = Image.open(__import__("io").BytesIO(data))
        img.load()
    except UnidentifiedImageError:
        raise ValidationError("That file is not a valid image", "BAD_IMAGE")
    if img.format not in ("JPEG", "PNG", "WEBP"):
        raise ValidationError("Only JPEG, PNG or WebP images are allowed", "BAD_TYPE")
    # strip metadata, downscale huge images
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
    fmt = "PNG" if img.mode == "RGBA" else "JPEG"
    if file_store.uses_db():
        if db is None:
            raise RuntimeError("A database session is required when STORAGE_BACKEND=db")
        buffer = io.BytesIO()
        img.save(buffer, fmt, quality=88)
        name = f"u{user_id}_{uuid4().hex[:10]}.{fmt.lower()}"
        return file_store.store(db, "profiles", name, "image/png" if fmt == "PNG" else "image/jpeg", buffer.getvalue())
    out_dir = settings.profile_image_dir
    os.makedirs(out_dir, exist_ok=True)
    name = f"u{user_id}_{uuid4().hex[:10]}.{fmt.lower()}"
    path = os.path.join(out_dir, name)
    img.save(path, fmt, quality=88)
    return path
