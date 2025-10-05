"""Central application configuration powered by Pydantic settings."""

from __future__ import annotations

from typing import List

from dotenv import load_dotenv
from pydantic import BaseSettings, Field, root_validator, validator

load_dotenv()


class SMTPSettings(BaseSettings):
    """Outgoing mail server configuration."""

    host: str | None = Field(default=None, env="SMTP_HOST")
    port: int = Field(default=587, env="SMTP_PORT")
    username: str | None = Field(default=None, env="SMTP_USER")
    password: str | None = Field(default=None, env="SMTP_PASS")
    from_address: str = Field(default="noreply@repairshop.com", env="EMAIL_FROM")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        allow_mutation = True

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.username and self.password)


class QuickBooksSettings(BaseSettings):
    """QuickBooks integration credentials."""

    client_id: str | None = Field(default=None, env="QUICKBOOKS_CLIENT_ID")
    client_secret: str | None = Field(default=None, env="QUICKBOOKS_CLIENT_SECRET")
    redirect_uri: str | None = Field(default=None, env="QUICKBOOKS_REDIRECT_URI")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        allow_mutation = True


class GoogleOAuthSettings(BaseSettings):
    """Google OAuth client configuration."""

    client_id: str | None = Field(default=None, env="GOOGLE_CLIENT_ID")
    client_secret: str | None = Field(default=None, env="GOOGLE_CLIENT_SECRET")
    redirect_uri: str | None = Field(default=None, env="GOOGLE_REDIRECT_URI")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        allow_mutation = True


class ThresholdSettings(BaseSettings):
    """Aggregated alert thresholds used across the application."""

    invoice_margin_alert_percent: float = Field(25.0, env="INVOICE_MARGIN_ALERT_THRESHOLD")
    substitution_reorder: int = Field(3, env="SUBSTITUTION_REORDER_THRESHOLD")
    unit_cost_multiplier: float = Field(1.15, env="UNIT_COST_ALERT_THRESHOLD")
    max_bay_jobs_per_day: int = Field(12, env="MAX_BAY_JOBS_PER_DAY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        allow_mutation = True


class TwilioSettings(BaseSettings):
    """Twilio credentials for SMS notifications."""

    account_sid: str | None = Field(default=None, env="TWILIO_ACCOUNT_SID")
    auth_token: str | None = Field(default=None, env="TWILIO_AUTH_TOKEN")
    from_number: str | None = Field(default=None, env="TWILIO_FROM_NUMBER")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        allow_mutation = True

    @property
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)


class Settings(BaseSettings):
    """Application settings loaded from the environment with validation."""

    database_url: str | None = Field(default=None, env="DATABASE_URL")
    secret_key: str = Field(default="supersecret", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    reset_token_expire_minutes: int = Field(default=15, env="RESET_TOKEN_EXPIRE_MINUTES")
    stripe_secret_key: str | None = Field(default=None, env="STRIPE_SECRET_KEY")
    env: str = Field(default="development", env="ENV")

    smtp: SMTPSettings = Field(default_factory=SMTPSettings)
    quickbooks: QuickBooksSettings = Field(default_factory=QuickBooksSettings)
    google: GoogleOAuthSettings = Field(default_factory=GoogleOAuthSettings)
    twilio: TwilioSettings = Field(default_factory=TwilioSettings)
    thresholds: ThresholdSettings = Field(default_factory=ThresholdSettings)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("env", pre=True)
    def _normalise_env(cls, value: str | None) -> str:
        if not value:
            return "development"
        return value.lower()

    @root_validator()
    def _validate_production_requirements(cls, values: dict[str, object]) -> dict[str, object]:
        env = values.get("env", "development")
        if env == "production":
            missing: List[str] = []

            def _missing(field: str, env_name: str, *, disallow_default: str | None = None) -> None:
                val = values.get(field)
                if not val or (disallow_default and val == disallow_default):
                    missing.append(env_name)

            _missing("database_url", "DATABASE_URL")
            _missing("secret_key", "SECRET_KEY", disallow_default="supersecret")
            _missing("stripe_secret_key", "STRIPE_SECRET_KEY")

            smtp: SMTPSettings | None = values.get("smtp")  # type: ignore[assignment]
            if not smtp or not smtp.host:
                missing.append("SMTP_HOST")
            if not smtp or not smtp.username:
                missing.append("SMTP_USER")
            if not smtp or not smtp.password:
                missing.append("SMTP_PASS")

            if missing:
                required = ", ".join(sorted(set(missing)))
                raise ValueError(
                    "Missing required environment variables for production: " + required
                )

        return values


settings = Settings()

