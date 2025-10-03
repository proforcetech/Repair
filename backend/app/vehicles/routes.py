# File: backend/app/vehicles/routes.py
# This file contains routes for managing vehicles, including adding new vehicles, retrieving user vehicles,
# and managing vehicle history and maintenance contracts.

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from app.auth.dependencies import get_current_user
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from fastapi.responses import StreamingResponse
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import io
from uuid import uuid4
from app.auth.dependencies import require_role
from app.db.prisma_client import db

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _current_odometer(job_items) -> Optional[int]:
    """Return the most recent odometer value from job items if available."""

    for item in job_items:
        odometer = getattr(item, "odometer", None)
        if odometer is not None:
            return odometer
    return None

class VehicleCreate(BaseModel):
    vin: str
    make: str
    model: str
    year: int


@router.post("/")
async def add_vehicle(data: VehicleCreate, user=Depends(get_current_user)):
    await db.connect()
    vehicle = await db.vehicle.create(
        data={
            "vin": data.vin,
            "make": data.make,
            "model": data.model,
            "year": data.year,
            "ownerId": user.id,
        }
    )
    await db.disconnect()
    return vehicle


@router.get("/")
async def get_user_vehicles(user=Depends(get_current_user)):
    await db.connect()
    vehicles = await db.vehicle.find_many(where={"ownerId": user.id})
    await db.disconnect()
    return vehicles


@router.get("/{vehicle_id}/history")
async def get_vehicle_history(vehicle_id: str, user=Depends(get_current_user)):
    await db.connect()
    vehicle = await db.vehicle.find_unique(
        where={"id": vehicle_id},
        include={
            "owner": True,
            "RepairOrder": {"include": {"job": True}},
        },
    )

    invoices = await db.invoice.find_many(where={"vehicleId": vehicle_id})
    estimates = await db.estimate.find_many(where={"vehicleId": vehicle_id})
    notes = await db.customernote.find_many(where={"vehicleId": vehicle_id})
    service_records = await db.servicerecord.find_many(
        where={"vehicleId": vehicle_id},
        order={"date": "desc"},
    )
    await db.disconnect()

    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    is_owner = vehicle.ownerId == user.id
    allowed_roles = {"ADMIN", "MANAGER", "FRONT_DESK", "TECHNICIAN"}
    if not (is_owner or user.role in allowed_roles):
        raise HTTPException(status_code=403, detail="Unauthorized")

    return {
        "vehicle": {
            "vin": vehicle.vin,
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
        },
        "owner": vehicle.owner.email if vehicle.owner else None,
        "repair_orders": vehicle.RepairOrder,
        "invoices": invoices,
        "estimates": estimates,
        "notes": notes,
        "service_records": service_records,
    }

@router.put("/{vehicle_id}/archive")
async def archive_vehicle(vehicle_id: str, user=Depends(get_current_user)):
    await db.connect()
    vehicle = await db.vehicle.find_unique(where={"id": vehicle_id})
    if not vehicle:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if vehicle.ownerId != user.id and user.role not in {"ADMIN", "MANAGER"}:
        await db.disconnect()
        raise HTTPException(status_code=403, detail="Unauthorized")

    updated = await db.vehicle.update(
        where={"id": vehicle_id},
        data={"isArchived": True},
    )
    await db.disconnect()
    return {"message": "Vehicle archived", "vehicle": updated}


@router.put("/{vehicle_id}/unarchive")
async def unarchive_vehicle(vehicle_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    updated = await db.vehicle.update(
        where={"id": vehicle_id},
        data={"isArchived": False},
    )
    await db.disconnect()
    return {"message": "Vehicle restored", "vehicle": updated}


@router.get("/{vehicle_id}/parts")
async def get_vehicle_part_history(vehicle_id: str, user=Depends(get_current_user)):
    await db.connect()
    jobs = await db.job.find_many(where={"vehicleId": vehicle_id})
    job_ids = [j.id for j in jobs]
    parts = await db.jobpart.find_many(
        where={"jobId": {"in": job_ids}},
        include={"part": True, "job": True},
    )
    await db.disconnect()
    return [
        {
            "job_id": p.jobId,
            "date": p.job.startTime,
            "sku": p.part.sku,
            "description": p.part.description,
            "qty": p.qty,
            "cost": p.qty * p.part.cost,
        }
        for p in parts
    ]


@router.get("/{vehicle_id}/history/pdf")
async def export_vehicle_history_pdf(vehicle_id: str, user=Depends(get_current_user)):
    await db.connect()
    vehicle = await db.vehicle.find_unique(where={"id": vehicle_id})
    invoices = await db.invoice.find_many(
        where={"estimate": {"vehicleId": vehicle_id}},
        include={"estimate": {"include": {"items": True}}}
    )
    await db.disconnect()

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("vehicle_history.html")
    html_out = template.render(vehicle=vehicle, invoices=invoices)

    pdf = HTML(string=html_out).write_pdf()
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=history_{vehicle_id}.pdf"
    })

class ContractCreate(BaseModel):
    planName: str
    startDate: datetime
    endDate: datetime
    mileageLimit: Optional[int]
    terms: Optional[str]

@router.post("/{vehicle_id}/contracts")
async def assign_contract(vehicle_id: str, data: ContractCreate, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    contract = await db.maintenancecontract.create(
        data={**data.dict(), "vehicleId": vehicle_id}
    )
    await db.disconnect()
    return contract

@router.get("/{vehicle_id}/contracts")
async def get_vehicle_contracts(vehicle_id: str, user=Depends(get_current_user)):
    await db.connect()
    contracts = await db.maintenancecontract.find_many(where={"vehicleId": vehicle_id})
    await db.disconnect()
    return contracts

class MaintenanceForecast(BaseModel):
    dueMileage: Optional[int]
    dueDate: Optional[datetime]
    serviceType: str
    notes: Optional[str]

@router.post("/{vehicle_id}/forecast")
async def add_maintenance_forecast(vehicle_id: str, entry: MaintenanceForecast, user=Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER"])(user)

    await db.connect()
    forecast = await db.maintenanceschedule.create(data={**entry.dict(), "vehicleId": vehicle_id})
    await db.disconnect()
    return forecast

@router.get("/maintenance/upcoming")
async def upcoming_maintenance(user=Depends(get_current_user)):
    require_role(["TECHNICIAN", "FRONT_DESK"])(user)

    today = datetime.utcnow()
    await db.connect()
    items = await db.maintenanceschedule.find_many(
        where={
            "isCompleted": False,
            "OR": [
                {"dueDate": {"lte": today + timedelta(days=30)}},
                {"dueMileage": {"lte": 1000}}  # hardcoded threshold
            ]
        }
    )
    await db.disconnect()
    return items

@router.get("/{vehicle_id}/recommendations")
async def recommend_services(vehicle_id: str, user=Depends(get_current_user)):
    await db.connect()

    jobs = await db.jobitem.find_many(
        where={"vehicleId": vehicle_id},
        order={"finishedAt": "desc"},
    )

    # naive example logic
    recommendations = []
    last_oil_change = next(
        (j for j in jobs if j.description and "oil" in j.description.lower()),
        None,
    )

    current_odometer = _current_odometer(jobs)
    if (
        last_oil_change
        and last_oil_change.odometer is not None
        and current_odometer is not None
        and last_oil_change.odometer + 5000 <= current_odometer
    ):
        recommendations.append("Oil Change")

    # Add more service logic here (e.g., brake inspection, tire rotation)

    await db.disconnect()
    return {"recommendedServices": recommendations}

@router.post("/{id}/upload-doc")
async def upload_doc(id: str, file: UploadFile, roleView: str, user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN", "TECHNICIAN"])(user)

    filename = f"{uuid4()}_{file.filename}"
    filepath = f"uploads/{filename}"
    with open(filepath, "wb") as f:
        f.write(await file.read())

    await db.connect()
    doc = await db.vehicledocument.create(
        data={
            "vehicleId": id,
            "uploadedBy": user.id,
            "filename": file.filename,
            "url": filepath,
            "roleView": roleView.upper(),
        }
    )
    await db.disconnect()
    return {"message": "Uploaded", "document": doc}

@router.get("/{id}/docs")
async def get_docs(id: str, user=Depends(get_current_user)):
    await db.connect()
    docs = await db.vehicledocument.find_many(where={
        "vehicleId": id,
        "roleView": {"in": [user.role, "ADMIN"]}  # e.g., tech sees TECHNICIAN/ADMIN docs
    })
    await db.disconnect()
    return docs


class ItemResponse(BaseModel):
    itemId: str
    status: str  # GOOD / ATTENTION / REPLACE
    notes: Optional[str] = None

class InspectionSubmission(BaseModel):
    templateId: str
    responses: list[ItemResponse]

@router.post("/{vehicle_id}/inspection")
async def submit_inspection(vehicle_id: str, data: InspectionSubmission, user=Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER"])(user)

    await db.connect()
    insp = await db.vehicleinspection.create(
        data={
            "vehicleId": vehicle_id,
            "technicianId": user.id,
            "templateId": data.templateId,
            "responses": {
                "create": [
                    {"itemId": r.itemId, "status": r.status, "notes": r.notes}
                    for r in data.responses
                ]
            },
        }
    )
    await db.disconnect()
    return {"message": "Inspection submitted", "inspection": insp}

class AssignContractIn(BaseModel):
    contractId: str
    startDate: datetime

@router.post("/{vehicle_id}/contract")
async def assign_contract_from_template(vehicle_id: str, data: AssignContractIn, user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    template = await db.maintenancecontract.find_unique(where={"id": data.contractId})
    if not template:
        raise HTTPException(404, detail="Contract not found")

    end = data.startDate + timedelta(days=template.durationMonths * 30)
    vc = await db.vehiclecontract.create(
        data={
            "contractId": data.contractId,
            "vehicleId": vehicle_id,
            "startDate": data.startDate,
            "endDate": end,
        }
    )
    await db.disconnect()
    return {"message": "Contract assigned", "contract": vc}
