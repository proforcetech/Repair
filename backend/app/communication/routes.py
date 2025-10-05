"""Communication routes including chat WebSocket handling."""

from __future__ import annotations

import json
from typing import Dict, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, require_role
from app.core.security import decode_token
from app.db.prisma_client import db
from app.communication.services import (
    ChatRepository,
    ThreadAccessError,
    ThreadNotFoundError,
)


router = APIRouter(prefix="/communication", tags=["communication"])


class NoteIn(BaseModel):
    appointmentId: Optional[str]
    vehicleId: Optional[str]
    content: str


@router.post("/notes/internal")
async def add_internal_note(data: NoteIn, user=Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)

    await db.connect()
    try:
        note = await db.internalnote.create(
            data={
                "appointmentId": data.appointmentId,
                "vehicleId": data.vehicleId,
                "authorId": user.id,
                "content": data.content,
            }
        )
    finally:
        await db.disconnect()

    return {"message": "Note added", "note": note}


chat_connections: Dict[str, Set[WebSocket]] = {}


def _connection_set(thread_id: str) -> Set[WebSocket]:
    return chat_connections.setdefault(thread_id, set())


async def _broadcast_message(thread_id: str, payload: dict) -> None:
    encoded = json.dumps(payload)
    sockets = list(chat_connections.get(thread_id, set()))
    stale: list[WebSocket] = []

    for connection in sockets:
        try:
            await connection.send_text(encoded)
        except Exception:  # pragma: no cover - defensive cleanup
            stale.append(connection)

    if stale:
        remaining = chat_connections.get(thread_id)
        if remaining is not None:
            for connection in stale:
                remaining.discard(connection)
            if not remaining:
                chat_connections.pop(thread_id, None)


@router.websocket("/ws/chat/{thread_id}")
async def websocket_chat(websocket: WebSocket, thread_id: str):
    token = websocket.query_params.get("token") or websocket.headers.get("Authorization")
    if token and token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1]

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_token(token)
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    email = payload.get("sub")
    if not email:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with ChatRepository(db) as repo:
        user = await repo.get_user_by_email(email)
        if not user or not getattr(user, "isActive", True):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        try:
            await repo.ensure_thread_access(thread_id, user)
        except ThreadNotFoundError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        except ThreadAccessError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()
        connections = _connection_set(thread_id)
        connections.add(websocket)

        try:
            while True:
                body = (await websocket.receive_text()).strip()
                if not body:
                    continue

                message = await repo.create_message(thread_id, getattr(user, "id"), body)
                await _broadcast_message(thread_id, message)
        except WebSocketDisconnect:
            pass
        finally:
            connections.discard(websocket)
            if not connections:
                chat_connections.pop(thread_id, None)


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, user=Depends(get_current_user)):
    async with ChatRepository(db) as repo:
        try:
            await repo.ensure_thread_access(thread_id, user)
        except ThreadNotFoundError:
            raise HTTPException(status_code=404, detail="Thread not found")
        except ThreadAccessError:
            raise HTTPException(status_code=403, detail="Access to this thread is denied")

        messages = await repo.list_messages(thread_id)

    return messages
