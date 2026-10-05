from typing import Optional

from pydantic import BaseModel, ConfigDict


class SeverityPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    Date: Optional[str] = None
    Time: Optional[str] = None
    Day_of_week: Optional[str] = None

    Age_band_of_driver: Optional[str] = None
    Sex_of_driver: Optional[str] = None
    Educational_level: Optional[str] = None
    Vehicle_driver_relation: Optional[str] = None
    Driving_experience: Optional[str] = None
    Type_of_vehicle: Optional[str] = None
    Owner_of_vehicle: Optional[str] = None
    Service_year_of_vehicle: Optional[str] = None
    Defect_of_vehicle: Optional[str] = None

    Area_accident_occured: Optional[str] = None

    Lanes_or_Medians: Optional[str] = None
    Road_allignment: Optional[str] = None
    Types_of_Junction: Optional[str] = None

    Road_surface_type: Optional[str] = None
    Road_surface_conditions: Optional[str] = None
    Light_conditions: Optional[str] = None
    Weather_conditions: Optional[str] = None

    Type_of_collision: Optional[str] = None
    Vehicle_movement: Optional[str] = None
    Casualty_type: Optional[str] = None
    Age_band_of_casualty: Optional[str] = None

    Hour: Optional[int] = None
    Minute: Optional[int] = None
    Time_period: Optional[str] = None


class SeverityPredictionResponse(BaseModel):
    predicted_severity: str
    probabilities: dict[str, float]
    fatal_probability: float
    fatal_threshold: float

    # Location / weather information returned by the backend
    sub_city: Optional[str] = None
    weather: Optional[str] = None
    temperature_c: Optional[float] = None
    precipitation_mm: Optional[float] = None
    cloud_cover_percent: Optional[float] = None
    humidity_percent: Optional[float] = None
    wind_speed_kmh: Optional[float] = None

    # Other prediction context
    light_conditions: Optional[str] = None
    is_peak_hour: bool = False
    peak_period: Optional[str] = None
    peak_message: Optional[str] = None