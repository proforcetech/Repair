# backend/app/bays/routes.py
# This file contains routes for managing bays, including updating bay status and listing bays.

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from app.core.notifier import send_email
from fastapi.responses import JSONResponse
from fastapi import UploadFile, File
from app.core.pdf import generate_pdf  # wherever your PDF helper lives
from datetime import datetime
from typing import Any
from fastapi.responses import FileResponse
from prisma import Prisma
from app.auth.dependencies import get_current_user, require_role
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from fastapi import HTTPException
from app.db.prisma_client import db

router = APIRouter(prefix="/bays", tags=["bays"])

@router.put("/bays/{id}/status")
async def update_bay_status(id: str, isOccupied: bool, user=Depends(get_current_user)):
    require_role(["FRONT-DESK", "MANAGER", "ADMIN"])(user)

    await db.connect()
    updated = await db.bay.update(where={"id": id}, data={"isOccupied": isOccupied})
    await db.disconnect()
    return {"message": "Bay updated", "bay": updated}

@router.get("/bays")
async def list_bays(user=Depends(get_current_user)):
    await db.connect()
    bays = await db.bay.find_many()
    await db.disconnect()
    return bays
