# backend/app/chat/routes.py
# This file contains routes for managing chat messages between users, including sending and retrieving messages.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatInput(BaseModel):
    receiverId: str
    message: str

@router.post("/chat/send")
async def send_chat(data: ChatInput, user=Depends(get_current_user)):
    await db.connect()
    msg = await db.chatmessage.create(data={
        "senderId": user.id,
        "receiverId": data.receiverId,
        "message": data.message
    })
    await db.disconnect()
    return msg

@router.get("/chat/with/{user_id}")
async def get_chat(user_id: str, user=Depends(get_current_user)):
    await db.connect()
    messages = await db.chatmessage.find_many(where={
        "OR": [
            {"senderId": user.id, "receiverId": user_id},
            {"senderId": user_id, "receiverId": user.id},
        ]
    }, order={"sentAt": "asc"})
    await db.disconnect()
    return messages
