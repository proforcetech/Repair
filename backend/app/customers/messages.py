## File: backend/app/customers/messages.py
# This file handles customer message logging and retrieval.
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db

router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)

class MessageCreate(BaseModel):
    type: str  # "SMS", "EMAIL", "NOTE"
    content: str

@router.post("/{customer_id}/messages")
async def log_message(customer_id: str, data: MessageCreate, user=Depends(get_current_user)):
    require_role(["ADMIN", "FRONT_DESK", "MANAGER", "TECHNICIAN"])(user)
    await db.connect()
    created = await db.customermessage.create(data={**data.dict(), "customerId": customer_id})
    await db.disconnect()
    return created

@router.get("/{customer_id}/messages")
async def list_messages(customer_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK", "TECHNICIAN"])(user)
    await db.connect()
    logs = await db.customermessage.find_many(where={"customerId": customer_id}, order={"sentAt": "desc"})
    await db.disconnect()
    return logs
