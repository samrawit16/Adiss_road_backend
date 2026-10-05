"""Realistic Addis Ababa sample data for the police dashboard.

Everything created here is tagged by the reporter email domain DEMO_DOMAIN, so it can
be found and removed again without touching real users. Coordinates are approximate
(good enough to cluster on a map around the real junctions), and the reports,
reporters and events are fictional.
"""
import json
import logging
import os
import random
import secrets
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.safety import AccidentReport, Authority, SafetyEvent
from app.models.user import User
from app.services.safety_service import distance_km

logger = logging.getLogger(__name__)

DEMO_DOMAIN = "demo.test"
ADDIS_UTC_OFFSET = timedelta(hours=3)  # Africa/Addis_Ababa, no DST

# (road / junction, lat, lng, weight, posted limit km/h)
LOCATIONS = [
    ("Megenagna Interchange", 9.0203, 38.8020, 12, 40),
    ("Bole Road, near Edna Mall", 8.9967, 38.7862, 11, 50),
    ("Meskel Square", 9.0107, 38.7613, 10, 40),
    ("Mexico Square", 9.0107, 38.7440, 8, 40),
    ("Merkato, Ras Abebe Aregay St", 9.0305, 38.7395, 9, 30),
    ("Piassa, Churchill Avenue", 9.0349, 38.7513, 6, 30),
    ("Kazanchis, Kirkos Sub-city", 9.0166, 38.7690, 7, 40),
    ("CMC Road, Michael Junction", 9.0205, 38.8585, 6, 60),
    ("Gerji, Mebrat Hail", 9.0027, 38.8335, 5, 50),
    ("Ayat Roundabout", 9.0335, 38.8720, 4, 60),
    ("Saris Abo Junction", 8.9530, 38.7480, 5, 60),
    ("Kality Bridge, Ring Road", 8.9310, 38.7610, 4, 80),
    ("Lideta, Tesfa Cinema Rd", 9.0130, 38.7335, 4, 40),
    ("Sarbet, Ring Road", 8.9925, 38.7180, 4, 60),
    ("Jemo Junction", 8.9705, 38.7010, 3, 50),
    ("Shiro Meda, Entoto Road", 9.0610, 38.7555, 3, 40),
    ("Torhailoch, Ring Road", 9.0035, 38.7130, 3, 60),
    ("Gotera Interchange", 8.9840, 38.7595, 4, 60),
]

REPORTER_NAMES = [
    "Abel Tesfaye", "Hanna Girma", "Dawit Alemu", "Meron Bekele", "Yonas Kebede",
    "Selamawit Tadesse", "Biruk Haile", "Tigist Mulugeta", "Kaleab Assefa", "Rediet Negash",
    "Eyob Worku", "Betelhem Demissie", "Nahom Getachew", "Liya Shiferaw", "Samuel Abera",
    "Mahlet Desta", "Henok Tsegaye", "Bethlehem Wolde", "Fikadu Lemma", "Sara Berhanu",
    "Tewodros Mengistu", "Kidist Ayele", "Mikias Zewdu", "Aster Gebre",
]

# Hour-of-day weights (local time): Addis commuter peaks around 07-09 and 16-19.
HOUR_WEIGHTS = [1, 1, 1, 1, 1, 2, 4, 9, 10, 6, 5, 5, 6, 6, 5, 6, 9, 11, 10, 8, 6, 4, 3, 2]

TYPE_WEIGHTS = [("road_accident", 62), ("vehicle_breakdown", 12), ("hazard", 14), ("hit_and_run", 9), ("other", 3)]

SEVERITY_BY_TYPE = {
    "road_accident": [("minor", 45), ("serious", 35), ("critical", 12), ("unknown", 8)],
    "hit_and_run": [("minor", 30), ("serious", 45), ("critical", 20), ("unknown", 5)],
    "hazard": [("minor", 80), ("unknown", 20)],
    "vehicle_breakdown": [("minor", 85), ("unknown", 15)],
    "other": [("minor", 60), ("unknown", 40)],
}

DESCRIPTIONS = {
    "road_accident": [
        "Two cars collided at the junction. Both drivers are out of the vehicles, traffic is backing up.",
        "Minibus taxi hit the rear of a private car while changing lanes. Nobody seems badly hurt.",
        "Motorcycle went down after a car pulled out without looking. Rider is on the ground, conscious.",
        "Pedestrian struck while crossing near the zebra crossing. Ambulance needed.",
        "Isuzu truck lost its brakes on the slope and hit two parked vehicles.",
        "Bajaj overturned taking the corner too fast. Passengers are shaken, one has a cut on the head.",
        "Rear-end collision, one lane blocked. Drivers are arguing about who is at fault.",
        "Car hit the median and spun. Driver is out but the road is partly blocked.",
        "Three-vehicle pile-up in the rain. Road is slippery and cars are not slowing down.",
        "Bus and a small car collided at the roundabout. Several passengers complaining of pain.",
    ],
    "hit_and_run": [
        "A white Vitz hit a pedestrian and drove off toward the ring road. I have part of the plate.",
        "Motorbike clipped a cyclist and sped away. The cyclist has a badly scraped leg.",
        "Car side-swiped a parked taxi and left without stopping. Witnesses saw the direction it went.",
    ],
    "hazard": [
        "Open manhole with no cover in the right lane. Very dangerous at night.",
        "Traffic light not working, cars are crossing from all directions.",
        "Large pothole after the rain, two cars already have damaged tyres.",
        "Construction material left on the road, half the lane is blocked.",
        "Street lights are out along this stretch. Pedestrians cannot be seen after dark.",
        "Flooded road after the rain, drivers are stalling in the water.",
    ],
    "vehicle_breakdown": [
        "Bus broke down in the middle lane with no warning triangle. Traffic is building.",
        "Truck with a flat tyre blocking the slow lane.",
        "Car overheated and stopped on the bridge. Driver is waiting for a tow.",
    ],
    "other": [
        "Drivers ignoring the traffic officer's signals at this junction.",
        "Minibus taxis stopping in the road to load passengers, causing near-misses.",
    ],
}

EVENT_TYPE_WEIGHTS = [("speed_limit_warning", 30), ("unsafe_speed", 20), ("phone_use_near_traffic", 30), ("safe_trip_check", 20)]


def _wchoice(rng: random.Random, pairs):
    total = sum(w for _, w in pairs)
    pick = rng.uniform(0, total)
    acc = 0.0
    for value, weight in pairs:
        acc += weight
        if pick <= acc:
            return value
    return pairs[-1][0]


def _local_to_utc(local: datetime) -> datetime:
    return local - ADDIS_UTC_OFFSET


def _demo_user_ids(db: Session) -> list[int]:
    return list(db.scalars(select(User.id).where(User.email.like(f"%@{DEMO_DOMAIN}"))))


def has_demo_data(db: Session) -> bool:
    return bool(_demo_user_ids(db))


def clear_demo_data(db: Session) -> None:
    ids = _demo_user_ids(db)
    if not ids:
        return
    db.execute(delete(AccidentReport).where(AccidentReport.user_id.in_(ids)))
    db.execute(delete(SafetyEvent).where(SafetyEvent.user_id.in_(ids)))
    db.execute(delete(User).where(User.id.in_(ids)))
    db.commit()


def _existing_evidence_urls() -> list[str]:
    folder = settings.evidence_image_dir
    if not os.path.isdir(folder):
        return []
    return [f"/uploads/evidence/{name}" for name in os.listdir(folder)
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]


def seed_demo_data(db: Session, *, reports: int = 160, events: int = 140, days: int = 210,
                   seed: int = 2026, reset: bool = False) -> dict:
    if reset:
        clear_demo_data(db)
    elif has_demo_data(db):
        return {"skipped": True}

    rng = random.Random(seed)
    now = datetime.utcnow()

    # One shared, unusable password hash: demo reporters cannot log in.
    unusable = hash_password(secrets.token_urlsafe(24))
    users: list[User] = []
    for i, name in enumerate(REPORTER_NAMES):
        first, last = name.lower().split()
        users.append(User(
            full_name=name,
            email=f"{first}.{last}@{DEMO_DOMAIN}",
            phone=f"+2519{rng.randint(10, 99)}{rng.randint(100000, 999999)}",
            hashed_password=unusable,
            is_verified=True,
            is_active=True,
            auth_provider="password",
            created_at=now - timedelta(days=rng.randint(days // 2, days + 60)),
        ))
    db.add_all(users)
    db.commit()
    for u in users:
        db.refresh(u)

    police = list(db.scalars(select(Authority).where(Authority.authority_type == "police",
                                                     Authority.is_active.is_(True))))
    evidence_pool = _existing_evidence_urls()
    loc_pairs = [(loc, loc[3]) for loc in LOCATIONS]

    rows: list[AccidentReport] = []
    for _ in range(reports):
        name, lat, lng, _w, _limit = _wchoice(rng, loc_pairs)
        rtype = _wchoice(rng, TYPE_WEIGHTS)
        severity = _wchoice(rng, SEVERITY_BY_TYPE[rtype])

        # Slightly more reports recently than long ago.
        age_days = int(days * (rng.random() ** 1.15))
        hour = rng.choices(range(24), weights=HOUR_WEIGHTS)[0]
        local = (now + ADDIS_UTC_OFFSET).replace(hour=hour, minute=rng.randint(0, 59), second=0, microsecond=0) \
            - timedelta(days=age_days)
        occurred = _local_to_utc(local)
        if occurred > now:
            occurred -= timedelta(days=1)
        created = min(now, occurred + timedelta(minutes=rng.choice([3, 5, 8, 12, 20, 35, 60, 180])))

        if severity == "critical":
            injuries, emergency = True, rng.random() < 0.9
        elif severity == "serious":
            injuries, emergency = rng.random() < 0.8, rng.random() < 0.4
        elif rtype in ("road_accident", "hit_and_run"):
            injuries, emergency = rng.random() < 0.12, False
        else:
            injuries, emergency = False, False

        # A police queue is worked oldest-first: fresh reports are still waiting, and
        # nothing stays untouched for months.
        age_h = (now - created).total_seconds() / 3600
        if age_h < 24:
            status = _wchoice(rng, [("submitted", 75), ("under_review", 25)])
        elif age_h < 24 * 4:
            status = _wchoice(rng, [("submitted", 40), ("under_review", 45), ("resolved", 10), ("rejected", 5)])
        elif age_h < 24 * 14:
            status = _wchoice(rng, [("submitted", 12), ("under_review", 38), ("resolved", 40), ("rejected", 10)])
        elif age_h < 24 * 60:
            status = _wchoice(rng, [("under_review", 12), ("resolved", 72), ("rejected", 16)])
        else:
            status = _wchoice(rng, [("under_review", 3), ("resolved", 80), ("rejected", 17)])
        # Serious emergencies get picked up first.
        if emergency and status == "submitted" and age_h > 2:
            status = "under_review"

        description = rng.choice(DESCRIPTIONS[rtype]) if rng.random() > 0.08 else None
        authority = min(police, key=lambda a: distance_km(lat, lng, a.latitude, a.longitude)) if police else None
        evidence = [rng.choice(evidence_pool)] if evidence_pool and rtype == "road_accident" and rng.random() < 0.1 else []

        rows.append(AccidentReport(
            user_id=rng.choice(users).id,
            authority_id=authority.id if authority else None,
            report_type=rtype,
            description=description,
            severity=severity,
            injuries_reported=injuries,
            emergency_required=emergency,
            # ~15-150 m of scatter so dots cluster around the junction, not on one pixel
            latitude=round(lat + rng.gauss(0, 0.0007), 6),
            longitude=round(lng + rng.gauss(0, 0.0007), 6),
            gps_accuracy_m=round(rng.uniform(4, 35), 1),
            road_name=name,
            address=None,
            occurred_at=occurred,
            created_at=created,
            status=status,
            evidence_urls=json.dumps(evidence),
        ))
    db.add_all(rows)

    evs: list[SafetyEvent] = []
    for _ in range(events):
        name, lat, lng, _w, limit = _wchoice(rng, loc_pairs)
        etype = _wchoice(rng, EVENT_TYPE_WEIGHTS)
        created = now - timedelta(days=rng.random() * 30, minutes=rng.randint(0, 1439))
        if etype == "phone_use_near_traffic":
            activity, phone, speed = rng.choice(["walking", "walking", "cycling"]), True, None
        else:
            activity, phone = "driving", rng.random() < 0.12
            if etype == "unsafe_speed":
                speed = float(limit + rng.randint(15, 40))
            elif etype == "speed_limit_warning":
                speed = float(limit + rng.randint(1, 15))
            else:
                speed = float(max(10, limit - rng.randint(0, 20)))
        evs.append(SafetyEvent(
            user_id=rng.choice(users).id,
            event_type=etype,
            activity=activity,
            phone_use=phone,
            latitude=round(lat + rng.gauss(0, 0.0005), 6),
            longitude=round(lng + rng.gauss(0, 0.0005), 6),
            speed_kmh=speed,
            road_name=name,
            speed_limit_kmh=float(limit),
            created_at=created,
        ))
    db.add_all(evs)
    db.commit()
    logger.info("Seeded %d demo reports and %d demo events", len(rows), len(evs))
    return {"skipped": False, "users": len(users), "reports": len(rows), "events": len(evs)}
