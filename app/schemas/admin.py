from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import UTCDateTime


ReportStatus = Literal["submitted", "under_review", "resolved", "rejected"]


class AdminReportUpdate(BaseModel):
    status: ReportStatus


class AdminReportOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: str
    user_phone: str
    report_type: str
    description: str | None
    severity: str | None
    injuries_reported: bool
    emergency_required: bool
    latitude: float
    longitude: float
    gps_accuracy_m: float | None
    road_name: str | None
    address: str | None
    occurred_at: UTCDateTime
    created_at: UTCDateTime
    status: str
    evidence_urls: list[str] = Field(default_factory=list)
    is_demo: bool = False


class DemoDataOut(BaseModel):
    present: bool
    reports: int = 0
    events: int = 0


class AdminStatsOut(BaseModel):
    total_reports: int
    submitted: int
    under_review: int
    resolved: int
    rejected: int
    emergency_reports: int
    # Emergency reports still waiting for police action (submitted / under review).
    open_emergencies: int = 0
    injury_reports: int = 0


class AdminMeOut(BaseModel):
    is_admin: bool = True
    email: str
    full_name: str


class AdminEventOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    event_type: str
    activity: str
    phone_use: bool
    latitude: float
    longitude: float
    speed_kmh: float | None
    road_name: str | None
    speed_limit_kmh: float | None
    created_at: UTCDateTime
    is_demo: bool = False
