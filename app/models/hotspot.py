from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

class Hotspot(Base):
    __tablename__ = "hotspots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    area: Mapped[str] = mapped_column(String(120), index=True)
    junction_type: Mapped[str] = mapped_column(String(80))
    accidents: Mapped[int] = mapped_column(Integer)
    fatalities: Mapped[int] = mapped_column(Integer)
    injuries: Mapped[int] = mapped_column(Integer)
    risk_score: Mapped[float] = mapped_column(Float)
    peak_hour: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20))
