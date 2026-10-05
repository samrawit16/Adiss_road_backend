from fastapi import APIRouter

from app.schemas.severity import (
    SeverityPredictionRequest,
    SeverityPredictionResponse,
)
from app.services.severity_prediction_service import (
    severity_prediction_service,
)


router = APIRouter(
    prefix="/severity",
    tags=["Accident Severity"],
)


@router.post(
    "/predict",
    response_model=SeverityPredictionResponse,
)
def predict_severity(
    request: SeverityPredictionRequest,
):
    return severity_prediction_service.predict(
        request.model_dump()
    )
