from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(32))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auth_provider: Mapped[str] = mapped_column(String(32), default="password")
    profile_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    biometric_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    biometric_public_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


    @property
    def profile_image_url(self) -> str | None:
        if not self.profile_image_path:
            return None
        return f"/uploads/profiles/{self.profile_image_path.rsplit('/', 1)[-1]}"
