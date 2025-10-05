import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))


if "fastapi" not in sys.modules:  # pragma: no cover - testing fallback
    fastapi_stub = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail

    class APIRouter:
        def __init__(self, *args, **kwargs):
            self.routes = []

        def post(self, *args, **kwargs):
            def decorator(func):
                self.routes.append(func)
                return func

            return decorator

    def Depends(dependency):  # noqa: D401 - simple passthrough stub
        return dependency

    def File(*args, **kwargs):  # noqa: D401 - simple sentinel stub
        return None

    class UploadFile:  # pragma: no cover - placeholder for type hints
        pass

    fastapi_stub.APIRouter = APIRouter
    fastapi_stub.Depends = Depends
    fastapi_stub.HTTPException = HTTPException
    fastapi_stub.File = File
    fastapi_stub.UploadFile = UploadFile

    sys.modules["fastapi"] = fastapi_stub


if "pydantic" not in sys.modules:  # pragma: no cover - testing fallback
    pydantic_stub = types.ModuleType("pydantic")

    class BaseModel:  # pragma: no cover - placeholder for import
        pass

    pydantic_stub.BaseModel = BaseModel
    sys.modules["pydantic"] = pydantic_stub


if "prisma" not in sys.modules:  # pragma: no cover - testing fallback
    prisma_stub = types.ModuleType("prisma")

    class Prisma:  # pragma: no cover - placeholder for import
        def __init__(self, *args, **kwargs):
            pass

    prisma_stub.Prisma = Prisma
    sys.modules["prisma"] = prisma_stub


if "app.auth.dependencies" not in sys.modules:  # pragma: no cover - testing fallback
    auth_dependencies_stub = types.ModuleType("app.auth.dependencies")

    def _require_role(roles):  # noqa: D401 - simple passthrough stub
        return lambda user: user

    async def _get_current_user():  # pragma: no cover - placeholder for import
        return SimpleNamespace(role="ACCOUNTANT")

    auth_dependencies_stub.require_role = _require_role
    auth_dependencies_stub.get_current_user = _get_current_user

    sys.modules["app.auth.dependencies"] = auth_dependencies_stub

from app.bank import routes as bank_routes  # noqa: E402


class FakeUploadFile:
    def __init__(self, content: bytes):
        self._content = content

    async def read(self) -> bytes:
        return self._content


class FakeBankTransactionTable:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []
        self.create_many_called = False

    async def create_many(self, *, data: List[Dict[str, Any]]):
        self.create_many_called = True
        self.records.extend(data)
        return SimpleNamespace(count=len(data))


class FakeDB:
    def __init__(self):
        self.banktransaction = FakeBankTransactionTable()
        self.connected = False

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False


@pytest.fixture(autouse=True)
def patch_db(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(bank_routes, "db", fake_db)
    monkeypatch.setattr(bank_routes, "require_role", lambda roles: lambda user: user)
    return fake_db


def _make_file(content: str) -> FakeUploadFile:
    return FakeUploadFile(content.encode("utf-8"))


def test_import_bank_transactions_success(patch_db):
    file = _make_file(
        "\n".join(
            [
                "date,amount,type,memo",
                "2024-01-01T00:00:00,150.25,DEPOSIT,Initial funding",
                "2024-01-02,75.00,WITHDRAWAL,Utilities",
            ]
        )
    )

    response = asyncio.run(
        bank_routes.import_bank_txn(file=file, user=SimpleNamespace(role="ACCOUNTANT"))
    )

    assert response == {"message": "Bank statement imported", "count": 2}
    assert patch_db.connected is False
    assert patch_db.banktransaction.create_many_called is True
    assert len(patch_db.banktransaction.records) == 2


def test_import_bank_transactions_missing_column(patch_db):
    file = _make_file(
        "\n".join(
            [
                "date,amount,memo",
                "2024-01-01,100,Missing type",
            ]
        )
    )

    with pytest.raises(bank_routes.HTTPException) as excinfo:
        asyncio.run(
            bank_routes.import_bank_txn(file=file, user=SimpleNamespace(role="ACCOUNTANT"))
        )

    assert excinfo.value.status_code == 400
    assert "Missing required columns" in excinfo.value.detail
    assert patch_db.banktransaction.create_many_called is False


def test_import_bank_transactions_invalid_date(patch_db):
    file = _make_file(
        "\n".join(
            [
                "date,amount,type",
                "not-a-date,100,DEPOSIT",
            ]
        )
    )

    with pytest.raises(bank_routes.HTTPException) as excinfo:
        asyncio.run(
            bank_routes.import_bank_txn(file=file, user=SimpleNamespace(role="ACCOUNTANT"))
        )

    assert excinfo.value.status_code == 400
    assert "invalid date" in excinfo.value.detail
    assert patch_db.banktransaction.create_many_called is False
