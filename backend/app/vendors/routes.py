# File: backend/app/vendors/routes.py
# This file contains routes for managing vendor-related operations, including purchase orders, vendor scorecards,
# and vendor quality monitoring.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from datetime import datetime, timedelta
from typing import Optional
from fastapi.responses import StreamingResponse
from io import StringIO
from app.core.email import send_email
import httpx

router = APIRouter(prefix="/vendors", tags=["vendors"])

@router.get("/vendors/flag-alerts")
async def vendor_flag_monitor(min_flags: int = 3, months: int = 3, user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    cutoff = datetime.utcnow() - timedelta(days=30 * months)
    await db.connect()
    flagged = await db.purchaseorderitem.find_many(
        where={
            "OR": [
                {"isDamaged": True},
                {"isMismatched": True},
                {"invoiceOverageFlag": True}
            ],
            "createdAt": {"gte": cutoff}
        },
        include={"po": True}
    )
    await db.disconnect()

    from collections import Counter
    vendor_counts = Counter(i.po.vendor for i in flagged)
    notified = []

    for vendor, count in vendor_counts.items():
        if count >= min_flags:
            await send_email(
                to=f"{vendor.lower()}@vendor.com",
                subject="⚠️ Repeated PO Quality Issues",
                body=f"Dear {vendor},\n\nWe've observed {count} flagged PO issues in the past {months} months. Please investigate and improve QC."
            )
            notified.append({"vendor": vendor, "flagged": count})

    return notified

@router.get("/vendors/scorecards")
async def vendor_scorecard(months: int = 3, user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "ACCOUNTANT"])(user)

    cutoff = datetime.utcnow() - timedelta(days=30 * months)
    await db.connect()
    items = await db.purchaseorderitem.find_many(
        where={"createdAt": {"gte": cutoff}},
        include={"po": True}
    )
    await db.disconnect()

    from collections import defaultdict
    metrics = defaultdict(lambda: {"total": 0, "flagged": 0, "avg_resolution_days": []})

    for i in items:
        v = i.po.vendor
        metrics[v]["total"] += 1
        if i.isDamaged or i.isMismatched or i.invoiceOverageFlag:
            metrics[v]["flagged"] += 1
        if i.flaggedAt and i.resolvedAt:
            days = (i.resolvedAt - i.flaggedAt).total_seconds() / 86400
            metrics[v]["avg_resolution_days"].append(days)

    return [{
        "vendor": v,
        "total_orders": d["total"],
        "flagged_orders": d["flagged"],
        "flag_rate_pct": round(d["flagged"] / d["total"] * 100, 2) if d["total"] else 0,
        "avg_resolution_days": round(sum(d["avg_resolution_days"]) / len(d["avg_resolution_days"]), 2) if d["avg_resolution_days"] else None
    } for v, d in metrics.items()]

@router.get("/vendor/scorecard")
async def vendor_self_scorecard(user = Depends(get_current_user)):
    if user.role != "VENDOR":
        raise HTTPException(status_code=403, detail="Access denied")

    vendor = user.email.split("@")[0].capitalize()  # or stored in DB

    cutoff = datetime.utcnow() - timedelta(days=90)
    await db.connect()
    items = await db.purchaseorderitem.find_many(
        where={
            "createdAt": {"gte": cutoff},
            "po": {"vendor": vendor}
        },
        include={"po": True}
    )
    await db.disconnect()

    flagged = [i for i in items if i.isDamaged or i.isMismatched or i.invoiceOverageFlag]
    durations = [
        (i.resolvedAt - i.flaggedAt).total_seconds() / 86400
        for i in flagged if i.flaggedAt and i.resolvedAt
    ]

    return {
        "vendor": vendor,
        "total_orders": len(items),
        "flagged_orders": len(flagged),
        "flag_rate": round(len(flagged) / len(items) * 100, 2) if items else 0,
        "avg_resolution_days": round(sum(durations)/len(durations), 2) if durations else None,
        "flagged_po_items": [{
            "poId": i.poId,
            "description": i.part.description,
            "issue": {
                "damaged": i.isDamaged,
                "mismatched": i.isMismatched,
                "invoice": i.invoiceOverageFlag
            }
        } for i in flagged]
    }


def get_vendor_tier(rating: float) -> str:
    if rating >= 90:
        return "Gold"
    elif rating >= 75:
        return "Silver"
    elif rating >= 60:
        return "Bronze"
    return "Restricted"

def tier_color(tier):
    return {
        "Gold": "#ffd700",
        "Silver": "#c0c0c0",
        "Bronze": "#cd7f32",
        "Restricted": "#ff4d4d"
    }.get(tier, "#000")


@router.get("/vendors/{vendor}/scorecard.pdf")
async def export_vendor_scorecard_pdf(vendor: str, user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "ACCOUNTANT"])(user)

    cutoff = datetime.utcnow() - timedelta(days=90)

    await db.connect()
    items = await db.purchaseorderitem.find_many(
        where={
            "createdAt": {"gte": cutoff},
            "po": {"vendor": vendor}
        },
        include={"po": True}
    )
    await db.disconnect()

    total = len(items)
    flagged = sum(1 for i in items if i.isDamaged or i.isMismatched or i.invoiceOverageFlag)
    resolutions = [
        (i.resolvedAt - i.flaggedAt).total_seconds() / 86400
        for i in items if i.flaggedAt and i.resolvedAt
    ]

    tier = get_vendor_tier(vendor.rating)

html = f"""
<style>
  body {{ font-family: Arial; }}
  h1 {{ color: {tier_color(tier)}; }}
</style>
<h1>Vendor Scorecard: {vendor.name}</h1>
<p><strong>Tier:</strong> {tier}</p>
    <h1>Vendor Scorecard: {vendor}</h1>
    <p>Reporting Period: Last 90 days</p>
    <ul>
        <li>Total POs: {total}</li>
        <li>Flagged POs: {flagged}</li>
        <li>Flag Rate: {round(flagged / total * 100, 2) if total else 0}%</li>
        <li>Avg Resolution Time: {round(sum(resolutions)/len(resolutions),2) if resolutions else 'N/A'} days</li>
    </ul>
    """

    from weasyprint import HTML
    pdf = HTML(string=html).write_pdf()

    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename={vendor}_scorecard.pdf"
    })

await db.vendorratinghistory.create({
    "vendorId": vendor.id,
    "rating": score,
})

@router.get("/vendors/{vendor_id}/rating-history")
async def get_rating_history(vendor_id: str, user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    history = await db.vendorratinghistory.find_many(
        where={"vendorId": vendor_id},
        order={"timestamp": "asc"}
    )
    await db.disconnect()

    return [{"date": h.timestamp, "rating": h.rating} for h in history]

MIN_VENDOR_RATING = 70.0

eligible_vendors = await db.vendor.find_many(where={"rating": {"gte": MIN_VENDOR_RATING}})

if not eligible_vendors:
    raise HTTPException(400, detail="No vendors meet the minimum quality threshold")

# Assign top-rated vendor or prompt for manual selection

def get_vendor_tier(rating: float) -> str:
    if rating >= 90:
        return "Gold"
    elif rating >= 75:
        return "Silver"
    elif rating >= 60:
        return "Bronze"
    return "Restricted"

@router.get("/vendors")
async def list_vendors(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    vendors = await db.vendor.find_many()
    await db.disconnect()

    return [{
        "name": v.name,
        "rating": v.rating,
        "tier": get_vendor_tier(v.rating)
    } for v in vendors]
    
    
 @router.get("/vendors/leaderboard")
async def vendor_leaderboard(user = Depends(get_current_user), days: int = 90):
    require_role(["ADMIN", "MANAGER"])(user)

    cutoff = datetime.utcnow() - timedelta(days=days)
    ...
    items = await db.purchaseorderitem.find_many(
        where={
            "deliveredAt": {"not": None},
            "createdAt": {"gte": cutoff}
        },
        include={"po": True}
    )


@router.get("/vendors/leaderboard/export.csv")
async def export_leaderboard_csv(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    leaderboard = await vendor_leaderboard(user)

    df = pd.DataFrame(leaderboard)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vendor_leaderboard.csv"}
    )

@router.get("/vendors/leaderboard/export.pdf")
async def export_leaderboard_pdf(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    leaderboard = await vendor_leaderboard(user)

    rows = ''.join(
        f"<tr><td>{v['vendor']}</td><td>{v['tier']}</td><td>{v['rating']}</td><td>{v['on_time_pct']}%</td></tr>"
        for v in leaderboard
    )

    html = f"""
    <h1>Vendor Leaderboard</h1>
    <table border="1" cellpadding="5" cellspacing="0">
        <thead><tr><th>Vendor</th><th>Tier</th><th>Rating</th><th>On-Time %</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """

    from weasyprint import HTML
    pdf = HTML(string=html).write_pdf()

    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=vendor_leaderboard.pdf"}
    )

@router.post("/vendors/")
async def create_vendor(data: VendorCreate):
    await db.connect()
    vendor = await db.vendor.create(data=data.dict())
    await db.disconnect()
    return vendor

@router.post("/vendor-bills/")
async def add_bill(data: VendorBillCreate):
    await db.connect()
    bill = await db.vendorbill.create(data=data.dict())
    await db.disconnect()
    return bill
@router.get("/vendor-bills")
async def list_vendor_bills(paid: Optional[bool] = None, user=Depends(get_current_user)):
    await db.connect()
    filters = {"paid": paid} if paid is not None else {}
    bills = await db.vendorbill.find_many(
        where=filters,
        include={"vendor": True}
    )
    await db.disconnect()
    return [
        {
            "id": bill.id,
            "vendor": bill.vendor.name,
            "description": bill.description,
            "amount": bill.amount,
            "dueDate": bill.dueDate,
            "paid": bill.paid
        } for bill in bills
    ]

@router.put("/vendor-bills/{bill_id}/recurring")
async def set_bill_recurring(bill_id: str, is_recurring: bool, recurrence: Optional[str] = None, user=Depends(get_current_user)):
    await db.connect()
    bill = await db.vendorbill.update(
        where={"id": bill_id},
        data={"isRecurring": is_recurring, "recurrence": recurrence}
    )
    await db.disconnect()
    return {"message": "Updated recurrence", "bill": bill}

@router.put("/vendor-bills/{bill_id}/category")
async def assign_category(bill_id: str, category: str, user=Depends(get_current_user)):
    await db.connect()
    bill = await db.vendorbill.update(
        where={"id": bill_id},
        data={"category": category.upper()}
    )
    await db.disconnect()
    return {"message": "Category assigned", "bill": bill}

from fastapi import UploadFile, File
import shutil
import uuid

@router.post("/vendor-bills/{bill_id}/upload")
async def upload_bill_doc(bill_id: str, file: UploadFile = File(...)):
    filename = f"{uuid.uuid4()}_{file.filename}"
    path = f"uploads/bills/{filename}"
    with open(path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    await db.connect()
    bill = await db.vendorbill.update(where={"id": bill_id}, data={"docPath": path})
    await db.disconnect()
    return {"message": "Uploaded", "path": path}

async def get_vendor_price(sku: str, vendor: str):
    if vendor.lower() == "partstech":
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://api.partstech.com/v1/parts/{sku}", headers={"Authorization": f"Bearer {PARTSTECH_KEY}"})
            return resp.json()
    if vendor.lower() == "nexpart":
        # similar logic here with token + endpoint
        ...
    return None

@router.get("/vendors/{vendor}/parts/{sku}")
async def lookup_vendor_part(vendor: str, sku: str, user=Depends(get_current_user)):
    require_role(["MANAGER", "FRONT_DESK"])(user)

    data = await get_vendor_price(sku, vendor)
    if not data:
        raise HTTPException(404, "Part not found or vendor API error")
    return data

import pytesseract
from PIL import Image
import pdfplumber

async def extract_text_from_pdf(file_path: str) -> str:
    with pdfplumber.open(file_path) as pdf:
        pages = [page.extract_text() for page in pdf.pages]
    return "\n".join(filter(None, pages))

from fastapi import UploadFile, File

@router.post("/vendor-bills/upload")
async def upload_vendor_bill(
    file: UploadFile = File(...), user=Depends(get_current_user)
):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    file_path = f"/tmp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    text = await extract_text_from_pdf(file_path)

    await db.connect()
    record = await db.vendorbill.create(data={
        "vendor": "Unknown",
        "amount": 0,
        "category": "Uncategorized",
        "uploadedById": user.id,
        "dueDate": datetime.utcnow() + timedelta(days=30)
    })
    await db.disconnect()

    return {"id": record.id, "extractedText": text}


@router.put("/vendor-bills/{id}/tag")
async def tag_bill(id: str, tag: BillTag, user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    bill = await db.vendorbill.update(where={"id": id}, data={"jobItemId": tag.jobItemId})
    await db.disconnect()

    return {"message": "Bill tagged to job", "bill": bill}


@router.get("/bills/payables")
async def list_payables(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    unpaid = await db.vendorbill.find_many(where={"isPaid": False}, order={"dueDate": "asc"})
    await db.disconnect()
    return unpaid

@router.post("/vendor-bills/{id}/pay")
async def mark_bill_paid(id: str, user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    paid = await db.vendorbill.update(
        where={"id": id},
        data={"isPaid": True, "paidDate": datetime.utcnow()}
    )
    await db.disconnect()
    return {"message": "Bill marked as paid", "bill": paid}
