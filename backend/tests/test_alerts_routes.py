from __future__ import annotations

import asyncio
import sys
import types
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List

import pytest


class _PrismaStub:
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - stub
        pass


if "prisma" in sys.modules:
    sys.modules["prisma"].Prisma = _PrismaStub
else:
    sys.modules["prisma"] = types.SimpleNamespace(Prisma=_PrismaStub)


class _FakeJWTError(Exception):
    pass


class _FakeJWTModule:
    @staticmethod
    def encode(*args: Any, **kwargs: Any) -> str:
        return "token"

    @staticmethod
    def decode(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}


if "jose" not in sys.modules:
    fake_jose = types.SimpleNamespace(
        JWTError=_FakeJWTError,
        jwt=_FakeJWTModule,
        exceptions=types.SimpleNamespace(ExpiredSignatureError=_FakeJWTError),
    )
    sys.modules["jose"] = fake_jose
    sys.modules["jose.exceptions"] = fake_jose.exceptions


class _FakeCryptContext:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def hash(self, password: str) -> str:
        return f"hashed-{password}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"hashed-{plain}"


if "passlib" not in sys.modules:
    fake_passlib = types.SimpleNamespace(context=types.SimpleNamespace(CryptContext=_FakeCryptContext))
    sys.modules["passlib"] = fake_passlib
    sys.modules["passlib.context"] = fake_passlib.context


if "dotenv" not in sys.modules:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None)


if "aiosmtplib" not in sys.modules:
    async def _fake_send(*args: Any, **kwargs: Any) -> None:
        return None

    sys.modules["aiosmtplib"] = types.SimpleNamespace(send=_fake_send)


sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.alerts import routes  # noqa: E402


class FakeTable:
    def __init__(self, records: List[Any] | None = None) -> None:
        self.records = records or []

    async def find_many(self, *args: Any, **kwargs: Any) -> List[Any]:
        return list(self.records)

    async def update(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}


class FakeDB:
    def __init__(self) -> None:
        self.jobpart = FakeTable()
        self.job = FakeTable()
        self.part = FakeTable()
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False


@pytest.fixture()
def fake_db(monkeypatch: pytest.MonkeyPatch) -> FakeDB:
    db = FakeDB()
    monkeypatch.setattr(routes, "db", db)
    return db


def test_high_substitution_alert_notifies_procurement(fake_db: FakeDB, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db.jobpart.records = [
        SimpleNamespace(substituted=True, originalSku="SKU-1"),
        SimpleNamespace(substituted=True, originalSku="SKU-1"),
        SimpleNamespace(substituted=True, originalSku="SKU-1"),
        SimpleNamespace(substituted=True, originalSku="SKU-2"),
    ]

    notifications: List[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def fake_notify_user(*args: Any, **kwargs: Any) -> None:
        notifications.append((args, kwargs))

    monkeypatch.setattr(routes, "notify_user", fake_notify_user)

    user = SimpleNamespace(role="MANAGER")
    result = asyncio.run(routes.substitution_procurement_alert(user=user))

    assert result["alerted_skus"] == ["SKU-1"]
    assert notifications
    _, kwargs = notifications[0]
    assert kwargs["email"] == "procurement@repairshop.com"
    assert "SKU-1" in kwargs["body"]


def test_bay_overload_alert_uses_settings_threshold(fake_db: FakeDB, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db.job.records = [
        SimpleNamespace(bayId="BAY-1", createdAt=datetime(2024, 1, 1, 8, 0, 0)),
        SimpleNamespace(bayId="BAY-1", createdAt=datetime(2024, 1, 1, 9, 0, 0)),
        SimpleNamespace(bayId="BAY-1", createdAt=datetime(2024, 1, 1, 10, 0, 0)),
    ]

    monkeypatch.setattr(routes.settings, "MAX_BAY_JOBS_PER_DAY", 2)

    notifications: List[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def fake_notify_user(*args: Any, **kwargs: Any) -> None:
        notifications.append((args, kwargs))

    monkeypatch.setattr(routes, "notify_user", fake_notify_user)

    user = SimpleNamespace(role="MANAGER")
    result = asyncio.run(routes.bay_overload_alert(user=user))

    assert result["alerts"] == [
        {"bay": "BAY-1", "date": "2024-01-01", "job_count": 3},
    ]
    assert notifications
    _, kwargs = notifications[0]
    assert "BAY-1" in kwargs["body"]


def test_low_stock_alert_notifies_channels(fake_db: FakeDB, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db.part.records = [
        SimpleNamespace(sku="SKU-LOW", description="Widget", quantityOnHand=1),
    ]

    email_calls: List[tuple[tuple[Any, ...], dict[str, Any]]] = []
    sms_calls: List[tuple[tuple[Any, ...], dict[str, Any]]] = []
    slack_calls: List[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def fake_send_email(*args: Any, **kwargs: Any) -> None:
        email_calls.append((args, kwargs))

    async def fake_send_sms(*args: Any, **kwargs: Any) -> None:
        sms_calls.append((args, kwargs))

    async def fake_notify_slack(*args: Any, **kwargs: Any) -> None:
        slack_calls.append((args, kwargs))

    monkeypatch.setattr(routes, "send_email", fake_send_email)
    monkeypatch.setattr(routes, "send_sms", fake_send_sms)
    monkeypatch.setattr(routes, "notify_slack", fake_notify_slack)

    asyncio.run(routes.alert_low_stock())

    assert email_calls and email_calls[0][1]["to_email"] == "manager@shop.com"
    assert sms_calls and sms_calls[0][0][0] == "+12223334444"
    assert slack_calls and slack_calls[0][0][0] == "#inventory"
