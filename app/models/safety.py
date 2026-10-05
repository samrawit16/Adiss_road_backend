
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Authority(Base):
    __tablename__ = "authorities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    authority_type: Mapped[str] = mapped_column(String(40), index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    coverage_area: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AccidentReport(Base):
    __tablename__ = "accident_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    authority_id: Mapped[int | None] = mapped_column(
        ForeignKey("authorities.id"), nullable=True, index=True
    )

    report_type: Mapped[str] = mapped_column(String(40), default="road_accident")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    injuries_reported: Mapped[bool] = mapped_column(Boolean, default=False)
    emergency_required: Mapped[bool] = mapped_column(Boolean, default=False)

    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    road_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(30), default="submitted", index=True)

    # JSON encoded by the API so the backend remains database-agnostic.
    evidence_urls: Mapped[str | None] = mapped_column(Text, nullable=True)


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    activity: Mapped[str] = mapped_column(String(30))
    phone_use: Mapped[bool] = mapped_column(Boolean, default=False)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    road_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    speed_limit_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RoadSpeedLimit(Base):
    __tablename__ = "road_speed_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    road_name: Mapped[str] = mapped_column(String(255), index=True)
    highway_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    speed_limit_kmh: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(80), default="osm")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
