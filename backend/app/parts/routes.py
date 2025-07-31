# backend/app/parts/routes.py
# This file contains part management routes for handling part returns and RMAs.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db

router = APIRouter(prefix="/parts", tags=["parts"])

class ReturnIn(BaseModel):
    partId: str
    reason: str

@router.post("/parts/return")
async def submit_part_return(data: ReturnIn, user=Depends(get_current_user)):
    require_role(["MANAGER", "INVENTORY", "ADMIN"])(user)

    await db.connect()
    return_record = await db.partreturn.create(data={
        "partId": data.partId,
        "reason": data.reason
    })
    await db.disconnect()
    return {"message": "Return initiated", "return": return_record}

@router.put("/parts/return/{id}/rma")
async def update_rma(id: str, rma: str, status: str, user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    updated = await db.partreturn.update(where={"id": id}, data={
        "rmaNumber": rma,
        "status": status.upper()
    })
    await db.disconnect()
    return {"message": "RMA updated", "return": updated}
