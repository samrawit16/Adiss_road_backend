
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.safety import AccidentReport, Authority
from app.models.user import User
from app.schemas.safety import (
    AccidentReportCreate, AccidentReportOut, AuthorityOut,
    SafetyContextRequest, SafetyContextResponse, SafetyEventOut, SafetyEventRequest, SafetyAlertOut,
)
from app.services.safety_service import SafetyService, distance_km
from app.services.evidence_service import save_evidence_image

router = APIRouter(prefix="/safety", tags=["Road Safety"])


@router.post("/context", response_model=SafetyContextResponse)
def safety_context(body: SafetyContextRequest, db: Session = Depends(get_db)):
    """Called by Flutter with current GPS/activity to keep safety information current."""
    return SafetyService(db).context(body)


@router.post("/events", response_model=SafetyEventOut)
def create_safety_event(
    body: SafetyEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event, _ = SafetyService(db).save_event(current_user.id, body)
    return event




@router.get("/alerts", response_model=list[SafetyAlertOut])
def nearby_alerts(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(5, gt=0, le=50),
    db: Session = Depends(get_db),
):
    reports = list(
        db.scalars(
            select(AccidentReport)
            .where(AccidentReport.status.in_(["submitted", "under_review"]))
            .order_by(AccidentReport.created_at.desc())
        )
    )
    result = []
    service = SafetyService(db)
    for report in reports:
        if service.distance_km(latitude, longitude, report.latitude, report.longitude) <= radius_km:
            result.append(service.serialize_alert(report))
    return result

@router.get("/authorities", response_model=list[AuthorityOut])
def nearby_authorities(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    authority_type: str | None = None,
    radius_km: float = Query(50, gt=0, le=500),
    db: Session = Depends(get_db),
):
    rows = list(db.scalars(select(Authority).where(Authority.is_active.is_(True))))
    result = []
    for row in rows:
        d = distance_km(latitude, longitude, row.latitude, row.longitude)
        if d <= radius_km and (authority_type is None or row.authority_type == authority_type):
            result.append((d, row))
    result.sort(key=lambda x: x[0])
    return [
        AuthorityOut(
            id=row.id, name=row.name, authority_type=row.authority_type,
            phone=row.phone, email=row.email, latitude=row.latitude,
            longitude=row.longitude, coverage_area=row.coverage_area,
            distance_km=round(d, 3)
        )
        for d, row in result
    ]




@router.post("/evidence", status_code=201)
async def upload_evidence(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    path = await save_evidence_image(file, db)
    return {"evidence_url": f"/uploads/evidence/{path.rsplit('/', 1)[-1]}"}

@router.post("/accident-reports", response_model=AccidentReportOut, status_code=201)
def submit_accident_report(
    body: AccidentReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        report, authority, _ = SafetyService(db).create_report(current_user.id, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return SafetyService(db).serialize_report(report, authority)


@router.get("/accident-reports", response_model=list[AccidentReportOut])
def my_accident_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = list(
        db.scalars(
            select(AccidentReport)
            .where(AccidentReport.user_id == current_user.id)
            .order_by(AccidentReport.created_at.desc())
        )
    )
    result = []
    for report in reports:
        authority = db.get(Authority, report.authority_id) if report.authority_id else None
        result.append(SafetyService(db).serialize_report(report, authority))
    return result
