# File: backend/app/mobile/routes.py
# This file contains routes for mobile app functionalities, including truck location updates and VIN scanning.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db 

APIRouter = APIRouter(prefix="/mobile", tags=["mobile"])

class LocationUpdate(BaseModel):
    lat: float
    lng: float

@router.put("/trucks/{truck_id}/location")
async def update_truck_location(truck_id: str, loc: LocationUpdate, user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)

    await db.connect()
    await db.mobiletruck.update(
        where={"id": truck_id},
        data={"lat": loc.lat, "lng": loc.lng}
    )
    await db.disconnect()
    return {"message": "Location updated"}

@router.get("/trucks/map")
async def list_truck_locations(user=Depends(get_current_user)):
    require_role(["MANAGER", "DISPATCH"])(user)

    await db.connect()
    trucks = await db.mobiletruck.find_many(where={"available": True})
    await db.disconnect()
    return trucks

@router.post("/scan/vin")
async def scan_vin(data: dict):
    vin = data.get("vin", "").strip().upper()
    if len(vin) != 17:
        raise HTTPException(400, detail="Invalid VIN")

    await db.connect()
    vehicle = await db.vehicle.find_unique(where={"vin": vin})
    await db.disconnect()
    if not vehicle:
        raise HTTPException(404, detail="Vehicle not found")
    return vehicle
