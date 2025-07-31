# backend/app/customers/vehicles.py

## This file contains routes for managing customer vehicles in the Repair application.
# It allows adding, listing, and archiving vehicles associated with a customer. 

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from prisma import Prisma
from app.auth.dependencies import get_current_user, require_role
from typing import Optional
from app.db.prisma_client import db

router = APIRouter(prefix="/customers", tags=["customers"])

db = Prisma()

class VehicleCreate(BaseModel):
    vin: str
    make: str
    model: str
    year: int

# This route allows admins and front desk staff to add a new vehicle for a customer.
# It requires the user to have one of the specified roles to access this functionality.
@router.post("/{customer_id}/vehicles")
async def add_vehicle(customer_id: str, data: VehicleCreate, user=Depends(get_current_user)):
    require_role(["ADMIN", "FRONT_DESK", "MANAGER"])(user)
    await db.connect()
    existing = await db.vehicle.find_unique(where={"vin": data.vin})
    if existing:
        await db.disconnect()
        raise HTTPException(400, "Vehicle already registered")
    
    created = await db.vehicle.create(data={**data.dict(), "customerId": customer_id})
    await db.disconnect()
    return created

# This route retrieves all vehicles associated with a specific customer.
# It requires the user to have one of the specified roles to access customer vehicle data.
@router.get("/{customer_id}/vehicles")
async def list_vehicles(customer_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "TECHNICIAN", "FRONT_DESK"])(user)
    await db.connect()
    vehicles = await db.vehicle.find_many(where={"customerId": customer_id})
    await db.disconnect()
    return vehicles

# This route retrieves the history of a specific vehicle, including its owner and repair orders.
# It requires the user to have one of the specified roles to access vehicle history.
@router.delete("/vehicles/{vehicle_id}")
async def archive_vehicle(vehicle_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    updated = await db.vehicle.update(where={"id": vehicle_id}, data={"archived": True})
    await db.disconnect()
    return {"message": "Vehicle archived", "vehicle": updated}
