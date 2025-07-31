# backend/app/repair/routes.py
# This file contains routes for managing repair orders, including creating, updating, and retrieving repair orders

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
import os
from fastapi.responses import FileResponse
import uuid
from fastapi import APIRouter, Depends
from prisma import Prisma
from app.auth.dependencies import get_current_user
from pydantic import BaseModel
from fastapi import UploadFile, File
import uuid
import os
from app.db.prisma_client import db
from fastapi.responses import FileResponse

APIRouter = APIRouter(prefix="/repair", tags=["repair"])

UPLOAD_DIR = "uploads"

@router.post("/{repair_order_id}/upload")
async def upload_file(repair_order_id: str, file: UploadFile = File(...), user = Depends(get_current_user)):
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    await db.connect()
    await db.repairattachment.create({
        "repairOrderId": repair_order_id,
        "filename": file.filename,
        "url": file_path
    })
    await db.disconnect()

    return {"message": "File uploaded", "path": file_path}


router = APIRouter()

class RepairOrderCreate(BaseModel):
    vehicle_id: str
    job_id: Optional[str] = None
    notes: Optional[str] = None

@router.post("/")
async def create_repair_order(data: RepairOrderCreate, user = Depends(get_current_user)):
    await db.connect()
    order = await db.repairorder.create({
        "vehicleId": data.vehicle_id,
        "customerId": user.id,
        "jobId": data.job_id,
        "notes": data.notes
    })
    await db.disconnect()
    return order

@router.post("/repair/{id}/invoice")
async def generate_invoice(id: str, user = Depends(get_current_user)):
    await db.connect()
    repair = await db.repairorder.find_unique(where={"id": id})
    if not repair or repair.customerId != user.id:
        await db.disconnect()
        raise HTTPException(status_code=403, detail="Unauthorized")

    invoice = await db.invoice.create({
        "customerId": repair.customerId,
        "repairOrderId": repair.id,
        "total": 0  # fill dynamically if items/job cards included
    })
    await db.disconnect()
    return invoice

@router.get("/{repair_order_id}/attachments")
async def list_attachments(repair_order_id: str, user = Depends(get_current_user)):
    await db.connect()
    attachments = await db.repairattachment.find_many(where={"repairOrderId": repair_order_id})
    await db.disconnect()
    return attachments

@router.get("/attachments/view/{filename}")
async def view_attachment(filename: str):
    file_path = os.path.join("uploads", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

class NoteCreate(BaseModel):
    message: str

@router.post("/{repair_order_id}/notes")
async def add_note(repair_order_id: str, data: NoteCreate, user = Depends(get_current_user)):
    await db.connect()
    order = await db.repairorder.find_unique(where={"id": repair_order_id})
    if not order:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Repair order not found")
    
    if user.role not in ["TECHNICIAN", "MANAGER", "ADMIN"] and order.customerId != user.id:
        await db.disconnect()
        raise HTTPException(status_code=403, detail="Permission denied")

    note = await db.repairnote.create({
        "repairOrderId": repair_order_id,
        "authorId": user.id,
        "message": data.message
    })
    await db.disconnect()
    return note

@router.get("/{repair_order_id}/notes")
async def get_notes(repair_order_id: str, user = Depends(get_current_user)):
    await db.connect()
    order = await db.repairorder.find_unique(where={"id": repair_order_id})
    if not order:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Repair order not found")
    
    if user.role not in ["TECHNICIAN", "MANAGER", "ADMIN"] and order.customerId != user.id:
        await db.disconnect()
        raise HTTPException(status_code=403, detail="Permission denied")

    notes = await db.repairnote.find_many(
        where={"repairOrderId": repair_order_id},
        include={"author": True},
        order={"timestamp": "asc"}
    )
    await db.disconnect()
    return notes
