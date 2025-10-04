import os
import sys
import types
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    import pyotp
except ImportError:  # pragma: no cover - fallback for test environment
    class _FakeTOTP:
        def __init__(self, secret: str):
            self._secret = secret

        def now(self) -> str:
            return self._secret

        def verify(self, token: str) -> bool:
            return token == self._secret

    class _FakePyOTP:
        @staticmethod
        def random_base32() -> str:
            return "A" * 16

        @staticmethod
        def TOTP(secret: str) -> _FakeTOTP:
            return _FakeTOTP(secret)

    pyotp = _FakePyOTP()

sys.path.append(str(Path(__file__).resolve().parents[1]))


class _PrismaStub:
    def __init__(self, *args, **kwargs):
        pass


if "prisma" in sys.modules:
    sys.modules["prisma"].Prisma = _PrismaStub
else:
    sys.modules["prisma"] = types.SimpleNamespace(Prisma=_PrismaStub)

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

from app.auth import routes as auth_routes  # noqa: E402
from app.core.security import (  # noqa: E402
    create_password_reset_token,
    hash_password,
    verify_password,
)


@dataclass
class FakeUserModel:
    id: str
    email: str
    role: str = "USER"
    hashedPwd: str = field(default_factory=lambda: hash_password("password"))
    failedLogins: int = 0
    lockedUntil: Optional[datetime] = None
    twoFactorEnabled: bool = False
    twoFactorSecret: Optional[str] = None
    isActive: bool = True
    createdAt: datetime = field(default_factory=datetime.utcnow)


class FakeUserTable:
    def __init__(self, user: Optional[FakeUserModel]):
        self.user = user

    async def find_unique(self, where: Dict[str, Any]):
        if not self.user:
            return None
        lookup = where.get("email") or where.get("id")
        if lookup in {self.user.email, self.user.id}:
            return self.user
        return None

    async def update(self, where: Dict[str, Any], data: Dict[str, Any]):
        if not self.user:
            return None
        matches_id = where.get("id")
        matches_email = where.get("email")
        if matches_id and matches_id != self.user.id:
            return None
        if matches_email and matches_email != self.user.email:
            return None
        for key, value in data.items():
            setattr(self.user, key, value)
        return self.user

    async def find_first(self, where: Dict[str, Any]):
        return None

    async def find_many(self, **_: Any):
        return []

    async def count(self, **_: Any):
        return 0


class FakeWarrantyAuditTable:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    async def create(self, data: Dict[str, Any]):
        self.records.append(data)
        return data

    async def find_first(self, **_: Any):
        return None

    async def find_many(self, **_: Any):
        return []


class FakeDB:
    def __init__(self, user: Optional[FakeUserModel]):
        self.user = FakeUserTable(user)
        self.warrantyaudit = FakeWarrantyAuditTable()
        self.connected = False

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False


@pytest.fixture
def make_client(monkeypatch):
    def _make(user: Optional[FakeUserModel]):
        fake_db = FakeDB(user)
        monkeypatch.setattr(auth_routes, "db", fake_db)
        app = FastAPI()
        app.include_router(auth_routes.router, prefix="/auth")
        client = TestClient(app)
        return client, fake_db

    return _make


def test_login_success(make_client):
    password = "s3cret"
    user = FakeUserModel(id="user-1", email="user@example.com", hashedPwd=hash_password(password))
    client, fake_db = make_client(user)

    response = client.post(
        "/auth/login",
        data={"username": user.email, "password": password},
        headers={"user-agent": "pytest"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert fake_db.warrantyaudit.records[-1]["action"] == "LOGIN"
    assert "Outcome=SUCCESS" in fake_db.warrantyaudit.records[-1]["detail"]
    assert user.failedLogins == 0
    assert user.lockedUntil is None


def test_login_failure_increments_counter(make_client):
    password = "s3cret"
    user = FakeUserModel(id="user-2", email="user@example.com", hashedPwd=hash_password(password))
    client, fake_db = make_client(user)

    response = client.post(
        "/auth/login",
        data={"username": user.email, "password": "wrong"},
        headers={"user-agent": "pytest"},
    )

    assert response.status_code == 401
    assert user.failedLogins == 1
    assert fake_db.warrantyaudit.records[-1]["action"] == "LOGIN_FAILED"
    assert "Outcome=INVALID_CREDENTIALS" in fake_db.warrantyaudit.records[-1]["detail"]


def test_login_with_2fa(make_client):
    password = "s3cret"
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    user = FakeUserModel(
        id="user-3",
        email="user@example.com",
        hashedPwd=hash_password(password),
        twoFactorEnabled=True,
        twoFactorSecret=secret,
    )
    client, fake_db = make_client(user)

    token = totp.now()
    response = client.post(
        "/auth/login",
        data={"username": user.email, "password": password, "two_factor_token": token},
        headers={"user-agent": "pytest"},
    )

    assert response.status_code == 200
    assert fake_db.warrantyaudit.records[-1]["action"] == "LOGIN"
    assert "Outcome=SUCCESS" in fake_db.warrantyaudit.records[-1]["detail"]


def test_reset_password_success(make_client):
    original_password = "old-pass"
    new_password = "n3w-pass"
    user = FakeUserModel(
        id="user-4",
        email="reset@example.com",
        hashedPwd=hash_password(original_password),
    )
    client, _ = make_client(user)

    token = create_password_reset_token(user.email, expires_delta=timedelta(minutes=5))

    response = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )

    assert response.status_code == 200
    assert verify_password(new_password, user.hashedPwd)


def test_reset_password_expired_token(make_client):
    original_password = "stay-same"
    user = FakeUserModel(
        id="user-5",
        email="expired@example.com",
        hashedPwd=hash_password(original_password),
    )
    client, _ = make_client(user)

    token = create_password_reset_token(user.email, expires_delta=timedelta(seconds=-1))

    response = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "unused"},
    )

    assert response.status_code == 400
    assert verify_password(original_password, user.hashedPwd)
