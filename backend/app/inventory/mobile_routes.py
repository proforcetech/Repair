# backend/app/inventory/mobile_routes.py
# This file contains mobile-specific inventory routes for quick part management.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/mobile/inventory")

@router.post("/receive")
async def mobile_quick_receive(
    sku: str,
    qty: int = 1,
    location: Optional[str] = None,
    user = Depends(get_current_user)
):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)
    await db.connect()
    part = await db.part.find_first(where={"sku": sku, "location": location} if location else {"sku": sku})

    if not part:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Part not found")

    updated = await db.part.update(
        where={"id": part.id},
        data={"quantity": part.quantity + qty}
    )

    await db.inventoryevent.create({
        "partId": part.id,
        "quantity": qty,
        "location": part.location,
        "type": "RECEIVE",
        "userId": user.id,
        "note": f"Mobile quick receive"
    })

    await db.disconnect()
    return {
        "message": f"Received {qty} x {part.name}",
        "new_quantity": updated.quantity
    }

class PartRequestCreate(BaseModel):
    sku: str
    quantity: int
    location: Optional[str] = None
    reason: Optional[str] = None

@router.post("/request-part")
async def request_part(data: PartRequestCreate, user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()
    req = await db.partrequest.create({
        **data.dict(),
        "userId": user.id
    })
    await db.disconnect()
    return {"message": "Request submitted", "request": req}

class PartRequestAck(BaseModel):
    note: Optional[str] = None

@router.post("/acknowledge/{request_id}")
async def acknowledge_request(request_id: str, data: PartRequestAck, user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()
    req = await db.partrequest.find_unique(where={"id": request_id})
    if not req or req.userId != user.id:
        await db.disconnect()
        raise HTTPException(status_code=403, detail="Not authorized")

    updated = await db.partrequest.update(
        where={"id": request_id},
        data={
            "techNote": data.note,
            "acknowledgedAt": datetime.utcnow()
        }
    )
    await db.disconnect()
    return {"message": "Request acknowledged", "request": updated}

class UpdateQtyMobile(BaseModel):
    qty: int

@router.put("/parts/{sku}/adjust")
async def adjust_quantity_mobile(sku: str, data: UpdateQtyMobile, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER"])(user)
    await db.connect()
    part = await db.part.find_unique(where={"sku": sku})
    if not part:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Part not found")

    updated = await db.part.update(where={"sku": sku}, data={"quantity": data.qty})
    await db.disconnect()
    return {"message": "Updated", "newQty": updated.quantity}
