from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import UTCDateTime

BroadcastCategory = Literal["announcement", "safety_tip", "road_alert", "warning"]


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    category: str
    report_id: int | None = None
    created_at: UTCDateTime
    is_read: bool = False


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int


class UnreadCountOut(BaseModel):
    unread_count: int


class NotificationCreate(BaseModel):
    """What the police write in the dashboard."""

    title: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=500)
    category: BroadcastCategory = "announcement"

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("message")
    @classmethod
    def clean_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class AdminNotificationOut(BaseModel):
    id: int
    title: str
    message: str
    category: str
    created_at: UTCDateTime
    sent_by: str | None = None
    recipients: int = 0  # users who could see it
    read_count: int = 0  # users who opened it
