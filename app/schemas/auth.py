from pydantic import AliasChoices, BaseModel, EmailStr, Field, field_validator

from app.core.security import validate_password_strength

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=9, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        err = validate_password_strength(v)
        if err:
            raise ValueError(err)
        return v

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    # The mobile app sends "reset_token" and the account email; older clients send "token".
    token: str = Field(min_length=6, max_length=6, validation_alias=AliasChoices("token", "reset_token"))
    email: EmailStr | None = None
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        err = validate_password_strength(v)
        if err:
            raise ValueError(err)
        return v

class OAuthUrlResponse(BaseModel):
    authorization_url: str
    state: str

class OAuthCallbackRequest(BaseModel):
    code: str = Field(min_length=1, max_length=2048)
    state: str = Field(min_length=8, max_length=256)

class BiometricEnrollRequest(BaseModel):
    public_key_pem: str = Field(min_length=64, max_length=4096)

class BiometricChallengeRequest(BaseModel):
    email: EmailStr

class BiometricVerifyRequest(BaseModel):
    email: EmailStr
    nonce: str = Field(min_length=8, max_length=128)
    signature: str = Field(min_length=16, max_length=4096)
