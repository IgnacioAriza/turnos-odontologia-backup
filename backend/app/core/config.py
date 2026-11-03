from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/turnos_odontologia",
        description="PostgreSQL async connection URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    jwt_secret: str = Field(
        default="dev-secret-change-in-production", description="JWT signing secret"
    )
    jwt_expires_min: int = Field(default=30, description="JWT access token expiry in minutes")
    tz_clinica: str = Field(
        default="America/Argentina/Buenos_Aires", description="Clinic timezone for business logic"
    )
    mp_access_token: str = Field(default="", description="Mercado Pago access token")
    mp_webhook_secret: str = Field(
        default="", description="Mercado Pago webhook secret for signature verification"
    )
    mp_ttl_min: int = Field(default=30, description="Mercado Pago preference TTL in minutes")
    twilio_sid: str = Field(default="", description="Twilio Account SID")
    twilio_token: str = Field(default="", description="Twilio Auth Token")
    twilio_wa_from: str = Field(
        default="", description="Twilio WhatsApp sender number (whatsapp:+14155238886)"
    )
    gcal_calendar_id: str = Field(default="", description="Google Calendar ID for backup sync")
    smtp_url: str = Field(
        default="", description="SMTP URL for email fallback (smtp://user:pass@host:port)"
    )
    frontend_url: str = Field(
        default="http://localhost:5173", description="Frontend URL for CORS and links"
    )
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    @property
    def JWT_SECRET(self) -> str:  # noqa: N802
        return self.jwt_secret

    @property
    def JWT_EXPIRES_MIN(self) -> int:  # noqa: N802
        return self.jwt_expires_min

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return self.database_url

    @property
    def REDIS_URL(self) -> str:  # noqa: N802
        return self.redis_url


settings = Settings()
