import os
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.append(str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("RESET_TOKEN_EXPIRE_MINUTES", "15")


class _PrismaImportStub:
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - import stub
        pass


if "prisma" in sys.modules:
    sys.modules["prisma"].Prisma = _PrismaImportStub
else:
    sys.modules["prisma"] = types.SimpleNamespace(Prisma=_PrismaImportStub)

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.audit import AuditLogMiddleware


class _UserRecord:
    def __init__(self, user_id: str):
        self.id = user_id


class _LogTable:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    async def create(self, data: Dict[str, Any]):
        self.records.append(data)
        return data


class _UserTable:
    def __init__(self, user: Optional[_UserRecord]):
        self._user = user

    async def find_unique(self, where: Dict[str, Any]):
        if not self._user:
            return None
        if where.get("email") == "user@example.com":
            return self._user
        return None


class _PrismaStub:
    def __init__(self, user: Optional[_UserRecord]):
        self.user = _UserTable(user)
        self.log = _LogTable()
        self._connected = False
        self.connect_calls = 0
        self.disconnect_calls = 0

    async def connect(self):
        self._connected = True
        self.connect_calls += 1

    async def disconnect(self):
        self._connected = False
        self.disconnect_calls += 1

    def is_connected(self) -> bool:
        return self._connected


@pytest.fixture
def audit_app(monkeypatch):
    prisma = _PrismaStub(_UserRecord("user-1"))

    def _decode(token: str):
        assert token == "valid-token"
        return {"sub": "user@example.com"}

    monkeypatch.setattr("app.core.audit.decode_token", _decode)

    app = FastAPI()
    app.add_middleware(AuditLogMiddleware, prisma_client=prisma)

    @app.get("/example")
    async def _example_route():
        return {"ok": True}

    client = TestClient(app)
    return client, prisma


def test_audit_middleware_records_metadata(audit_app):
    client, prisma = audit_app

    response = client.get(
        "/example",
        headers={"Authorization": "Bearer valid-token", "User-Agent": "pytest-agent"},
    )

    assert response.status_code == 200
    assert prisma.connect_calls == 1
    assert prisma.disconnect_calls == 1
    assert len(prisma.log.records) == 1

    record = prisma.log.records[0]
    assert record["action"] == "GET /example"
    assert record["userId"] == "user-1"
    assert record["userAgent"] == "pytest-agent"
    assert record["clientIp"]
    assert isinstance(record["latencyMs"], (int, float))
    assert record["latencyMs"] >= 0
