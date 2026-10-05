from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hotspot import Hotspot

class HotspotRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, area: str | None = None) -> list[Hotspot]:
        stmt = select(Hotspot).order_by(Hotspot.risk_score.desc())
        if area:
            stmt = stmt.where(Hotspot.area == area)
        return list(self.db.scalars(stmt))
