from __future__ import annotations

import pytest

from app.core.config import Settings


def test_production_missing_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    for key in [
        "DATABASE_URL",
        "SECRET_KEY",
        "STRIPE_SECRET_KEY",
        "SMTP_HOST",
        "SMTP_USER",
        "SMTP_PASS",
    ]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError) as excinfo:
        Settings()

    message = str(excinfo.value)
    for expected in [
        "DATABASE_URL",
        "SECRET_KEY",
        "STRIPE_SECRET_KEY",
        "SMTP_HOST",
        "SMTP_USER",
        "SMTP_PASS",
    ]:
        assert expected in message


def test_production_allows_when_env_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/db")
    monkeypatch.setenv("SECRET_KEY", "super-secret-key")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "stripe-secret")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USER", "smtp-user")
    monkeypatch.setenv("SMTP_PASS", "smtp-pass")
    monkeypatch.setenv("EMAIL_FROM", "alerts@example.com")

    settings = Settings()
    assert settings.env == "production"
    assert settings.smtp.is_configured
    assert settings.smtp.host == "smtp.example.com"
