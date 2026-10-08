from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Aiss Road API"
    database_url: str = "sqlite:///./rta_dev.db"
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5
    frontend_url: str = "http://localhost:3000"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_ssl: bool | None = None
    otp_console_fallback: bool = False
    app_env: str = "development"
    storage_backend: str = "disk"
    brevo_api_key: str | None = None
    brevo_api_url: str = "https://api.brevo.com/v3/smtp/email"
    email_from: str | None = None
    email_from_name: str = "AAGuardian"
    resend_api_key: str | None = None
    google_client_id: str = ""
    google_client_secret: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    oauth_redirect_url: str = "http://localhost:3000/auth/oauth-callback"
    profile_image_dir: str = "./uploads/profiles"
    evidence_image_dir: str = "./uploads/evidence"
    max_profile_image_bytes: int = 5 * 1024 * 1024
    max_evidence_image_bytes: int = 8 * 1024 * 1024
    admin_emails: str = ""
    default_admin_email: str = "samrawityisak60@gmail.com"
    default_admin_password: str = "PoliceAdiss2026!"
    default_admin_name: str = "Police Command Admin"
    default_admin_phone: str = "+251911000000"
    seed_demo_data: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalise_database_url(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("postgres://"):
                value = "postgresql+psycopg2://" + value[len("postgres://"):]
            elif value.startswith("postgresql://"):
                value = "postgresql+psycopg2://" + value[len("postgresql://"):]
        return value

    @field_validator("storage_backend")
    @classmethod
    def _check_storage_backend(cls, value):
        value = (value or "disk").strip().lower()
        if value not in {"disk", "db"}:
            raise ValueError('STORAGE_BACKEND must be "disk" or "db"')
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    def production_problems(self) -> list[str]:
        problems: list[str] = []
        if self.jwt_secret_key == "dev-secret-change-me" or len(self.jwt_secret_key) < 32:
            problems.append("JWT_SECRET_KEY must be a random value of at least 32 characters.")
        if self.default_admin_password == "PoliceAdiss2026!":
            problems.append("DEFAULT_ADMIN_PASSWORD is still the public default. Set a strong private password.")
        if self.database_url.startswith("sqlite"):
            problems.append("DATABASE_URL points to SQLite, which loses data on free hosts. Use a PostgreSQL URL (for example from Neon).")
        if self.otp_console_fallback:
            problems.append("OTP_CONSOLE_FALLBACK must be false in production (it prints login codes into the logs).")
        return problems

    @property
    def admin_email_set(self) -> set[str]:
        emails = {
            item.strip().lower()
            for item in self.admin_emails.split(",")
            if item.strip()
        }
        if self.default_admin_email.strip():
            emails.add(self.default_admin_email.strip().lower())
        return emails


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
