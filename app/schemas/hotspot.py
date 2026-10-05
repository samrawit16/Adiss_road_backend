from pydantic import BaseModel

class HotspotOut(BaseModel):
    id: int
    area: str
    junction_type: str
    accidents: int
    fatalities: int
    injuries: int
    risk_score: float
    peak_hour: int
    severity: str

    class Config:
        from_attributes = True
