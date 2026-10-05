import io
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ValidationError
from app.services import file_store

EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

# Photos kept in the database are shrunk so the free 0.5 GB database holds many of them.
MAX_SIDE = 1600
JPEG_PIXEL_LIMIT = 120_000_000   # decoded at reduced size (draft), so large phone photos are fine
OTHER_PIXEL_LIMIT = 30_000_000


def sniff_image_type(data: bytes) -> str | None:
    """Identify JPEG/PNG/WebP from the file signature.

    Mobile and web clients often upload photos as application/octet-stream, so the
    declared Content-Type cannot be relied on (and should not be trusted anyway).
    """
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _reencode_for_database(data: bytes) -> bytes:
    """Shrink to MAX_SIDE and re-save as JPEG. This also removes EXIF metadata such as GPS tags."""
    try:
        img = Image.open(io.BytesIO(data))
        width, height = img.size
        limit = JPEG_PIXEL_LIMIT if img.format == "JPEG" else OTHER_PIXEL_LIMIT
        if width * height > limit:
            raise ValidationError("The photo dimensions are too large.", "EVIDENCE_TOO_LARGE")
        if img.format == "JPEG":
            img.draft("RGB", (MAX_SIDE * 2, MAX_SIDE * 2))
        img.load()
        img = ImageOps.exif_transpose(img)  # keep the phone's orientation before metadata is dropped
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        out = io.BytesIO()
        img.save(out, "JPEG", quality=82, optimize=True)
        return out.getvalue()
    except ValidationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ValidationError("That file is not a valid image.", "INVALID_EVIDENCE_TYPE") from exc


async def save_evidence_image(file: UploadFile, db: Session | None = None) -> str:
    data = await file.read()
    if not data:
        raise ValidationError("The uploaded image is empty.", "EMPTY_EVIDENCE")
    if len(data) > settings.max_evidence_image_bytes:
        raise ValidationError("Evidence image must be 8 MB or smaller.", "EVIDENCE_TOO_LARGE")

    content_type = sniff_image_type(data)
    if content_type is None:
        raise ValidationError("Only JPEG, PNG, and WebP images are allowed.", "INVALID_EVIDENCE_TYPE")

    if file_store.uses_db():
        if db is None:
            raise RuntimeError("A database session is required when STORAGE_BACKEND=db")
        jpeg = _reencode_for_database(data)
        return file_store.store(db, "evidence", f"report_{uuid4().hex}.jpg", "image/jpeg", jpeg)

    directory = Path(settings.evidence_image_dir)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"report_{uuid4().hex}{EXTENSIONS[content_type]}"
    path = directory / filename
    path.write_bytes(data)
    return str(path)
