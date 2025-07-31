# backend/app/purchase/routes.py
# This file contains purchase order management routes for handling approvals, rejections, and reorders.
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from datetime import timedelta, datetime
from typing import Optional
from fastapi.responses import StreamingResponse
import pandas as pd
from io import StringIO
import uuid
import os

router = APIRouter(prefix="/purchase", tags=["purchase"])


# Approve purchase order routes
@router.post("/purchase-orders/{po_id}/approve")
async def approve_purchase_order(po_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    po = await db.purchaseorder.update(
        where={"id": po_id},
        data={"status": "APPROVED", "approvedBy": user.id}
    )
    await db.disconnect()

    return {"message": "PO approved", "purchase_order": po}

class PORejection(BaseModel):
    reason: str
    
# Reject purchase order routes
@router.post("/purchase-orders/{po_id}/reject")
async def reject_po(po_id: str, data: PORejection, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    po = await db.purchaseorder.update(
        where={"id": po_id},
        data={
            "status": "REJECTED",
            "rejectionReason": data.reason
        }
    )
    await db.disconnect()
    return {"message": "PO rejected", "purchase_order": po}

class ReorderRequest(BaseModel):
    vendor: str

# Generate reorder purchase order routes
@router.post("/purchase-orders/generate-reorder")
async def generate_reorder_po(data: ReorderRequest, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    parts = await db.part.find_many(where={
        "vendor": data.vendor,
        "quantity": {"lt": {"path": ["minQty"]}}
    })

    if not parts:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="No low-stock items for this vendor")

    po = await db.purchaseorder.create({
        "status": "DRAFT",
        "vendor": data.vendor,
        "createdById": user.id,
    })

    for part in parts:
        await db.purchaseorderitem.create({
            "poId": po.id,
            "partId": part.id,
            "qty": part.maxQty - part.quantity,
            "expectedCost": part.cost,
        })

    await db.disconnect()
    return {"message": "PO created", "poId": po.id}

# when creating PO items:
eta = datetime.utcnow() + timedelta(days=part.leadTimeDays)
await db.purchaseorderitem.create({
    ...
    "expectedArrival": eta
})

# Incoming Purchase Orders
@router.get("/purchase-orders/incoming")
async def get_weekly_incoming(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    now = datetime.utcnow()
    week_later = now + timedelta(days=7)

    await db.connect()
    incoming = await db.purchaseorderitem.find_many(
        where={"expectedArrival": {"gte": now, "lte": week_later}},
        include={"part": True, "po": True}
    )
    await db.disconnect()

    return [{
        "poId": item.poId,
        "sku": item.part.sku,
        "description": item.part.description,
        "expectedArrival": item.expectedArrival
    } for item in incoming]

# Handle late purchase orders
@router.get("/purchase-orders/late")
async def get_late_pos(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    now = datetime.utcnow()

    await db.connect()
    late_items = await db.purchaseorderitem.find_many(
        where={
            "expectedArrival": {"lt": now},
            "po": {
                "status": {"not": "RECEIVED"}
            }
        },
        include={"part": True, "po": True}
    )
    await db.disconnect()

    return [{
        "poId": item.poId,
        "sku": item.part.sku,
        "expectedArrival": item.expectedArrival,
        "vendor": item.po.vendor,
        "status": item.po.status
    } for item in late_items]

class ReceiveItemRequest(BaseModel):
    qty: int

# Receive Purchase Order Item
@router.post("/purchase-orders/items/{item_id}/receive")
async def receive_po_item(item_id: str, data: ReceiveItemRequest, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    item = await db.purchaseorderitem.find_unique(where={"id": item_id}, include={"part": True})
    if not item:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="PO item not found")

    if item.receivedQty + data.qty > item.qty:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Cannot receive more than ordered")

    await db.purchaseorderitem.update(
        where={"id": item_id},
        data={
            "receivedQty": item.receivedQty + data.qty,
            "receivedAt": datetime.utcnow()
        }
    )
    # Create inventory event for receiving - Handling inventory increase, Damanged, Missmatched
    class POItemIssueReport(BaseModel):
    isDamaged: Optional[bool] = False
    isMismatched: Optional[bool] = False
    notes: Optional[str] = None

    # Increase part inventory
    await db.part.update(
        where={"id": item.partId},
        data={"quantity": item.part.quantity + data.qty}
    )
    
    if any([
    update_data.get("invoiceOverageFlag") == False,
    update_data.get("isDamaged") == False,
    update_data.get("isMismatched") == False
]):
    update_data["resolvedAt"] = datetime.utcnow()
    
    await db.disconnect()

    return {"message": f"{data.qty} units received and inventory updated"}

# Check if all PO items are fully received
items = await db.purchaseorderitem.find_many(where={"poId": item.poId})
all_received = all(i.receivedQty >= i.qty for i in items)

if all_received:
    await db.purchaseorder.update(where={"id": item.poId}, data={"status": "RECEIVED"})

# Export weekly incoming purchase orders as CSV
@router.get("/purchase-orders/incoming/export.csv")
async def export_weekly_incoming_csv(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    now = datetime.utcnow()
    week_later = now + timedelta(days=7)

    await db.connect()
    items = await db.purchaseorderitem.find_many(
        where={"expectedArrival": {"gte": now, "lte": week_later}},
        include={"part": True, "po": True}
    )
    await db.disconnect()

    data = [{
        "PO ID": item.poId,
        "SKU": item.part.sku,
        "Description": item.part.description,
        "Expected Arrival": item.expectedArrival.isoformat(),
        "Vendor": item.po.vendor
    } for item in items]

    df = pd.DataFrame(data)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    return StreamingResponse(buf, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=weekly_po_report.csv"
    })
    # Upload signature for PO item
@router.post("/purchase-orders/items/{item_id}/signature")
async def upload_po_item_signature(
    item_id: str,
    file: UploadFile = File(...),
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)

    ext = file.filename.split('.')[-1]
    fname = f"{uuid.uuid4()}.{ext}"
    path = os.path.join("/app/static/receipts", fname)

    with open(path, "wb") as f:
        f.write(await file.read())

    url = f"/static/receipts/{fname}"

    await db.connect()
    await db.purchaseorderitem.update(
        where={"id": item_id},
        data={"receivedSignatureUrl": url}
    )
    await db.disconnect()

    return {"message": "Signature uploaded", "url": url}

# Receiving Dashboard
@router.get("/purchase-orders/receiving-dashboard")
async def get_receiving_dashboard(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    items = await db.purchaseorderitem.find_many(
        where={
            "receivedQty": {"lt": {"path": ["qty"]}}
        },
        include={"part": True, "po": True}
    )
    await db.disconnect()

    return [{
        "poId": i.poId,
        "sku": i.part.sku,
        "description": i.part.description,
        "orderedQty": i.qty,
        "receivedQty": i.receivedQty,
        "expectedArrival": i.expectedArrival,
        "vendor": i.po.vendor
    } for i in items]

# Upload invoice for PO item
@router.post("/purchase-orders/items/{item_id}/invoice")
async def upload_po_invoice(item_id: str, file: UploadFile = File(...), user = Depends(get_current_user)):
    require_role(["ACCOUNTANT", "MANAGER"])(user)

    ext = file.filename.split('.')[-1]
    fname = f"{uuid.uuid4()}.{ext}"
    path = os.path.join("/app/static/invoices", fname)

    with open(path, "wb") as f:
        f.write(await file.read())

    url = f"/static/invoices/{fname}"

    await db.connect()
    await db.purchaseorderitem.update(where={"id": item_id}, data={"invoiceScanUrl": url})
    await db.disconnect()

    return {"message": "Invoice attached", "url": url}

# Export Purchase Order as PDF
@router.get("/purchase-orders/{id}/export.pdf")
async def export_po_pdf(id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN", "ACCOUNTANT"])(user)
    await db.connect()
    po = await db.purchaseorder.find_unique(
        where={"id": id},
        include={"items": {"include": {"part": True}}}
    )
    await db.disconnect()

    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    # Generate HTML
    html = f"""
    <h1>Purchase Order #{po.id}</h1>
    <p>Vendor: {po.vendor}</p>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th>SKU</th><th>Description</th><th>Ordered</th><th>Received</th><th>ETA</th><th>Signature</th>
        </tr>
        {''.join(f"<tr><td>{i.part.sku}</td><td>{i.part.description}</td><td>{i.qty}</td><td>{i.receivedQty}</td><td>{i.expectedArrival}</td><td>{'<img src=' + i.receivedSignatureUrl + ' width=100>' if i.receivedSignatureUrl else ''}</td></tr>" for i in po.items)}
    </table>
    """
    def render_row(item):
    mismatch = item.receivedQty != item.qty or item.isMismatched or item.isDamaged
    style = ' style="background-color:#ffe6e6;"' if mismatch else ''
    return f"""
    <tr{style}>
        <td>{item.part.sku}</td>
        <td>{item.part.description}</td>
        <td>{item.qty}</td>
        <td>{item.receivedQty}</td>
        <td>{item.expectedArrival}</td>
        <td>{'⚠️' if mismatch else ''}</td>
    </tr>
    """

html_rows = ''.join(render_row(i) for i in po.items)


    # Convert to PDF
    from weasyprint import HTML
    pdf = HTML(string=html).write_pdf()

    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=PO_{po.id}.pdf"
    })


# Report issue with PO item
@router.put("/purchase-orders/items/{item_id}/report-issue")
async def report_po_item_issue(item_id: str, data: POItemIssueReport, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    await db.purchaseorderitem.update(where={"id": item_id}, data=data.dict(exclude_unset=True))
    await db.disconnect()
    return {"message": "PO item issue recorded"}

await db.expense.create({
    "vendor": item.po.vendor,
    "amount": item.expectedCost * data.qty,
    "category": "Inventory",
    "poItemId": item.id
})

# filter PO Issues
@router.get("/purchase-orders/issues")
async def get_po_issues(
    damaged: Optional[bool] = None,
    mismatched: Optional[bool] = None,
    vendor: Optional[str] = None,
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)

    filters = {}
    if damaged is not None:
        filters["isDamaged"] = damaged
    if mismatched is not None:
        filters["isMismatched"] = mismatched
    if vendor:
        filters["po"] = {"vendor": vendor}

    await db.connect()
    items = await db.purchaseorderitem.find_many(
        where=filters,
        include={"part": True, "po": True}
    )
    await db.disconnect()

    return [{
        "poId": i.poId,
        "sku": i.part.sku,
        "description": i.part.description,
        "issue": {
            "damaged": i.isDamaged,
            "mismatched": i.isMismatched,
            "notes": i.notes
        },
        "vendor": i.po.vendor
    } for i in items]

# Vendor Expenses Report Monthly
@router.get("/reports/vendor-expenses")
async def vendor_expenses(
    vendor: Optional[str] = None,
    user = Depends(get_current_user)
):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    filters = {}
    if vendor:
        filters["vendor"] = vendor

    await db.connect()
    expenses = await db.expense.find_many(where=filters)
    await db.disconnect()

    from collections import defaultdict
    from datetime import datetime

    report = defaultdict(float)
    for e in expenses:
        key = f"{e.vendor} - {e.createdAt.year}-{e.createdAt.month:02d}"
        report[key] += e.amount

    return [{"vendor_month": k, "total": round(v, 2)} for k, v in report.items()]

class InvoiceMatchRequest(BaseModel):
    scannedTotal: float

# Match Invoice Total with PO Item
@router.post("/purchase-orders/items/{item_id}/match-invoice")
async def match_invoice_total(item_id: str, data: InvoiceMatchRequest, user = Depends(get_current_user)):
    require_role(["ACCOUNTANT", "MANAGER"])(user)

    await db.connect()
    item = await db.purchaseorderitem.find_unique(where={"id": item_id})
    await db.disconnect()

    expected_total = item.expectedCost * item.qty
    diff = abs(expected_total - data.scannedTotal)

    return {
        "expected": expected_total,
        "scanned": data.scannedTotal,
        "difference": round(diff, 2),
        "match": diff < 0.01
    }

@router.post("/purchase-orders/items/{item_id}/match-invoice")
async def match_invoice_total(item_id: str, data: InvoiceMatchRequest, user = Depends(get_current_user)):
    ...
    tolerance = expected_total * 0.01
    overage_flag = diff > tolerance

    await db.connect()
    await db.purchaseorderitem.update(
        where={"id": item_id},
        data={"invoiceOverageFlag": overage_flag}
    )
    await db.disconnect()

    return {
        "expected": expected_total,
        "scanned": data.scannedTotal,
        "difference": round(diff, 2),
        "match": not overage_flag
    }

@router.get("/purchase-orders/issues/dashboard")
async def po_issue_dashboard(
    status: Optional[str] = None,  # "open", "resolved", "overdue"
    sla_days: int = 3,
    user = Depends(get_current_user)
):
    require_role(["ADMIN", "MANAGER", "ACCOUNTANT"])(user)

    await db.connect()
    items = await db.purchaseorderitem.find_many(
        where={
            "OR": [
                {"invoiceOverageFlag": True},
                {"isDamaged": True},
                {"isMismatched": True}
            ]
        },
        include={"part": True, "po": True}
    )
    await db.disconnect()

    now = datetime.utcnow()
    filtered = []

    for i in items:
        is_open = not i.resolvedAt
        overdue = is_open and i.flaggedAt and (now - i.flaggedAt).days > sla_days

        if status == "open" and is_open:
            filtered.append(i)
        elif status == "resolved" and not is_open:
            filtered.append(i)
        elif status == "overdue" and overdue:
            filtered.append(i)
        elif not status:
            filtered.append(i)

    return [{
        "poId": i.poId,
        "sku": i.part.sku,
        "vendor": i.po.vendor,
        "flaggedAt": i.flaggedAt,
        "resolvedAt": i.resolvedAt,
        "issue": {
            "damaged": i.isDamaged,
            "mismatched": i.isMismatched,
            "invoiceMismatch": i.invoiceOverageFlag
        },
        "overdue": (not i.resolvedAt and i.flaggedAt and (now - i.flaggedAt).days > sla_days)
    } for i in filtered]

is_late = data.received_date > item.expectedArrival
await db.purchaseorderitem.update(
    where={"id": item_id},
    data={
        "deliveredAt": data.received_date,
        "wasLate": is_late
    }
)


@router.post("/purchase-orders/manual")
async def create_po_with_override(
    data: CreatePORequest,
    override: bool = False,
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)

    vendor = await db.vendor.find_unique(where={"name": data.vendor})
    if vendor.rating < MIN_VENDOR_RATING and not override:
        raise HTTPException(400, detail="Vendor rating below minimum threshold. Use override=True to proceed.")

    if vendor.rating < MIN_VENDOR_RATING and override:
        await db.auditlog.create({
            "action": "PO_OVERRIDE",
            "details": f"Vendor: {vendor.name}, Rating: {vendor.rating}",
            "userId": user.id
        })

    # Proceed with PO creation...


@router.post("/purchase-orders/generate")
async def generate_purchase_order(vendor: str, user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    low_stock_parts = await db.part.find_many(
        where={"quantityOnHand": {"lte": "minThreshold"}, "vendor": vendor}
    )

    if not low_stock_parts:
        raise HTTPException(404, detail="No low stock items for vendor")

    po = await db.purchaseorder.create(data={"vendor": vendor})
    for part in low_stock_parts:
        await db.poitem.create(data={
            "purchaseOrderId": po.id,
            "sku": part.sku,
            "description": part.description,
            "quantity": part.reorderQty or 10
        })

    await db.disconnect()
    return {"message": "PO created", "id": po.id}

import httpx

class ItemIn(BaseModel):
    sku: str
    quantity: int

@router.post("/inventory/purchase-orders")
async def create_po(vendor: str, items: list[ItemIn], user=Depends(get_current_user)):
    require_role(["INVENTORY", "ADMIN"])(user)

    await db.connect()
    po = await db.purchaseorder.create(data={
        "vendor": vendor,
        "items": {"create": [item.dict() for item in items]}
    })
    await db.disconnect()
    return {"message": "PO created", "po": po}

@router.post("/inventory/receive/{po_id}")
async def receive_po(po_id: str, user=Depends(get_current_user)):
    require_role(["INVENTORY", "ADMIN"])(user)

    await db.connect()
    po = await db.purchaseorder.find_unique(where={"id": po_id}, include={"items": True})
    for item in po.items:
        await db.part.update_many(
            where={"sku": item.sku},
            data={"quantity": {"increment": item.quantity}}
        )
        await db.purchaseitem.update(
            where={"id": item.id},
            data={"received": item.quantity}
        )
    await db.purchaseorder.update(where={"id": po_id}, data={"status": "RECEIVED"})
    await db.disconnect()
    return {"message": "Stock received"}
