from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationListOut, UnreadCountOut
from app.services import notification_service as service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListOut)
def my_notifications(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = service.list_for_user(db, user, limit)
    return {
        "items": [
            {"id": n.id, "title": n.title, "message": n.message, "category": n.category,
             "report_id": n.report_id, "created_at": n.created_at, "is_read": read}
            for n, read in rows
        ],
        "unread_count": service.unread_count(db, user),
    }


@router.get("/unread-count", response_model=UnreadCountOut)
def my_unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"unread_count": service.unread_count(db, user)}


@router.post("/read-all", response_model=UnreadCountOut)
def read_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.mark_all_read(db, user)
    return {"unread_count": service.unread_count(db, user)}


@router.post("/{notification_id}/read", response_model=UnreadCountOut)
def read_one(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not service.mark_read(db, user, notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"unread_count": service.unread_count(db, user)}
