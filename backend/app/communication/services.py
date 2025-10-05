"""Chat persistence services backed by Prisma."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, List, Sequence

from app.db.prisma_client import db


class ThreadNotFoundError(Exception):
    """Raised when a chat thread cannot be located."""


class ThreadAccessError(Exception):
    """Raised when a user attempts to access a thread they are not part of."""


def _extract(record: Any, key: str, default: Any | None = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def _normalise_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:  # pragma: no cover - defensive
            return None
    return None


def serialise_message(message: Any) -> dict[str, Any]:
    sent_at = _normalise_datetime(_extract(message, "sentAt"))
    return {
        "id": _extract(message, "id"),
        "threadId": _extract(message, "threadId"),
        "senderId": _extract(message, "senderId"),
        "body": _extract(message, "body"),
        "sentAt": sent_at.isoformat() if sent_at else None,
    }


class ChatRepository:
    """Repository for chat threads and messages that manages DB connections."""

    def __init__(self, database=db):
        self._db = database
        self._connected = False

    async def __aenter__(self) -> "ChatRepository":
        await self._db.connect()
        self._connected = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._connected:
            await self._db.disconnect()
        self._connected = False

    async def get_user_by_email(self, email: str) -> Any:
        return await self._db.user.find_unique(where={"email": email})

    async def get_thread(self, thread_id: str) -> Any:
        return await self._db.chatthread.find_unique(where={"id": thread_id})

    async def ensure_thread_access(self, thread_id: str, user: Any) -> Any:
        thread = await self.get_thread(thread_id)
        if not thread:
            raise ThreadNotFoundError(thread_id)

        participants: Sequence[str] = _extract(thread, "participants", []) or []
        user_id = _extract(user, "id")
        role = (_extract(user, "role") or "").upper()

        if role not in {"ADMIN", "MANAGER"} and user_id not in set(participants):
            raise ThreadAccessError(thread_id)

        return thread

    async def create_message(self, thread_id: str, sender_id: str, body: str) -> dict[str, Any]:
        message = await self._db.chatmessage.create(
            data={
                "threadId": thread_id,
                "senderId": sender_id,
                "body": body,
            }
        )
        return serialise_message(message)

    async def list_messages(self, thread_id: str, limit: int = 100) -> List[dict[str, Any]]:
        messages: Iterable[Any] = await self._db.chatmessage.find_many(
            where={"threadId": thread_id},
            order={"sentAt": "asc"},
            take=limit,
        )
        return [serialise_message(message) for message in messages]

