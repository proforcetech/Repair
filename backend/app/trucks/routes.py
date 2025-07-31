# File: backend/app/trucks/routes.py
# This file contains routes for managing truck GPS updates and location tracking.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from datetime import datetime
from typing import Optional
from fastapi import APIRouter
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from typing import Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
router = APIRouter(prefix="/trucks", tags=["trucks"])

class GPSUpdate(BaseModel):
    lat: float
    lon: float

@router.post("/trucks/{id}/location")
async def update_gps(id: str, loc: GPSUpdate):
    await db.connect()
    updated = await db.servicetruck.update(
        where={"id": id},
        data={"gpsLat": loc.lat, "gpsLon": loc.lon, "lastUpdate": datetime.utcnow()}
    )
    await db.disconnect()
    return {"message": "Location updated", "truck": updated}

class GPSPing(BaseModel):
    lat: float
    lon: float

@router.post("/trucks/{id}/ping")
async def record_gps_ping(id: str, ping: GPSPing):
    await db.connect()
    await db.truckgps.create(data={"truckId": id, "lat": ping.lat, "lon": ping.lon})
    await db.disconnect()
    return {"message": "Ping recorded"}
