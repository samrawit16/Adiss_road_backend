import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.admin import require_admin
from app.db.session import get_db
from app.models.safety import AccidentReport, SafetyEvent
from app.models.user import User
from app.schemas.admin import (
    AdminEventOut, AdminMeOut, AdminReportOut, AdminReportUpdate, AdminStatsOut, DemoDataOut,
)
from app.schemas.notification import AdminNotificationOut, NotificationCreate
from app.services import notification_service
from app.services.demo_seed import DEMO_DOMAIN, clear_demo_data

router = APIRouter(prefix="/admin", tags=["admin"])


def _report_dict(report: AccidentReport, user: User) -> dict:
    try:
        evidence = json.loads(report.evidence_urls or "[]")
    except json.JSONDecodeError:
        evidence = []
    return {
        "id": report.id,
        "user_id": report.user_id,
        "user_name": user.full_name,
        "user_email": user.email,
        "user_phone": user.phone,
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
        "evidence_urls": evidence,
        "is_demo": user.email.lower().endswith("@" + DEMO_DOMAIN),
    }


@router.get("/me", response_model=AdminMeOut)
def admin_me(user: User = Depends(require_admin)):
    return {"is_admin": True, "email": user.email, "full_name": user.full_name}


@router.get("/reports", response_model=list[AdminReportOut])
def all_reports(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = (
        select(AccidentReport, User)
        .join(User, User.id == AccidentReport.user_id)
        .order_by(AccidentReport.created_at.desc())
    )
    if status:
        stmt = stmt.where(AccidentReport.status == status)
    rows = db.execute(stmt).all()
    return [_report_dict(report, user) for report, user in rows]


@router.get("/reports/{report_id}", response_model=AdminReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = db.execute(
        select(AccidentReport, User)
        .join(User, User.id == AccidentReport.user_id)
        .where(AccidentReport.id == report_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_dict(row[0], row[1])


@router.patch("/reports/{report_id}", response_model=AdminReportOut)
def update_report(
    report_id: int,
    body: AdminReportUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    report = db.get(AccidentReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    changed = report.status != body.status
    report.status = body.status
    db.commit()
    db.refresh(report)
    user = db.get(User, report.user_id)
    if changed and user is not None:
        # The citizen sees this in the bell of the mobile app.
        notification_service.notify_report_status(db, report.id, user, body.status)
    return _report_dict(report, user)


@router.get("/stats", response_model=AdminStatsOut)
def stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    total = db.scalar(select(func.count(AccidentReport.id))) or 0
    submitted = db.scalar(select(func.count(AccidentReport.id)).where(AccidentReport.status == "submitted")) or 0
    under_review = db.scalar(select(func.count(AccidentReport.id)).where(AccidentReport.status == "under_review")) or 0
    resolved = db.scalar(select(func.count(AccidentReport.id)).where(AccidentReport.status == "resolved")) or 0
    rejected = db.scalar(select(func.count(AccidentReport.id)).where(AccidentReport.status == "rejected")) or 0
    emergency = db.scalar(select(func.count(AccidentReport.id)).where(AccidentReport.emergency_required.is_(True))) or 0
    open_emergencies = db.scalar(
        select(func.count(AccidentReport.id)).where(
            AccidentReport.emergency_required.is_(True),
            AccidentReport.status.in_(["submitted", "under_review"]),
        )
    ) or 0
    injuries = db.scalar(select(func.count(AccidentReport.id)).where(AccidentReport.injuries_reported.is_(True))) or 0
    return {
        "total_reports": total,
        "submitted": submitted,
        "under_review": under_review,
        "resolved": resolved,
        "rejected": rejected,
        "emergency_reports": emergency,
        "open_emergencies": open_emergencies,
        "injury_reports": injuries,
    }


@router.get("/events", response_model=list[AdminEventOut])
def behaviour_events(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Driver/pedestrian behaviour events (overspeed, phone use near traffic, ...)."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.execute(
        select(SafetyEvent, User)
        .join(User, User.id == SafetyEvent.user_id)
        .where(SafetyEvent.created_at >= since)
        .order_by(SafetyEvent.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": e.id, "user_id": e.user_id, "user_name": u.full_name,
            "event_type": e.event_type, "activity": e.activity, "phone_use": e.phone_use,
            "latitude": e.latitude, "longitude": e.longitude, "speed_kmh": e.speed_kmh,
            "road_name": e.road_name, "speed_limit_kmh": e.speed_limit_kmh,
            "created_at": e.created_at,
            "is_demo": u.email.lower().endswith("@" + DEMO_DOMAIN),
        }
        for e, u in rows
    ]


def _demo_counts(db: Session) -> dict:
    like = f"%@{DEMO_DOMAIN}"
    reports = db.scalar(
        select(func.count(AccidentReport.id)).join(User, User.id == AccidentReport.user_id).where(User.email.like(like))
    ) or 0
    events = db.scalar(
        select(func.count(SafetyEvent.id)).join(User, User.id == SafetyEvent.user_id).where(User.email.like(like))
    ) or 0
    has_users = db.scalar(select(func.count(User.id)).where(User.email.like(like))) or 0
    return {"present": bool(has_users), "reports": reports, "events": events}


@router.get("/demo-data", response_model=DemoDataOut)
def demo_data_status(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Is fictional sample data still in the database? (Never touches real reports.)"""
    return _demo_counts(db)


@router.delete("/demo-data", response_model=DemoDataOut)
def remove_demo_data(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Delete only the fictional sample reporters, reports and events."""
    clear_demo_data(db)
    return _demo_counts(db)


@router.post("/notifications", response_model=AdminNotificationOut, status_code=201)
def send_notification(body: NotificationCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Write a message that appears in the bell of every app user."""
    note = notification_service.broadcast(db, admin, body.title, body.message, body.category)
    return notification_service.admin_view(db, note, admin.full_name)


@router.get("/notifications", response_model=list[AdminNotificationOut])
def notification_history(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return notification_service.admin_history(db)


@router.delete("/notifications/{notification_id}", status_code=204)
def retract_notification(notification_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if not notification_service.delete_broadcast(db, notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")

