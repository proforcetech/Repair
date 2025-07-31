# File: backend/app/expenses/routes.py
# This file contains routes for managing expenses, vendor invoices, and bills.
# It uses FastAPI's dependency injection system to handle authentication and authorization.
# It includes endpoints for adding expenses, recording vendor invoices, uploading invoice scans,
# and generating recurring expenses and bills.

from io import BytesIO, StringIO
from datetime import datetime, timedelta
from typing import List, Optional
from dateutil.relativedelta import relativedelta
import uuid, os
import pandas as pd
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from app.core.notifier import send_email

router = APIRouter(prefix="/expenses", tags=["expenses"])


# ——— Shared dependency to manage DB connections ———
async def get_db():
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()


# ——— Pydantic schemas ———

class ExpenseCreate(BaseModel):
    vendor: str
    category: str
    amount: float
    recurring: bool = False
    recurrence: Optional[str] = None


class VendorInvoiceCreate(BaseModel):
    vendor: str
    amount: float
    parts: Optional[str] = None
    poId: Optional[str] = None
    receivedAt: datetime


class VendorInvoiceItemInput(BaseModel):
    partId: str
    qty: int
    costPerUnit: float


class VendorInvoiceCreateFull(BaseModel):
    vendor: str
    receivedAt: datetime
    items: List[VendorInvoiceItemInput]


class BillCreate(BaseModel):
    vendor: str
    category: str
    amount: float
    postedAt: Optional[datetime] = None
    dueDate: Optional[datetime] = None
    recurringId: Optional[str] = None


# ——— Routes ———

@router.post("/", response_model=None)
async def add_expense(
    data: ExpenseCreate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    exp = await db.expense.create(data=data.dict())
    return exp


@router.get("/", response_model=None)
async def list_expenses(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    expenses = await db.expense.find_many()
    return expenses


@router.post("/vendor-invoices", response_model=None)
async def record_invoice(
    data: VendorInvoiceCreate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["MANAGER", "ADMIN", "ACCOUNTANT"])(user)
    invoice = await db.vendorinvoice.create(data=data.dict())
    return invoice


@router.post("/vendor-invoices/full", response_model=None)
async def record_invoice_full(
    data: VendorInvoiceCreateFull,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["MANAGER", "ADMIN", "ACCOUNTANT"])(user)

    total_amount = sum(i.qty * i.costPerUnit for i in data.items)
    invoice = await db.vendorinvoice.create(
        data={
            "vendor": data.vendor,
            "amount": total_amount,
            "receivedAt": data.receivedAt,
        }
    )

    for item in data.items:
        # 1) record each line
        await db.vendorinvoiceitem.create(
            data={
                "invoiceId": invoice.id,
                "partId": item.partId,
                "qty": item.qty,
                "costPerUnit": item.costPerUnit,
            }
        )
        # 2) update inventory avg cost
        part = await db.part.find_unique(where={"id": item.partId})
        new_qty = part.quantity + item.qty
        new_cost = (
            (part.quantity * part.cost)
            + (item.qty * item.costPerUnit)
        ) / new_qty
        await db.part.update(
            where={"id": item.partId},
            data={"quantity": new_qty, "cost": round(new_cost, 2)},
        )
        # 3) check PO‐variance if applicable
        if data.poId:
            po_item = await db.purchaseorderitem.find_first(
                where={
                    "poId": data.poId,
                    "partId": item.partId
                }
            )
            if po_item:
                variance = item.costPerUnit - po_item.expectedCost
                if abs(variance) > 0.01:
                    # notify or log variance
                    await send_email(
                        subject=f"Cost variance on {item.partId}",
                        body=f"Variance: {variance:.2f}"
                    )

    return {
        "message": "Invoice recorded and part costs updated",
        "invoiceId": invoice.id,
    }


@router.post("/{expense_id}/invoice", response_model=None)
async def upload_expense_invoice(
    expense_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    # save locally (swap for S3, etc.)
    upload_dir = os.getenv("INVOICE_UPLOAD_DIR", "/tmp")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(upload_dir, filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    url = f"/invoices/{filename}"

    await db.expense.update(
        where={"id": expense_id},
        data={"invoiceFileUrl": url, "uploadedById": user.id}
    )
    return {"message": "Invoice uploaded", "url": url}


@router.get("/{expense_id}", response_model=None)
async def get_expense(
    expense_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["ACCOUNTANT", "ADMIN"])(user)
    exp = await db.expense.find_unique(
        where={"id": expense_id},
        include={"uploadedBy": True}
    )
    if not exp:
        raise HTTPException(404, "Expense not found")

    return {
        "id": exp.id,
        "amount": exp.amount,
        "vendor": exp.vendor,
        "invoice": exp.invoiceFileUrl,
        "uploadedBy": exp.uploadedBy.email if exp.uploadedBy else None,
        "uploadedAt": exp.createdAt,
    }


@router.get("/purchase-orders/flagged/export.csv", response_model=None)
async def export_flagged_po_items(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["ACCOUNTANT", "ADMIN"])(user)
    items = await db.purchaseorderitem.find_many(
        where={"invoiceOverageFlag": True},
        include={"part": True, "po": True}
    )

    data = [{
        "PO ID": i.poId,
        "SKU": i.part.sku,
        "Description": i.part.description,
        "Vendor": i.po.vendor,
        "Expected": i.expectedCost * i.qty,
        "Status": i.po.status,
        "ETA": i.expectedArrival,
    } for i in items]

    df = pd.DataFrame(data)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=flagged_po_items.csv"
        }
    )


@router.post("/bills", response_model=None)
async def create_bill(
    data: BillCreate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    bill = await db.bill.create(data=data.dict())
    return bill


@router.get("/bills", response_model=None)
async def list_bills(
    category: Optional[str] = None,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    where = {"category": category} if category else {}
    bills = await db.bill.find_many(where=where, order={"postedAt": "desc"})
    return bills


@router.post("/bills/recurring/run", response_model=None)
async def generate_recurring_bills(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    now = datetime.utcnow()
    recurs = await db.recurringbill.find_many(where={"nextRun": {"lte": now}})
    for r in recurs:
        await db.bill.create(data={
            "vendorId": r.vendorId,
            "amount": r.amount,
            "category": r.category,
            "postedAt": now,
            "dueDate": now + timedelta(days=30),
            "recurringId": r.id
        })
        next_run = now + timedelta(days=30 if r.frequency == "MONTHLY" else 7)
        await db.recurringbill.update(
            where={"id": r.id}, data={"nextRun": next_run}
        )
    return {"message": f"{len(recurs)} recurring bills created"}


async def extract_text_from_bill(file: UploadFile) -> str:
    content = await file.read()
    if file.filename.lower().endswith(".pdf"):
        images = convert_from_bytes(content)
        text = "\n".join(pytesseract.image_to_string(img) for img in images)
    else:
        img = Image.open(BytesIO(content))
        text = pytesseract.image_to_string(img)
    return text


@router.post("/bills/upload-scan", response_model=None)
async def upload_bill_scan(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    text = await extract_text_from_bill(file)
    return {"extractedText": text}


@router.post("/recurring/run", response_model=None)
async def generate_recurring_expenses(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["ACCOUNTANT", "ADMIN"])(user)
    now = datetime.utcnow()
    active = await db.recurringexpense.find_many(
        where={"isActive": True, "nextDue": {"lte": now}}
    )
    for exp in active:
        await db.vendorbill.create(data={
            "category": exp.category,
            "amount": exp.amount,
            "vendor": exp.vendor,
            "dueDate": exp.nextDue + timedelta(days=15),
            "recurringId": exp.id
        })
        freq_months = {"MONTHLY": 1, "QUARTERLY": 3}.get(exp.frequency, 1)
        await db.recurringexpense.update(
            where={"id": exp.id},
            data={"nextDue": exp.nextDue + relativedelta(months=freq_months)}
        )
    return {"message": f"{len(active)} recurring expenses processed"}
