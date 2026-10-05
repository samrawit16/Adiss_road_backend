from app.schemas.auth import (RegisterRequest, VerifyOtpRequest, LoginRequest,
                              TokenResponse, ForgotPasswordRequest, ResetPasswordRequest)
from app.schemas.user import UserOut
from app.schemas.hotspot import HotspotOut
__all__ = ["RegisterRequest", "VerifyOtpRequest", "LoginRequest", "TokenResponse",
           "ForgotPasswordRequest", "ResetPasswordRequest", "UserOut", "HotspotOut"]
