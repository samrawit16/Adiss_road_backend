from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class StoredFile(Base):
    """A photo kept inside the database (STORAGE_BACKEND=db) so it survives free-host restarts."""

    __tablename__ = "stored_files"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # "evidence" | "profiles"
    content_type: Mapped[str] = mapped_column(String(50))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
