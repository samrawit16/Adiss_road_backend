from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.hotspot_repository import HotspotRepository
from app.schemas.hotspot import HotspotOut

router = APIRouter(prefix="/hotspots", tags=["hotspots"])

@router.get("", response_model=list[HotspotOut])
def get_hotspots(area: str | None = Query(None), db: Session = Depends(get_db)):
    return HotspotRepository(db).list_all(area)
