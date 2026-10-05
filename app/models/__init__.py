
from app.models.user import User
from app.models.hotspot import Hotspot
from app.models.otp_token import OtpToken
from app.models.safety import Authority, AccidentReport, SafetyEvent, RoadSpeedLimit

__all__ = [
    "User", "Hotspot", "OtpToken",
    "Authority", "AccidentReport", "SafetyEvent", "RoadSpeedLimit",
]
