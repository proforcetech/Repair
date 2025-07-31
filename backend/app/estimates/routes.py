# File: backend/app/estimates/routes.py
# This file contains routes for managing estimates, including creating, updating, and retrieving estimates.
# It uses FastAPI's dependency injection system to handle authentication and authorization.
# It includes endpoints for creating estimates, adding items, updating status, and converting estimates to repair orders.
# It also supports templates for job cards and allows applying service packages to estimates.
# The routes are designed to be used by technicians, service writers, and managers.
# It connects to a Prisma database client to perform CRUD operations on estimates and related entities.
# The routes are organized under the "/estimates" prefix and tagged for easy identification in API documentation.
# It includes error handling for unauthorized access and invalid operations.
# The routes are designed to be efficient and follow best practices for RESTful API design.

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from typing import List, Optional
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db

router = APIRouter(prefix="/estimates", tags=["estimates"])

# --- Dependency to manage DB connection ---
async def get_db():
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()


# --- Pydantic schemas ---
class EstimateItemCreate(BaseModel):
    description: str
    cost: float
    part_id: Optional[str] = None
    qty: Optional[int] = None


class EstimateCreate(BaseModel):
    vehicle_id: str
    items: List[EstimateItemCreate]


class JobCardItemCreate(BaseModel):
    description: str
    labor_hours: float
    parts_cost: float


class TemplateCreate(BaseModel):
    label: str
    items: List[JobCardItemCreate]


# --- Helpers ---
async def get_estimate_or_403(estimate_id: str, user, db):
    est = await db.estimate.find_unique(
        where={"id": estimate_id}, include={"items": True}
    )
    if not est or est.customerId != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return est


# --- Routes ---

@router.post("/", response_model=None)
async def create_estimate(
    data: EstimateCreate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    total = sum(item.cost for item in data.items)
    estimate = await db.estimate.create(
        data={
            "vehicleId": data.vehicle_id,
            "customerId": user.id,
            "total": total,
            "items": {
                "create": [
                    item.dict(exclude_none=True, by_alias=True)
                    for item in data.items
                ]
            },
        }
    )
    return estimate


@router.get("/{estimate_id}", response_model=None)
async def get_estimate(
    estimate_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    return await get_estimate_or_403(estimate_id, user, db)


@router.post("/{estimate_id}/items", response_model=None)
async def add_item(
    estimate_id: str,
    item: EstimateItemCreate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    est = await get_estimate_or_403(estimate_id, user, db)
    new_item = await db.estimateitem.create(
        data={
            "estimateId": estimate_id,
            "description": item.description,
            "cost": item.cost,
            **(
                {"partId": item.part_id, "qty": item.qty}
                if item.part_id
                else {}
            ),
        }
    )
    # Update the estimate total
    await db.estimate.update(
        where={"id": estimate_id}, data={"total": est.total + item.cost}
    )
    return new_item


@router.put("/{estimate_id}/status", response_model=None)
async def update_status(
    estimate_id: str,
    status: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    valid = {
        "APPROVED",
        "REJECTED",
        "PENDING_CUSTOMER_APPROVAL",
    }
    status_upper = status.upper()
    if status_upper not in valid:
        raise HTTPException(status_code=400, detail="Invalid status")
    await get_estimate_or_403(estimate_id, user, db)
    updated = await db.estimate.update(
        where={"id": estimate_id}, data={"status": status_upper}
    )
    return {"message": f"Estimate {status_upper.lower()}", "estimate": updated}


@router.put("/{estimate_id}/approve", response_model=None)
async def approve_estimate(
    estimate_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    await require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)
    updated = await db.estimate.update(
        where={"id": estimate_id}, data={"status": "APPROVED"}
    )
    return {"message": "Estimate approved", "estimate": updated}


@router.put("/{estimate_id}/reject", response_model=None)
async def reject_estimate(
    estimate_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    await require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)
    updated = await db.estimate.update(
        where={"id": estimate_id}, data={"status": "REJECTED"}
    )
    return {"message": "Estimate rejected", "estimate": updated}


@router.post("/{estimate_id}/duplicate", response_model=None)
async def duplicate_estimate(
    estimate_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    est = await get_estimate_or_403(estimate_id, user, db)
    new_est = await db.estimate.create(
        data={
            "customerId": est.customerId,
            "vehicleId": est.vehicleId,
            "status": "DRAFT",
            "total": est.total,
            "items": {
                "create": [
                    {"description": i.description, "cost": i.cost}
                    for i in est.items
                ]
            },
        }
    )
    return {"message": "Estimate duplicated", "estimate": new_est}


@router.post("/{estimate_id}/convert", response_model=None)
async def convert_estimate_to_repair_order(
    estimate_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    await require_role(["MANAGER", "ADMIN"])(user)
    est = await db.estimate.find_unique(where={"id": estimate_id})
    if not est or est.status != "APPROVED":
        raise HTTPException(
            status_code=400, detail="Estimate not approved or not found"
        )
    repair_order = await db.repairorder.create(
        data={
            "customerId": est.customerId,
            "vehicleId": est.vehicleId,
            "notes": f"Auto-generated from Estimate {estimate_id}",
        }
    )
    return {"message": "Estimate converted", "repair_order": repair_order}


@router.post("/templates", response_model=None)
async def create_template(
    data: TemplateCreate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    await require_role(["MANAGER", "ADMIN"])(user)
    template = await db.jobcardtemplate.create(
        data={
            "label": data.label,
            "items": {"create": [item.dict() for item in data.items]},
        }
    )
    return template


@router.post("/{estimate_id}/apply-template/{template_id}", response_model=None)
async def apply_template_to_estimate(
    estimate_id: str,
    template_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    await require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)
    template = await db.jobcardtemplate.find_unique(
        where={"id": template_id}, include={"items": True}
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.jobcard.create(
        data={
            "label": template.label,
            "estimateId": estimate_id,
            "items": {
                "create": [
                    {
                        "description": item.description,
                        "laborHours": item.labor_hours,
                        "partsCost": item.parts_cost,
                    }
                    for item in template.items
                ]
            },
        }
    )
    return {"message": "Template applied"}


@router.put("/{estimate_id}/set-expiry", response_model=None)
async def set_estimate_expiry(
    estimate_id: str,
    days: int = 7,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    await require_role(["MANAGER", "ADMIN"])(user)
    expire_at = datetime.utcnow() + timedelta(days=days)
    await db.estimate.update(
        where={"id": estimate_id}, data={"expiresAt": expire_at}
    )
    return {
        "message": f"Estimate will expire on {expire_at.date().isoformat()}"
    }


@router.put("/{estimate_id}/add-package", response_model=None)
async def add_package(
    estimate_id: str,
    package_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    await require_role(["SERVICE_WRITER", "MANAGER"])(user)
    package = await db.servicepackage.find_unique(
        where={"id": package_id}, include={"items": True}
    )
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    # (Omitted: logic to merge package.items into the estimate)
    await db.estimate.update(
        where={"id": estimate_id}, data={"servicePackageId": package_id}
    )
    return {"message": "Package applied"}
