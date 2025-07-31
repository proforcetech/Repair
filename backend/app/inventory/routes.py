# backend/app/inventory/routes.py
# This file contains inventory management routes for handling parts, stock transfers, and purchase orders.

from fastapi import APIRouter, Depends, HTTPException
from app.core.notifier import send_email
from fastapi import UploadFile, File
import uuid, os
from pydantic import BaseModel
from fastapi import router
from typing import Optional

class StockTransferRequest(BaseModel):
    partId: str
    fromLocation: str
    toLocation: str
    quantity: int
    note: Optional[str] = None

APIRouter = APIRouter(prefix="/inventory", tags=["inventory"])

@router.post("/stock/transfer")
async def transfer_stock(data: StockTransferRequest, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    part = await db.part.find_unique(where={"id": data.partId})
    if not part or part.location != data.fromLocation:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Part/location mismatch")

    if part.quantity < data.quantity:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Insufficient stock")

    # Deduct from source
    await db.part.update(
        where={"id": data.partId},
        data={"quantity": part.quantity - data.quantity}
    )

    # Create or update destination
    existing = await db.part.find_first(where={
        "sku": part.sku,
        "location": data.toLocation
    })

    if existing:
        await db.part.update(
            where={"id": existing.id},
            data={"quantity": existing.quantity + data.quantity}
        )
    else:
        await db.part.create({
            "name": part.name,
            "sku": part.sku,
            "vendor": part.vendor,
            "cost": part.cost,
            "location": data.toLocation,
            "quantity": data.quantity
        })

    # Log transfer
    await db.stocktransfer.create({
        "partId": part.id,
        "fromLocation": data.fromLocation,
        "toLocation": data.toLocation,
        "quantity": data.quantity,
        "note": data.note
    })

    await db.disconnect()
    return {"message": "Transfer complete"}


@router.get("/parts")
async def list_parts(
    location: Optional[str] = None,
    user = Depends(get_current_user)
):
    await db.connect()
    if location:
        parts = await db.part.find_many(where={"location": location})
    else:
        parts = await db.part.find_many()
    await db.disconnect()
    return parts


@router.post("/purchase-orders/create")
async def create_purchase_order(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    parts = await db.part.find_many()
    vendor_groups = {}

    for part in parts:
        if part.reorderMin is not None and part.quantity < part.reorderMin:
            order_qty = part.reorderMin * 2 - part.quantity
            vendor_groups.setdefault(part.vendor, []).append({
                "partId": part.id,
                "quantity": order_qty,
                "cost": part.cost
            })

    created_pos = []
    for vendor, items in vendor_groups.items():
        po = await db.purchaseorder.create({
            "vendor": vendor,
            "items": {
                "create": items
            }
        })

        # Optional email notification (stub)
        await send_email(
            to_email=f"{vendor.lower()}@example.com",
            subject=f"New Purchase Order #{po.id}",
            body=f"PO generated for {len(items)} items. Please log in to view."
        )
        created_pos.append(po)

    await db.disconnect()
    return {"created": created_pos}


@router.post("/purchase-orders")
async def create_po(vendor: str, items: list[dict], user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    order = await db.purchaseorder.create({
        "vendor": vendor,
        "items": {
            "create": [
                {
                    "partId": item["part_id"],
                    "quantity": item["quantity"],
                    "cost": item["cost"]
                } for item in items
            ]
        }
    })
    await db.disconnect()
    return order

class PartUsageCreate(BaseModel):
    jobId: str
    partId: str
    quantity: int

@router.post("/consume")
async def consume_part(data: PartUsageCreate, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER"])(user)
    await db.connect()

    part = await db.part.find_unique(where={"id": data.partId})
    if not part or part.quantity < data.quantity:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Insufficient stock")

    # Deduct stock
    await db.part.update(
        where={"id": data.partId},
        data={"quantity": part.quantity - data.quantity}
    )

    usage = await db.partusage.create({
        "jobId": data.jobId,
        "partId": data.partId,
        "quantity": data.quantity,
        "cost": part.cost
    })

    await db.disconnect()
    return usage


@router.post("/restock-orders/generate")
async def generate_restock_order(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    parts = await db.part.find_many()

    restock_list = []
    for part in parts:
        if part.reorderMin is not None and part.quantity < part.reorderMin:
            order_qty = part.reorderMin * 2 - part.quantity  # buffer stock
            restock_list.append({
                "sku": part.sku,
                "name": part.name,
                "vendor": part.vendor,
                "quantity_to_order": order_qty
            })

    await db.disconnect()
    return {"items": restock_list}

from fastapi.responses import FileResponse
from app.core.pdf_utils import generate_po_pdf

@router.get("/purchase-orders/{po_id}/pdf")
async def download_po_pdf(po_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    po = await db.purchaseorder.find_unique(where={"id": po_id})
    items = await db.purchaseitem.find_many(where={"poId": po_id})
    await db.disconnect()

    pdf_path = generate_po_pdf(po, items)
    return FileResponse(pdf_path, filename=f"purchase_order_{po_id}.pdf")

@router.post("/purchase-orders/{po_id}/approve")
async def approve_po(po_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    po = await db.purchaseorder.find_unique(where={"id": po_id})
    if not po or po.status != "DRAFT":
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Only DRAFT POs can be approved")

    updated = await db.purchaseorder.update(
        where={"id": po_id},
        data={"status": "APPROVED", "approvedBy": user.id}
    )
    await db.disconnect()
    return {"message": "PO approved", "purchase_order": updated}

@router.post("/scan-receive")
async def scan_receive_part(sku: str, quantity: int = 1, location: Optional[str] = None, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)
    await db.connect()

    part = await db.part.find_first(where={"sku": sku, "location": location} if location else {"sku": sku})
    if not part:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Part not found for scanned SKU")

    updated = await db.part.update(
        where={"id": part.id},
        data={"quantity": part.quantity + quantity}
    )
    await db.disconnect()
    return {"message": f"Received {quantity} unit(s) of {part.name}", "part": updated}

class POStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None

@router.post("/purchase-orders/{po_id}/status")
async def update_po_status(po_id: str, data: POStatusUpdate, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    po = await db.purchaseorder.update(
        where={"id": po_id},
        data={"status": data.status}
    )

    await db.purchaseorderlog.create({
        "poId": po_id,
        "status": data.status,
        "changedBy": user.id,
        "note": data.note
    })

    await db.disconnect()
    return {"message": f"Status updated to {data.status}", "po": po}

@router.post("/scan-receive")
async def scan_receive_part(sku: str, quantity: int = 1, location: Optional[str] = None, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)
    await db.connect()

    part = await db.part.find_first(where={"sku": sku, "location": location} if location else {"sku": sku})
    if not part:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Part not found")

    updated = await db.part.update(
        where={"id": part.id},
        data={"quantity": part.quantity + quantity}
    )

    await db.inventoryevent.create({
        "partId": part.id,
        "quantity": quantity,
        "location": part.location,
        "type": "RECEIVE",
        "userId": user.id,
        "note": f"Scanned via SKU: {sku}"
    })

    await db.disconnect()
    return {"message": f"{quantity} {part.name} received", "part": updated}

@router.get("/scan-lookup")
async def scan_lookup(sku: str, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)
    await db.connect()
    part = await db.part.find_first(where={"sku": sku})
    await db.disconnect()

    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    return {
        "name": part.name,
        "sku": part.sku,
        "location": part.location,
        "quantity": part.quantity
    }

@router.get("/inventory-events")
async def list_inventory_events(
    part_id: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    sort_by: Optional[str] = "timestamp",
    descending: bool = True,
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    filters = {}
    if part_id:
        filters["partId"] = part_id
    if event_type:
        filters["type"] = event_type.upper()
    if user_id:
        filters["userId"] = user_id

    order = {sort_by: "desc" if descending else "asc"}
    events = await db.inventoryevent.find_many(where=filters, order=order)

    await db.disconnect()
    return events

@router.get("/part-requests")
async def list_part_requests(status: Optional[str] = None, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    filters = {"status": status.upper()} if status else {}
    requests = await db.partrequest.find_many(where=filters)
    await db.disconnect()
    return requests

class PartRequestUpdate(BaseModel):
    status: str  # "APPROVED", "DENIED"
    note: Optional[str] = None

@router.put("/part-requests/{request_id}")
async def update_part_request(request_id: str, data: PartRequestUpdate, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    updated = await db.partrequest.update(
        where={"id": request_id},
        data={"status": data.status.upper()}
    )
    await db.disconnect()

if data.status.upper() == "APPROVED":
    tech = await db.user.find_unique(where={"id": updated.userId})
    if tech and tech.email:
        await notify_user(
            tech.email,
            "Part Request Approved",
            f"Your request for SKU {updated.sku} has been approved."
        )

    return {"message": f"Request {data.status}", "request": updated}

    if data.status.upper() == "APPROVED":
        part = await db.part.find_first(where={"sku": updated.sku})
        if part:
            draft = await db.purchaseorder.find_first(where={
                "vendor": part.vendor,
                "status": "DRAFT"
            })

            if draft:
                await db.purchaseitem.create({
                    "poId": draft.id,
                    "partId": part.id,
                    "quantity": updated.quantity,
                    "cost": part.cost
                })
            else:
                new_po = await db.purchaseorder.create({
                    "vendor": part.vendor,
                    "status": "DRAFT",
                    "items": {
                        "create": [{
                            "partId": part.id,
                            "quantity": updated.quantity,
                            "cost": part.cost
                        }]
                    }
                })

"items": {
    "create": [{
        "partId": part.id,
        "quantity": updated.quantity,
        "cost": part.cost,
        "partRequestId": updated.id
    }]
}

class TemplateCreate(BaseModel):
    name: str
    items: list[dict]

@router.post("/request-templates")
async def create_template(data: TemplateCreate, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    template = await db.partrequesttemplate.create({
        "name": data.name,
        "createdBy": user.id,
        "items": {
            "create": data.items
        }
    })
    await db.disconnect()
    return template

@router.post("/request-templates/{template_id}/apply")
async def apply_template(template_id: str, user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()
    template = await db.partrequesttemplate.find_unique(where={"id": template_id}, include={"items": True})
    if not template:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Template not found")

    for item in template.items:
        await db.partrequest.create({
            "sku": item.sku,
            "quantity": item.quantity,
            "userId": user.id,
            "location": None
        })

    await db.disconnect()
    return {"message": f"Requested parts from template {template.name}"}

@router.get("/request-templates")
async def list_templates(
    name: Optional[str] = None,
    created_by: Optional[str] = None,
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)
    filters = {}
    if name:
        filters["name"] = {"contains": name, "mode": "insensitive"}
    if created_by:
        filters["createdBy"] = created_by

    await db.connect()
    templates = await db.partrequesttemplate.find_many(
        where=filters,
        include={"items": True}
    )
    await db.disconnect()
    return templates

class TemplateUpdate(BaseModel):
    name: Optional[str]
    items: Optional[list[dict]]  # overwrite all items

@router.put("/request-templates/{template_id}")
async def update_template(template_id: str, data: TemplateUpdate, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    if data.items is not None:
        await db.templateitem.delete_many(where={"templateId": template_id})
        for item in data.items:
            await db.templateitem.create({
                "templateId": template_id,
                "sku": item["sku"],
                "quantity": item["quantity"]
            })

    updated = await db.partrequesttemplate.update(
        where={"id": template_id},
        data={"name": data.name} if data.name else {}
    )

    await db.disconnect()
    return {"message": "Template updated", "template": updated}

@router.post("/request-templates/{template_id}/clone")
async def clone_template(template_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    original = await db.partrequesttemplate.find_unique(
        where={"id": template_id}, include={"items": True}
    )
    if not original:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Template not found")

    clone = await db.partrequesttemplate.create({
        "name": f"{original.name} (Copy)",
        "createdBy": user.id,
        "items": {
            "create": [
                {"sku": i.sku, "quantity": i.quantity}
                for i in original.items
            ]
        }
    })
    await db.disconnect()
    return {"message": "Template cloned", "template": clone}


@router.delete("/request-templates/{template_id}")
async def delete_template(template_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    await db.templateitem.delete_many(where={"templateId": template_id})
    await db.partrequesttemplate.delete(where={"id": template_id})
    await db.disconnect()
    return {"message": "Template deleted"}

@router.get("/request-templates/suggest")
async def suggest_templates(
    job_type: Optional[str] = None,
    vehicle_tag: Optional[str] = None,
    user = Depends(get_current_user)
):
    await db.connect()
    templates = await db.partrequesttemplate.find_many(
        where={
            "jobType": job_type if job_type else undefined,
            "vehicleTag": vehicle_tag if vehicle_tag else undefined
        },
        include={"items": True}
    )
    await db.disconnect()
    return templates
await db.partrequesttemplate.update(
    where={"id": template_id},
    data={"usageCount": {"increment": 1}}
)

@router.get("/request-templates/top-used")
async def get_top_templates(limit: int = 5, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    top = await db.partrequesttemplate.find_many(
        order={"usageCount": "desc"},
        take=limit
    )
    await db.disconnect()
    return top

@router.get("/substitution-causes")
async def substitution_causes(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    parts = await db.jobpart.find_many(where={"substituted": True})
    await db.disconnect()

    from collections import Counter
    sku_counts = Counter([p.originalSku for p in parts if p.originalSku])
    
    # Could be matched against historical inventory events to detect stockouts
    return [
        {"original_sku": sku, "substitution_count": count}
        for sku, count in sku_counts.items()
    ]

@router.get("/substitution-inventory-issues")
async def substitution_vs_inventory(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    parts = await db.jobpart.find_many(where={"substituted": True})
    logs = await db.inventorylog.find_many()
    await db.disconnect()

    from datetime import timedelta

    issues = []
    for p in parts:
        if not p.originalSku or not p.usedAt:
            continue
        # Check for matching inventory log snapshot before or on usedAt
        snapshot = next(
            (l for l in sorted(logs, key=lambda x: x.createdAt, reverse=True)
             if l.sku == p.originalSku and l.createdAt <= p.usedAt),
            None
        )
        if snapshot and snapshot.quantity <= 0:
            issues.append({
                "sku": p.originalSku,
                "usedAt": p.usedAt,
                "substitutedSku": p.sku,
                "availableQtyAtTime": snapshot.quantity
            })

    return {"substitution_due_to_stockout": issues}

@router.post("/auto-reorder-substituted")
async def auto_reorder_from_substitution(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    subs = await db.jobpart.find_many(where={"substituted": True})
    count = {}
    for p in subs:
        if p.originalSku:
            count[p.originalSku] = count.get(p.originalSku, 0) + 1

    reordered = []
    for sku, c in count.items():
        if c >= SUBSTITUTION_REORDER_THRESHOLD:
            await db.purchaseorder.create({
                "sku": sku,
                "quantity": 10,  # configurable default
                "status": "PENDING",
                "reason": "Auto-reorder triggered by substitution volume"
            })
            reordered.append(sku)

    await db.disconnect()
    return {"reordered_skus": reordered}

@router.get("/inventory/sku-trend/{sku}")
async def inventory_trend(sku: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    logs = await db.inventorylog.find_many(where={"sku": sku})
    await db.disconnect()

    from collections import defaultdict
    trend = defaultdict(int)
    for log in logs:
        month = log.createdAt.strftime("%Y-%m")
        trend[month] += log.quantity

    return [{"month": k, "net_change": v} for k, v in sorted(trend.items())]

@router.get("/inventory/cost-trend/{sku}")
async def part_cost_trend(sku: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    logs = await db.inventorylog.find_many(where={"sku": sku, "unitCost": {"not": None}})
    await db.disconnect()

    trend = [
        {"date": l.createdAt.strftime("%Y-%m-%d"), "cost": l.unitCost}
        for l in sorted(logs, key=lambda x: x.createdAt)
    ]

    return {"sku": sku, "cost_trend": trend}

@router.post("/inventory/restock")
async def restock_item(
    sku: str,
    quantity: int,
    unit_cost: float,
    reason: str,
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    last = await db.inventorylog.find_first(
        where={"sku": sku, "unitCost": {"not": None}},
        order={"createdAt": "desc"}
    )

    if last and unit_cost > last.unitCost * UNIT_COST_ALERT_THRESHOLD:
        await notify_user(
            email="procurement@repairshop.com",
            subject="⚠️ High Unit Cost Alert",
            body=f"{sku} restocked at ${unit_cost:.2f}, exceeding 15% above previous (${last.unitCost:.2f})"
        )

    await db.inventorylog.create({
        "sku": sku,
        "quantity": quantity,
        "unitCost": unit_cost,
        "reason": reason
    })
    await db.disconnect()

    return {"message": "Restock recorded"}

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db.prisma_client import db
from app.auth.dependencies import get_current_user, require_role

router = APIRouter()

class PartCreate(BaseModel):
    sku: str
    description: str
    cost: float
    msrp: float
    markupPct: float = 0
    vendor: str | None = None
    location: str | None = None
    quantity: int = 0

@router.post("/parts")
async def create_part(data: PartCreate, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    exists = await db.part.find_unique(where={"sku": data.sku})
    if exists:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="SKU already exists")
    part = await db.part.create(data.dict())
    await db.disconnect()
    return part

@router.get("/parts")
async def list_parts(user = Depends(get_current_user)):
    await db.connect()
    parts = await db.part.find_many()
    await db.disconnect()
    return parts

@router.post("/parts/reorder")
async def create_purchase_order(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    low_stock_parts = await db.part.find_many(where={"alert": True})
    if not low_stock_parts:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="No parts below threshold")

    po = await db.purchaseorder.create({
        "vendor": "MULTIPLE",
        "items": {
            "create": [
                {
                    "partId": p.id,
                    "qty": max(p.minQty * 2 - p.quantity, 1)
                } for p in low_stock_parts
            ]
        }
    })

    await db.disconnect()
    return po


class POStatusUpdate(BaseModel):
    status: str  # RECEIVED, CANCELED, PARTIAL
    reason: Optional[str] = None

@router.post("/purchase-orders/{id}/status")
async def update_po_status(id: str, data: POStatusUpdate, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    po = await db.purchaseorder.update(where={"id": id}, data={"status": data.status})
    await db.poauditlog.create({
        "poId": id,
        "status": data.status,
        "reason": data.reason,
        "byUserId": user.id
    })
    await db.disconnect()

    return {"message": f"PO marked as {data.status}", "po": po}

from fastapi import UploadFile, File
import csv
from io import StringIO

@router.post("/parts/import")
async def bulk_import_parts(file: UploadFile = File(...), user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    content = await file.read()
    stream = StringIO(content.decode("utf-8"))
    reader = csv.DictReader(stream)

    await db.connect()
    count = 0
    for row in reader:
        if not row.get("sku"): continue
        exists = await db.part.find_unique(where={"sku": row["sku"]})
        if exists: continue

        await db.part.create({
            "sku": row["sku"],
            "description": row["description"],
            "cost": float(row["cost"]),
            "msrp": float(row["msrp"]),
            "markupPct": float(row.get("markupPct", 0)),
            "vendor": row.get("vendor"),
            "location": row.get("location"),
            "quantity": int(row.get("quantity", 0)),
        })
        count += 1

    await db.disconnect()
    return {"imported": count}

@router.get("/parts/export.csv")
async def export_parts_csv(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    parts = await db.part.find_many()
    await db.disconnect()

    data = [{
        "SKU": p.sku,
        "Description": p.description,
        "Cost": p.cost,
        "MSRP": p.msrp,
        "Markup %": p.markupPct,
        "Vendor": p.vendor,
        "Location": p.location,
        "Qty": p.quantity
    } for p in parts]

    df = pd.DataFrame(data)
    stream = StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)
    return StreamingResponse(stream, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=parts_snapshot.csv"
    })

@router.get("/parts/lookup/{sku}")
async def lookup_part_by_sku(sku: str, user = Depends(get_current_user)):
    await db.connect()
    part = await db.part.find_unique(where={"sku": sku})
    await db.disconnect()

    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    return {
        "id": part.id,
        "description": part.description,
        "location": part.location,
        "quantity": part.quantity,
        "cost": part.cost
    }
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

def generate_barcode_image(sku: str) -> BytesIO:
    code128 = barcode.get('code128', sku, writer=ImageWriter())
    buffer = BytesIO()
    code128.write(buffer, options={"write_text": False})
    buffer.seek(0)
    return buffer

from fastapi.responses import StreamingResponse
from app.inventory.barcodes import generate_barcode_image

@router.get("/parts/{sku}/label")
async def download_part_label(sku: str, user = Depends(get_current_user)):
    await db.connect()
    part = await db.part.find_unique(where={"sku": sku})
    await db.disconnect()

    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    barcode_image = generate_barcode_image(sku)
    return StreamingResponse(barcode_image, media_type="image/png", headers={
        "Content-Disposition": f"inline; filename={sku}_barcode.png"
    })

class LocationCreate(BaseModel):
    name: str

@router.post("/locations")
async def create_location(data: LocationCreate, user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    loc = await db.partlocation.create({"name": data.name})
    await db.disconnect()
    return loc

class PartTransferRequest(BaseModel):
    partId: str
    fromId: str
    toId: str
    qty: int

@router.post("/parts/transfer")
async def transfer_part(data: PartTransferRequest, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    part = await db.part.find_unique(where={"id": data.partId})
    if not part or part.locationId != data.fromId or part.quantity < data.qty:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Invalid transfer")

    await db.part.update(where={"id": part.id}, data={
        "locationId": data.toId,
        "quantity": part.quantity - data.qty
    })

    await db.parttransfer.create({
        "partId": data.partId,
        "fromId": data.fromId,
        "toId": data.toId,
        "qty": data.qty,
        "byUserId": user.id
    })

    await db.disconnect()
    return {"message": "Transfer completed"}

from datetime import datetime

@router.get("/parts/transfers")
async def get_part_transfers(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    from_id: Optional[str] = None,
    to_id: Optional[str] = None,
    user = Depends(get_current_user)
):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()

    filters = {}
    if start:
        filters["createdAt"] = {"gte": start}
    if end:
        filters.setdefault("createdAt", {}).update({"lte": end})
    if from_id:
        filters["fromId"] = from_id
    if to_id:
        filters["toId"] = to_id

    transfers = await db.parttransfer.find_many(
        where=filters,
        include={"part": True, "from": True, "to": True}
    )
    await db.disconnect()

    return [
        {
            "timestamp": t.createdAt,
            "part": t.part.sku,
            "description": t.part.description,
            "qty": t.qty,
            "from": t.from.name,
            "to": t.to.name,
        } for t in transfers
    ]

from app.inventory.qrcodes import generate_qr_code

@router.get("/parts/{sku}/qr")
async def get_part_qr(sku: str, user = Depends(get_current_user)):
    await db.connect()
    part = await db.part.find_unique(where={"sku": sku})
    await db.disconnect()

    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    qr = generate_qr_code(sku)
    return StreamingResponse(qr, media_type="image/png", headers={
        "Content-Disposition": f"inline; filename={sku}_qr.png"
    })

@router.post("/parts/transfer/import")
async def batch_transfer(file: UploadFile = File(...), user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    content = await file.read()
    reader = csv.DictReader(StringIO(content.decode()))

    await db.connect()
    count = 0
    for row in reader:
        part = await db.part.find_unique(where={"sku": row["part_sku"]})
        from_loc = await db.partlocation.find_unique(where={"name": row["from_location"]})
        to_loc = await db.partlocation.find_unique(where={"name": row["to_location"]})
        qty = int(row["qty"])

        if part and from_loc and to_loc and part.locationId == from_loc.id and part.quantity >= qty:
            await db.part.update(where={"id": part.id}, data={
                "locationId": to_loc.id,
                "quantity": part.quantity - qty
            })

            await db.parttransfer.create({
                "partId": part.id,
                "fromId": from_loc.id,
                "toId": to_loc.id,
                "qty": qty,
                "byUserId": user.id
            })
            count += 1
    await db.disconnect()
    return {"message": f"{count} transfers completed"}

class CycleCountEntry(BaseModel):
    partId: str
    countedQty: int

@router.post("/parts/cycle-count")
async def record_cycle_count(data: list[CycleCountEntry], user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    for entry in data:
        part = await db.part.find_unique(where={"id": entry.partId})
        if not part:
            continue
        variance = entry.countedQty - part.quantity
        await db.cyclecount.create({
            "partId": part.id,
            "countedBy": user.id,
            "countedQty": entry.countedQty,
            "systemQty": part.quantity,
            "variance": variance,
            "locationId": part.locationId
        })
    await db.disconnect()
    return {"message": "Cycle counts recorded"}

from datetime import datetime, timedelta

@router.get("/parts/expiring")
async def get_expiring_parts(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    now = datetime.utcnow()
    soon = now + timedelta(days=30)

    await db.connect()
    parts = await db.part.find_many(where={
        "expiryDate": {"gte": now, "lte": soon}
    })
    expired = await db.part.find_many(where={
        "expiryDate": {"lt": now}
    })
    await db.disconnect()

    return {
        "expiring_soon": parts,
        "expired": expired
    }

@router.get("/cycle-counts/export.csv")
async def export_cycle_counts_csv(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    counts = await db.cyclecount.find_many(include={"part": True, "location": True})
    await db.disconnect()

    data = [
        {
            "Date": c.createdAt.isoformat(),
            "SKU": c.part.sku,
            "Description": c.part.description,
            "Counted": c.countedQty,
            "System Qty": c.systemQty,
            "Variance": c.variance,
            "Location": c.location.name if c.location else "N/A"
        }
        for c in counts
    ]

    df = pd.DataFrame(data)
    stream = StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)
    return StreamingResponse(stream, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=cycle_counts.csv"
    })



UPLOAD_DIR = "/app/static/cycle_photos"

@router.post("/cycle-counts/{id}/upload-photo")
async def upload_cycle_photo(id: str, file: UploadFile = File(...), user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    ext = file.filename.split(".")[-1]
    fname = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(UPLOAD_DIR, fname)

    with open(path, "wb") as f:
        f.write(await file.read())

    url = f"/static/cycle_photos/{fname}"
    await db.connect()
    await db.cyclecount.update(where={"id": id}, data={"photoUrl": url})
    await db.disconnect()

    return {"message": "Photo uploaded", "url": url}

from datetime import datetime

@router.post("/cycle-counts/{id}/approve")
async def approve_cycle_count(id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    cc = await db.cyclecount.find_unique(where={"id": id}, include={"part": True})
    if not cc or cc.approved:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Already approved or not found")

    await db.part.update(where={"id": cc.partId}, data={"quantity": cc.countedQty})
    await db.cyclecount.update(where={"id": id}, data={
        "approved": True,
        "approvedBy": user.id,
        "approvedAt": datetime.utcnow()
    })
    await db.disconnect()

    return {"message": "Cycle count approved and inventory updated"}

VARIANCE_THRESHOLD = 10
PERCENT_THRESHOLD = 0.2

variance = entry.countedQty - part.quantity
percent_diff = abs(variance) / (part.quantity or 1)

if abs(variance) > VARIANCE_THRESHOLD or percent_diff > PERCENT_THRESHOLD:
    await notify_warehouse_manager(part.sku, variance, user.email)

async def notify_warehouse_manager(sku: str, variance: int, by: str):
    subject = f"Inventory variance alert: {sku}"
    body = f"User {by} reported a variance of {variance} units for part {sku}."
    await send_email("warehouse@example.com", subject=subject, body=body)


class CycleCountEntry(BaseModel):
    partId: str
    countedQty: int
    comment: Optional[str] = None

# Inside loop in record_cycle_count:
await db.cyclecount.create({
    "partId": part.id,
    "countedBy": user.id,
    "countedQty": entry.countedQty,
    "systemQty": part.quantity,
    "variance": variance,
    "locationId": part.locationId,
    "comment": entry.comment
})

class ApprovalNote(BaseModel):
    note: Optional[str] = None

@router.post("/cycle-counts/{id}/approve")
async def approve_cycle_count(id: str, data: ApprovalNote, user = Depends(get_current_user)):
    ...
    await db.cyclecount.update(where={"id": id}, data={
        ...
        "approvalNote": data.note
    })


@router.post("/inventory-log/{id}/photo")
async def upload_adjustment_photo(id: str, file: UploadFile = File(...), user = Depends(get_current_user)):
    ext = file.filename.split(".")[-1]
    fname = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(UPLOAD_DIR, fname)

    with open(path, "wb") as f:
        f.write(await file.read())

    url = f"/static/cycle_photos/{fname}"
    await db.connect()
    await db.inventorylog.update(where={"id": id}, data={"photoUrl": url})
    await db.disconnect()

    return {"message": "Photo uploaded", "url": url}

@router.get("/inventory-log/export.csv")
async def export_inventory_log_csv(
    userId: Optional[str] = None,
    action: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    user = Depends(get_current_user)
):
    require_role(["ADMIN", "MANAGER"])(user)

    filters = {}
    if userId:
        filters["userId"] = userId
    if action:
        filters["action"] = action
    if start:
        filters["createdAt"] = {"gte": start}
    if end:
        filters.setdefault("createdAt", {}).update({"lte": end})

    await db.connect()
    logs = await db.inventorylog.find_many(
        where=filters,
        include={"part": True}
    )
    await db.disconnect()

    data = [{
        "Date": l.createdAt.isoformat(),
        "Part": l.part.sku,
        "Action": l.action,
        "Qty": l.quantity,
        "User": l.userId,
        "Reason": l.reason
    } for l in logs]

    df = pd.DataFrame(data)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    return StreamingResponse(buf, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=inventory_log.csv"
    })

@router.delete("/parts/{id}")
async def delete_part(id: str, user = Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    await db.connect()
    part = await db.part.find_unique(where={"id": id})
    if not part:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Part not found")
    if part.quantity > 0:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Cannot delete part with quantity > 0")

    await db.part.delete(where={"id": id})
    await db.disconnect()
    return {"message": "Part deleted"}

@router.get("/inventory/reorder-suggestions")
async def reorder_report(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    parts = await db.part.find_many()
    await db.disconnect()

    to_order = [
        {
            "sku": p.sku,
            "description": p.description,
            "quantity": p.quantity,
            "minQty": p.minQty,
            "maxQty": p.maxQty,
            "suggestedOrderQty": max(p.maxQty - p.quantity, 0)
        }
        for p in parts if p.quantity < p.minQty
    ]

    return {"reorder": to_order}

@router.get("/inventory/reorder-suggestions")
async def reorder_report(vendor: Optional[str] = None, user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    where = {"vendor": vendor} if vendor else {}
    parts = await db.part.find_many(where=where)
    await db.disconnect()

    to_order = [
        {
            "sku": p.sku,
            "description": p.description,
            "vendor": p.vendor,
            "quantity": p.quantity,
            "minQty": p.minQty,
            "maxQty": p.maxQty,
            "suggestedOrderQty": max(p.maxQty - p.quantity, 0)
        }
        for p in parts if p.quantity < p.minQty
    ]

    return {"reorder": to_order}

async def check_reorder_notifications():
    await db.connect()
    low_stock = await db.part.find_many(where={
        "notifyOnReorder": True,
        "quantity": {"lt": {"path": ["minQty"]}}
    })

    for part in low_stock:
        await send_email("warehouse@example.com", subject=f"Reorder Alert: {part.sku}", body=f"{part.description} is below minimum threshold.")
    await db.disconnect()

class PartUpdate(BaseModel):
    notifyOnReorder: Optional[bool] = None

@router.put("/parts/{id}")
async def update_part(id: str, data: PartUpdate, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    update_data = data.dict(exclude_unset=True)

    await db.connect()
    updated = await db.part.update(where={"id": id}, data=update_data)
    await db.disconnect()
    return {"message": "Part updated", "part": updated}

@router.get("/inventory/summary")
async def inventory_summary(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()

    parts = await db.part.find_many()
    pos = await db.purchaseorderitem.find_many(
        where={"expectedArrival": {"gte": datetime.utcnow()}},
        include={"part": True}
    )

    await db.disconnect()

    total_value = sum(p.quantity * p.cost for p in parts)
    expired = sum(1 for p in parts if p.expiryDate and p.expiryDate < datetime.utcnow())

    return {
        "total_parts": len(parts),
        "expired_parts": expired,
        "expired_pct": round((expired / len(parts)) * 100, 2) if parts else 0,
        "stock_value": round(total_value, 2),
        "reorder_frequency": sorted(
            [{"sku": p.sku, "reorderCount": p.reorderCount} for p in parts],
            key=lambda x: -x["reorderCount"]
        ),
        "incoming_pos": [
            {
                "sku": item.part.sku,
                "description": item.part.description,
                "expectedArrival": item.expectedArrival
            }
            for item in pos
        ]
    }

@router.post("/inventory/check-reorder")
async def draft_po(user=Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)

    await db.connect()
    low_stock = await db.part.find_many(
        where={"reorderMin": {"not": None}, "stock": {"lt": PrismaClient.field("reorderMin")}}
    )

    po = [
        {
            "partId": part.id,
            "name": part.name,
            "vendorId": part.vendorId,
            "neededQty": part.reorderMin - part.stock,
        }
        for part in low_stock
    ]
    await db.disconnect()
    return {"purchaseOrderDraft": po}

@router.get("/inventory/vendor-price")
async def check_vendor_price(sku: str):
    # Simulate 3rd-party response
    mock_vendor_data = {
        "sku": sku,
        "vendor": "PartsTech",
        "price": 52.99,
        "msrp": 74.99,
        "inStock": True,
        "eta": "2 days"
    }
    return mock_vendor_data


@router.post("/inventory/auto-po")
async def generate_auto_po(user=Depends(get_current_user)):
    require_role(["INVENTORY", "MANAGER"])(user)

    await db.connect()
    low_parts = await db.part.find_many(where={"quantity": {"lte": 3}})

    # Group by vendor
    grouped = {}
    for part in low_parts:
        grouped.setdefault(part.vendor, []).append(part)

    for vendor, parts in grouped.items():
        po = await db.purchaseorder.create(data={"vendor": vendor})
        for part in parts:
            await db.poitem.create(data={
                "orderId": po.id,
                "partId": part.id,
                "quantity": part.minQty * 2,
                "cost": part.cost
            })

    await db.disconnect()
    return {"message": "POs generated"}

import csv
from io import StringIO
from fastapi import UploadFile, File

@router.post("/inventory/import")
async def import_inventory(file: UploadFile = File(...), user=Depends(get_current_user)):
    require_role(["INVENTORY", "ADMIN"])(user)

    content = (await file.read()).decode()
    reader = csv.DictReader(StringIO(content))

    await db.connect()
    for row in reader:
        await db.part.upsert(
            where={"sku": row["sku"]},
            update={
                "name": row["name"],
                "cost": float(row["cost"]),
                "msrp": float(row["msrp"]),
                "vendor": row["vendor"],
                "location": row["location"],
                "quantity": int(row["quantity"])
            },
            create={
                "sku": row["sku"],
                "name": row["name"],
                "cost": float(row["cost"]),
                "msrp": float(row["msrp"]),
                "vendor": row["vendor"],
                "location": row["location"],
                "quantity": int(row["quantity"])
            }
        )
    await db.disconnect()
    return {"message": "Inventory imported successfully"}
