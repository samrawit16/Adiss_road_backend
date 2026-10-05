"""Where uploaded photos live: on disk (local development) or inside the database (free hosting)."""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.stored_file import StoredFile

DB_PREFIX = "db://"


def uses_db() -> bool:
    return settings.storage_backend == "db"


def store(db: Session, kind: str, filename: str, content_type: str, data: bytes) -> str:
    """Save bytes in the database and return a path-like reference ("db://kind/filename")."""
    db.add(StoredFile(name=filename, kind=kind, content_type=content_type, data=data))
    db.commit()
    return f"{DB_PREFIX}{kind}/{filename}"


def delete_stored(db: Session, path: str | None) -> bool:
    """Delete a database-stored file by its reference. Returns False for ordinary disk paths."""
    if not path or not path.startswith(DB_PREFIX):
        return False
    filename = path.rsplit("/", 1)[-1]
    row = db.get(StoredFile, filename)
    if row is not None:
        db.delete(row)
        db.commit()
    return True
