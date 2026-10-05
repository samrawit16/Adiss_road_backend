"""Notifications: admin broadcasts and per-user messages, with a per-user read marker."""
from bisect import bisect_right

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationRead
from app.models.user import User
from app.services.demo_seed import DEMO_DOMAIN

REPORT_STATUS_MESSAGES = {
    "under_review": (
        "Report #{id} is under review",
        "The police have started reviewing your report. We will tell you when it changes.",
    ),
    "resolved": (
        "Report #{id} resolved",
        "The police marked your report as resolved. Thank you for helping keep Addis Ababa's roads safe.",
    ),
    "rejected": (
        "Report #{id} closed",
        "The police reviewed your report and closed it without further action. "
        "If something important was missed, you can send a new report with more details.",
    ),
}


def _visible_to(user: User):
    """Notifications addressed to the user, plus broadcasts sent after the account existed
    (a new user is not greeted with a pile of old announcements as 'unread')."""
    return or_(
        Notification.user_id == user.id,
        and_(Notification.user_id.is_(None), Notification.created_at >= user.created_at),
    )


def _read_join(user: User):
    return and_(NotificationRead.notification_id == Notification.id, NotificationRead.user_id == user.id)


def list_for_user(db: Session, user: User, limit: int = 50) -> list[tuple[Notification, bool]]:
    rows = db.execute(
        select(Notification, NotificationRead.id)
        .outerjoin(NotificationRead, _read_join(user))
        .where(_visible_to(user))
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    ).all()
    return [(n, read_id is not None) for n, read_id in rows]


def unread_count(db: Session, user: User) -> int:
    return db.scalar(
        select(func.count(Notification.id))
        .select_from(Notification)
        .outerjoin(NotificationRead, _read_join(user))
        .where(_visible_to(user), NotificationRead.id.is_(None))
    ) or 0


def mark_read(db: Session, user: User, notification_id: int) -> bool:
    visible = db.scalar(select(Notification.id).where(Notification.id == notification_id, _visible_to(user)))
    if visible is None:
        return False
    already = db.scalar(select(NotificationRead.id).where(
        NotificationRead.notification_id == notification_id, NotificationRead.user_id == user.id))
    if already is None:
        db.add(NotificationRead(notification_id=notification_id, user_id=user.id))
        db.commit()
    return True


def mark_all_read(db: Session, user: User) -> int:
    ids = db.scalars(
        select(Notification.id)
        .select_from(Notification)
        .outerjoin(NotificationRead, _read_join(user))
        .where(_visible_to(user), NotificationRead.id.is_(None))
    ).all()
    if ids:
        db.add_all([NotificationRead(notification_id=i, user_id=user.id) for i in ids])
        db.commit()
    return len(ids)


def broadcast(db: Session, admin: User, title: str, message: str, category: str) -> Notification:
    note = Notification(title=title, message=message, category=category, user_id=None, created_by=admin.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def notify_user(db: Session, user_id: int, title: str, message: str,
                category: str = "report_update", report_id: int | None = None) -> Notification:
    note = Notification(title=title, message=message, category=category, user_id=user_id, report_id=report_id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def notify_report_status(db: Session, report_id: int, reporter: User, new_status: str) -> None:
    """Tell the citizen when police change the status of their report. Fictional sample users are skipped."""
    template = REPORT_STATUS_MESSAGES.get(new_status)
    if template is None or reporter.email.lower().endswith("@" + DEMO_DOMAIN):
        return
    title, message = template
    notify_user(db, reporter.id, title.format(id=report_id), message, "report_update", report_id)


def _eligible_users():
    return (User.is_active.is_(True), User.is_verified.is_(True), ~User.email.like(f"%@{DEMO_DOMAIN}"))


def admin_history(db: Session, limit: int = 100) -> list[dict]:
    """Broadcasts newest first, with how many people could see each and how many opened it."""
    rows = db.execute(
        select(Notification, User.full_name)
        .outerjoin(User, User.id == Notification.created_by)
        .where(Notification.user_id.is_(None))
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    ).all()
    if not rows:
        return []

    signups = sorted(db.scalars(select(User.created_at).where(*_eligible_users())).all())
    ids = [n.id for n, _ in rows]
    reads = dict(db.execute(
        select(NotificationRead.notification_id, func.count(NotificationRead.id))
        .where(NotificationRead.notification_id.in_(ids))
        .group_by(NotificationRead.notification_id)
    ).all())

    return [
        {
            "id": n.id, "title": n.title, "message": n.message, "category": n.category,
            "created_at": n.created_at, "sent_by": sender,
            "recipients": bisect_right(signups, n.created_at),
            "read_count": reads.get(n.id, 0),
        }
        for n, sender in rows
    ]


def admin_view(db: Session, note: Notification, sender: str | None) -> dict:
    recipients = db.scalar(select(func.count(User.id)).where(*_eligible_users(), User.created_at <= note.created_at)) or 0
    return {
        "id": note.id, "title": note.title, "message": note.message, "category": note.category,
        "created_at": note.created_at, "sent_by": sender, "recipients": recipients, "read_count": 0,
    }


def delete_broadcast(db: Session, notification_id: int) -> bool:
    note = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id.is_(None)))
    if note is None:
        return False
    # SQLite does not enforce ON DELETE CASCADE by default, so remove the read markers explicitly.
    db.execute(delete(NotificationRead).where(NotificationRead.notification_id == notification_id))
    db.delete(note)
    db.commit()
    return True
