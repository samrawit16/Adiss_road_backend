from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import UTCDateTime

class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str
    is_verified: bool
    created_at: UTCDateTime
    profile_image_url: str | None = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=9, max_length=32)

class ProfileImageOut(BaseModel):
    profile_image_url: str
