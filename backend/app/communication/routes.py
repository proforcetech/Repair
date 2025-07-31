# backend/app/communication/routes.py
# This file contains routes for managing internal notes and chat messages between users.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict

router = APIRouter(prefix="/communication", tags=["communication"])



class NoteIn(BaseModel):
    appointmentId: Optional[str]
    vehicleId: Optional[str]
    content: str

@router.post("/notes/internal")
async def add_internal_note(data: NoteIn, user=Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)

    await db.connect()
    note = await db.internalnote.create(data={
        "appointmentId": data.appointmentId,
        "vehicleId": data.vehicleId,
        "authorId": user.id,
        "content": data.content
    })
    await db.disconnect()
    return {"message": "Note added", "note": note}

chat_connections: Dict[str, list[WebSocket]] = {}

@router.websocket("/ws/chat/{thread_id}")
async def websocket_chat(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    if thread_id not in chat_connections:
        chat_connections[thread_id] = []
    chat_connections[thread_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast to all users in thread
            for conn in chat_connections[thread_id]:
                await conn.send_text(data)
    except WebSocketDisconnect:
        chat_connections[thread_id].remove(websocket)
