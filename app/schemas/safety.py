
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import UTCDateTime


Activity = Literal["walking", "cycling", "driving", "passenger", "unknown"]


class SafetyContextRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    activity: Activity = "walking"
    speed_kmh: float | None = Field(default=None, ge=0, le=300)
    phone_use: bool = False


class SafetyContextResponse(BaseModel):
    activity: Activity
    latitude: float
    longitude: float
    phone_use: bool
    near_traffic: bool = False
    road_name: str | None
    highway_type: str | None
    speed_limit_kmh: float | None
    speed_limit_source: str | None
    speed_warning: str | None
    phone_use_warning: str | None
    safety_message: str
    location_accuracy_required: bool = True


class SafetyEventRequest(SafetyContextRequest):
    event_type: Literal[
        "phone_use_near_traffic",
        "speed_limit_warning",
        "unsafe_speed",
        "safe_trip_check",
    ] = "safe_trip_check"


class SafetyEventOut(BaseModel):
    id: int
    event_type: str
    activity: str
    phone_use: bool
    latitude: float
    longitude: float
    speed_kmh: float | None
    road_name: str | None
    speed_limit_kmh: float | None
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


class AccidentReportCreate(BaseModel):
    report_type: Literal[
        "road_accident", "hazard", "hit_and_run", "vehicle_breakdown", "other"
    ] = "road_accident"
    description: str | None = Field(default=None, max_length=5000)
    severity: Literal["minor", "serious", "critical", "unknown"] = "unknown"
    injuries_reported: bool = False
    emergency_required: bool = False

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    gps_accuracy_m: float | None = Field(default=None, ge=0, le=10000)
    # Road or place name. Filled by the app from GPS, or typed by the reporter when the map
    # has no name for that road. Optional: if empty the server tries its own lookup.
    road_name: str | None = None
    occurred_at: datetime
    authority_id: int | None = None
    evidence_urls: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("road_name")
    @classmethod
    def clean_road_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = " ".join(v.split())  # trim and collapse whitespace/newlines
        return v[:255] or None

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_must_be_reasonable(cls, v: datetime) -> datetime:
        # The column is naive UTC. Convert aware values (the app sends "...Z") instead of
        # letting the database driver reinterpret them in its own session time zone.
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        # A phone with a fast clock must not make the report fail: clamp to "now".
        now = datetime.utcnow()
        if v > now + timedelta(minutes=5):
            v = now
        return v


class SafetyAlertOut(BaseModel):
    id: int
    report_type: str
    severity: str | None
    latitude: float
    longitude: float
    road_name: str | None
    occurred_at: UTCDateTime
    created_at: UTCDateTime
    status: str
    evidence_urls: list[str] = Field(default_factory=list)


class AuthorityOut(BaseModel):
    id: int
    name: str
    authority_type: str
    phone: str | None
    email: str | None
    latitude: float
    longitude: float
    coverage_area: str | None
    distance_km: float | None = None

    model_config = {"from_attributes": True}


class AccidentReportOut(BaseModel):
    id: int
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
    authority: AuthorityOut | None = None
    evidence_urls: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}
