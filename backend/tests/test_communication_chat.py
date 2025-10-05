from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import types


class _PrismaStub:
    def __init__(self, *args, **kwargs):
        pass


if "prisma" in sys.modules:
    sys.modules["prisma"].Prisma = _PrismaStub
else:
    sys.modules["prisma"] = types.SimpleNamespace(Prisma=_PrismaStub)

from app.auth.dependencies import get_current_user
from app.communication import routes as communication_routes
from app.communication import services as communication_services


@dataclass
class FakeUser:
    id: str
    email: str
    role: str = "TECHNICIAN"
    isActive: bool = True


@dataclass
class FakeThread:
    id: str
    participants: List[str] = field(default_factory=list)


@dataclass
class FakeMessage:
    id: str
    threadId: str
    senderId: str
    body: str
    sentAt: datetime


class FakeChatThreadTable:
    def __init__(self, records: Optional[List[FakeThread]] = None):
        self._records: Dict[str, FakeThread] = {record.id: record for record in records or []}

    async def find_unique(self, where: Dict[str, Any]):
        return self._records.get(where.get("id"))


class FakeChatMessageTable:
    def __init__(self, records: Optional[List[FakeMessage]] = None):
        self._records: List[FakeMessage] = records or []
        self._counter = len(self._records)

    async def create(self, data: Dict[str, Any]):
        self._counter += 1
        message = FakeMessage(
            id=f"msg-{self._counter}",
            threadId=data["threadId"],
            senderId=data["senderId"],
            body=data["body"],
            sentAt=datetime.utcnow(),
        )
        self._records.append(message)
        return message

    async def find_many(self, where: Dict[str, Any], order: Optional[Dict[str, str]] = None, take: Optional[int] = None):
        thread_id = where.get("threadId") if where else None
        results = [record for record in self._records if not thread_id or record.threadId == thread_id]

        if order and order.get("sentAt", "asc").lower() == "asc":
            results.sort(key=lambda record: record.sentAt)
        elif order and order.get("sentAt", "asc").lower() == "desc":
            results.sort(key=lambda record: record.sentAt, reverse=True)

        if take is not None:
            results = results[:take]
        return list(results)


class FakeUserTable:
    def __init__(self, users: Optional[List[FakeUser]] = None):
        self._users: Dict[str, FakeUser] = {user.email: user for user in users or []}

    async def find_unique(self, where: Dict[str, Any]):
        lookup = where.get("email")
        return self._users.get(lookup)


class FakeDB:
    def __init__(self, *, users: List[FakeUser], threads: List[FakeThread], messages: Optional[List[FakeMessage]] = None):
        self.connected = False
        self.user = FakeUserTable(users)
        self.chatthread = FakeChatThreadTable(threads)
        self.chatmessage = FakeChatMessageTable(messages)

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False


@pytest.fixture
def patch_chat_db(monkeypatch):
    def _patch(fake_db: FakeDB):
        monkeypatch.setattr(communication_routes, "db", fake_db)
        monkeypatch.setattr(communication_services, "db", fake_db)

    return _patch


def create_app(current_user: FakeUser) -> FastAPI:
    app = FastAPI()
    app.include_router(communication_routes.router)
    app.dependency_overrides[get_current_user] = lambda: current_user
    return app


def test_chat_repository_persists_messages(patch_chat_db):
    user = FakeUser(id="user-1", email="tech@example.com")
    thread = FakeThread(id="thread-1", participants=[user.id])
    fake_db = FakeDB(users=[user], threads=[thread])
    patch_chat_db(fake_db)

    async def _store_message():
        async with communication_services.ChatRepository(fake_db) as repo:
            return await repo.create_message(thread.id, user.id, "Hello")

    stored = asyncio.run(_store_message())

    assert stored["body"] == "Hello"
    assert stored["senderId"] == user.id
    assert stored["threadId"] == thread.id
    assert "T" in stored["sentAt"]
    assert not fake_db.connected


def test_message_history_returns_sorted_messages(patch_chat_db):
    user = FakeUser(id="user-1", email="tech@example.com")
    thread = FakeThread(id="thread-1", participants=[user.id])
    earlier = FakeMessage(
        id="msg-1",
        threadId=thread.id,
        senderId=user.id,
        body="first",
        sentAt=datetime.utcnow() - timedelta(minutes=5),
    )
    later = FakeMessage(
        id="msg-2",
        threadId=thread.id,
        senderId=user.id,
        body="second",
        sentAt=datetime.utcnow(),
    )

    fake_db = FakeDB(users=[user], threads=[thread], messages=[later, earlier])
    patch_chat_db(fake_db)

    app = create_app(user)
    client = TestClient(app)

    response = client.get(f"/communication/threads/{thread.id}/messages")

    assert response.status_code == 200
    payload = response.json()
    assert [message["body"] for message in payload] == ["first", "second"]


def test_message_history_enforces_participation(patch_chat_db):
    participant = FakeUser(id="user-1", email="tech@example.com")
    outsider = FakeUser(id="user-2", email="viewer@example.com")
    thread = FakeThread(id="thread-1", participants=[participant.id])

    fake_db = FakeDB(users=[participant, outsider], threads=[thread])
    patch_chat_db(fake_db)

    app = create_app(outsider)
    client = TestClient(app)

    response = client.get(f"/communication/threads/{thread.id}/messages")

    assert response.status_code == 403
    assert response.json()["detail"] == "Access to this thread is denied"


def test_message_history_allows_admin_override(patch_chat_db):
    participant = FakeUser(id="user-1", email="tech@example.com")
    admin = FakeUser(id="admin", email="admin@example.com", role="ADMIN")
    thread = FakeThread(id="thread-1", participants=[participant.id])

    fake_db = FakeDB(users=[participant, admin], threads=[thread])
    patch_chat_db(fake_db)

    app = create_app(admin)
    client = TestClient(app)

    response = client.get(f"/communication/threads/{thread.id}/messages")

    assert response.status_code == 200
    assert response.json() == []
