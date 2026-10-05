
from datetime import datetime, timezone
import json
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.safety import AccidentReport, Authority, SafetyEvent
from app.services.road_context_service import RoadContextService


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class SafetyService:
    def __init__(self, db: Session):
        self.db = db
        self.road_context = RoadContextService(db)

    def context(self, payload):
        road = self.road_context.lookup(payload.latitude, payload.longitude)
        limit = road.get("speed_limit_kmh")
        speed = payload.speed_kmh
        phone_warning = None
        speed_warning = None
        near_traffic = road.get("highway_type") is not None

        if payload.activity in ("walking", "cycling"):
            if payload.phone_use:
                phone_warning = (
                    "Put the phone away and keep your attention on traffic, "
                    "crossings and other road users."
                )
            
            if limit is not None:
                speed_warning = f"Nearby road speed limit: {limit:g} km/h."
        elif payload.activity == "driving" and speed is not None and limit is not None:
            if speed > limit:
                speed_warning = (
                    f"You are about {speed:.0f} km/h on a road with a "
                    f"{limit:g} km/h limit."
                )

        if phone_warning and speed_warning:
            message = phone_warning + " " + speed_warning
        elif phone_warning:
            message = phone_warning
        elif speed_warning:
            message = speed_warning
        else:
            message = "Stay alert and follow the road signs and local traffic rules."

        return {
            "activity": payload.activity,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "phone_use": payload.phone_use,
            "near_traffic": near_traffic,
            "road_name": road.get("road_name"),
            "highway_type": road.get("highway_type"),
            "speed_limit_kmh": limit,
            "speed_limit_source": road.get("source"),
            "speed_warning": speed_warning,
            "phone_use_warning": phone_warning,
            "safety_message": message,
            "location_accuracy_required": True,
        }

    def save_event(self, user_id: int, payload):
        context = self.context(payload)
        event = SafetyEvent(
            user_id=user_id,
            event_type=payload.event_type,
            activity=payload.activity,
            phone_use=payload.phone_use,
            latitude=payload.latitude,
            longitude=payload.longitude,
            speed_kmh=payload.speed_kmh,
            road_name=context["road_name"],
            speed_limit_kmh=context["speed_limit_kmh"],
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event, context

    def distance_km(self, latitude, longitude, target_latitude, target_longitude):
        return distance_km(latitude, longitude, target_latitude, target_longitude)

    def serialize_alert(self, report):
        try:
            evidence = json.loads(report.evidence_urls or "[]")
        except json.JSONDecodeError:
            evidence = []
        return {
            "id": report.id,
            "report_type": report.report_type,
            "severity": report.severity,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "road_name": report.road_name,
            "occurred_at": report.occurred_at,
            "created_at": report.created_at,
            "status": report.status,
            "evidence_urls": evidence,
        }

    def nearest_authority(self, latitude, longitude, authority_type=None):
        stmt = select(Authority).where(Authority.is_active.is_(True))
        if authority_type:
            stmt = stmt.where(Authority.authority_type == authority_type)
        authorities = list(self.db.scalars(stmt))
        if not authorities:
            return None, None

        authority = min(
            authorities,
            key=lambda a: distance_km(latitude, longitude, a.latitude, a.longitude),
        )
        return authority, distance_km(latitude, longitude, authority.latitude, authority.longitude)

    def create_report(self, user_id: int, payload):
        authority = None
        distance = None
        if payload.authority_id is not None:
            authority = self.db.get(Authority, payload.authority_id)
            if authority is None or not authority.is_active:
                raise ValueError("Selected authority was not found or is inactive.")
        else:
            authority, distance = self.nearest_authority(payload.latitude, payload.longitude)

        # What the reporter typed or confirmed wins; otherwise use the server-side GPS lookup.
        road_name = getattr(payload, "road_name", None)
        if not road_name:
            road_name = self.road_context.lookup(payload.latitude, payload.longitude).get("road_name")

        report = AccidentReport(
            user_id=user_id,
            authority_id=authority.id if authority else None,
            report_type=payload.report_type,
            description=payload.description,
            severity=payload.severity,
            injuries_reported=payload.injuries_reported,
            emergency_required=payload.emergency_required,
            latitude=payload.latitude,
            longitude=payload.longitude,
            gps_accuracy_m=payload.gps_accuracy_m,
            road_name=road_name,
            occurred_at=payload.occurred_at,
            evidence_urls=json.dumps(payload.evidence_urls),
            status="submitted",
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report, authority, distance

    def serialize_report(self, report, authority=None):
        urls = []
        if report.evidence_urls:
            try:
                urls = json.loads(report.evidence_urls)
            except json.JSONDecodeError:
                urls = []
        return {
            "id": report.id,
            "report_type": report.report_type,
            "description": report.description,
            "severity": report.severity,
            "injuries_reported": report.injuries_reported,
            "emergency_required": report.emergency_required,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "gps_accuracy_m": report.gps_accuracy_m,
            "road_name": report.road_name,
            "address": report.address,
            "occurred_at": report.occurred_at,
            "created_at": report.created_at,
            "status": report.status,
            "authority": authority,
            "evidence_urls": urls,
        }
