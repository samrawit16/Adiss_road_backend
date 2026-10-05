"""Serves photos stored in the database (STORAGE_BACKEND=db) at the same /uploads/... URLs as the disk mode."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.stored_file import StoredFile

router = APIRouter(tags=["uploads"])


@router.get("/uploads/{kind}/{filename}")
def get_upload(kind: str, filename: str, db: Session = Depends(get_db)):
    if kind not in ("evidence", "profiles"):
        raise HTTPException(status_code=404, detail="File not found")
    row = db.get(StoredFile, filename)
    if row is None or row.kind != kind:
        raise HTTPException(status_code=404, detail="File not found")
    # File names are random and never reused, so browsers may cache them for a long time.
    return Response(
        content=row.data,
        media_type=row.content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
