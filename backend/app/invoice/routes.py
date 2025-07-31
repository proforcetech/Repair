# backend/app/invoice/routes.py
# This file contains invoice management routes for handling customer invoices, payments, and PDF generation.


from datetime import datetime, timedelta
from dotenv import load_dotenv
from email.message import EmailMessage
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import aiosmtplib
import os
import smtplib
import stripe
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db

apirouter = APIRouter(prefix="/invoice", tags=["invoice"])


load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@router.post("/invoice/{id}/pay/online")
async def stripe_checkout(id: str, user = Depends(get_current_user)):
    await db.connect()
    invoice = await db.invoice.find_unique(where={"id": id}, include={"items": True})
    if not invoice or invoice.customerId != user.id:
        await db.disconnect()
        raise HTTPException(status_code=403, detail="Unauthorized")
    amount = int((invoice.total + invoice.lateFee) * 100)  # cents

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Invoice {invoice.id}"},
                "unit_amount": amount,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url="https://your-app/success",
        cancel_url="https://your-app/cancel",
        metadata={"invoice_id": invoice.id}
    )
    await db.disconnect()
    return {"checkout_url": session.url}


def calculate_late_fee(invoice, daily_rate: float = 2.0) -> float:
    if not invoice.dueDate:
        return 0.0
    today = datetime.utcnow()
    grace = invoice.dueDate + timedelta(days=invoice.graceDays)
    if today <= grace:
        return 0.0
    days_overdue = (today - grace).days
    return round(days_overdue * daily_rate, 2)


@router.get("/invoice/{invoice_id}/pdf")
async def generate_invoice_pdf(invoice_id: str, user = Depends(get_current_user)):
    await db.connect()
    invoice = await db.invoice.find_unique(where={"id": invoice_id}, include={"items": True})
    if not invoice or invoice.customerId != user.id:
        await db.disconnect()
        raise HTTPException(status_code=403, detail="Unauthorized")
    customer = await db.user.find_unique(where={"id": invoice.customerId})
    await db.disconnect()

    env = Environment(loader=FileSystemLoader("templates"))
    html = env.get_template("invoice.html").render(invoice=invoice, customer=customer, items=invoice.items)

    file_path = f"/tmp/invoice_{invoice.id}.pdf"
    HTML(string=html).write_pdf(file_path)
    return FileResponse(file_path, media_type="application/pdf", filename=f"Invoice-{invoice.id}.pdf")




async def send_invoice_email(to_email: str, subject: str, body: str, pdf_path: str):
    message = EmailMessage()
    message["From"] = "you@example.com"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    with open(pdf_path, "rb") as f:
        message.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))
    await aiosmtplib.send(message, hostname="smtp.gmail.com", port=587, start_tls=True, username="you@example.com", password="yourpassword")


class PaymentCreate(BaseModel):
    amount: float
    method: str

@router.post("/invoice/{id}/pay")
async def add_payment(id: str, data: PaymentCreate, user = Depends(get_current_user)):
    await db.connect()
    invoice = await db.invoice.find_unique(where={"id": id})
    if not invoice or invoice.customerId != user.id:
        await db.disconnect()
        raise HTTPException(status_code=403, detail="Unauthorized")

    late_fee = calculate_late_fee(invoice)
    await db.invoice.update(where={"id": id}, data={"lateFee": late_fee})
    total_due = invoice.total + late_fee

    payment = await db.payment.create({
        "invoiceId": id,
        "amount": data.amount,
        "method": data.method
    })

    payments = await db.payment.aggregate(
        where={"invoiceId": id},
        _sum={"amount": True}
    )

    total_paid = payments._sum.amount or 0
    status = "PAID" if total_paid >= invoice.total else "PARTIALLY_PAID"

    await db.invoice.update(where={"id": id}, data={"status": status})
    await db.disconnect()
    return {"payment": payment, "total_paid": total_paid, "status": status}

async def reward_loyalty(invoice_id: str):
    await db.connect()
    invoice = await db.invoice.find_unique(where={"id": invoice_id}, include={"customer": True})
    if not invoice or invoice.status != "PAID":
        await db.disconnect()
        return

    points = int(invoice.total // 50)  # 1 point per $50 spent
    await db.customer.update(
        where={"id": invoice.customer.id},
        data={
            "loyaltyPoints": {"increment": points},
            "visits": {"increment": 1}
        }
    )
    await db.disconnect()


@router.post("/invoices/{invoice_id}/finalize")
async def finalize_invoice(invoice_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    invoice = await db.invoice.find_unique(where={"id": invoice_id})
    if not invoice:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Update invoice status
    await db.invoice.update(where={"id": invoice_id}, data={"status": "FINALIZED"})

    # Mark job parts as used
    await db.jobpart.update_many(
        where={"jobId": invoice.jobId},
        data={"used": True}
    )

    await db.disconnect()
    return {"message": "Invoice finalized and parts marked used"}


@router.get("/invoices/{invoice_id}/margin")
async def get_invoice_margin(invoice_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    parts = await db.invoicepart.find_many(where={"invoiceId": invoice_id})
    await db.disconnect()

    total_cost = sum(p.cost * p.quantity for p in parts)
    total_price = sum(p.unitPrice * p.quantity for p in parts)
    margin = round(((total_price - total_cost) / total_price) * 100, 2) if total_price > 0 else 0

    return {
        "total_cost": total_cost,
        "total_price": total_price,
        "gross_margin_percent": margin
    }

from app.core.config import INVOICE_MARGIN_ALERT_THRESHOLD

...

parts = await db.invoicepart.find_many(where={"invoiceId": invoice_id})
total_cost = sum(p.cost * p.quantity for p in parts)
total_price = sum(p.unitPrice * p.quantity for p in parts)
margin = round(((total_price - total_cost) / total_price) * 100, 2) if total_price else 0

if margin < INVOICE_MARGIN_ALERT_THRESHOLD:
    # Optionally log or notify manager
    await notify_user(
        email="manager@repairshop.com",
        subject="?? Low Margin Invoice Alert",
        body=f"Invoice {invoice_id} has a gross margin of {margin}%."
    )

@router.post("/expenses/{id}/invoice")
async def upload_expense_invoice(id: str, file: UploadFile = File(...), user = Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    ext = file.filename.split(".")[-1]
    fname = f"{uuid.uuid4()}.{ext}"
    path = os.path.join("/app/static/expense_invoices", fname)

    with open(path, "wb") as f:
        f.write(await file.read())

    url = f"/static/expense_invoices/{fname}"
    await db.connect()
    await db.expense.update(where={"id": id}, data={"invoiceFileUrl": url})
    await db.disconnect()

    return {"message": "Invoice uploaded", "url": url}


@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(invoice_id: str, user=Depends(get_current_user)):
    await db.connect()
    invoice = await db.invoice.find_unique(where={"id": invoice_id}, include={"estimate": {"include": {"vehicle": True, "items": True}}})
    customer = await db.customer.find_unique(where={"id": invoice.estimate.vehicle.customerId})
    await db.disconnect()

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("invoice.html")
    html_out = template.render(
        shop_name="Fast Auto Repair",
        invoice=invoice,
        customer=customer,
        items=invoice.estimate.items
    )

    pdf = HTML(string=html_out).write_pdf()
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=invoice_{invoice_id}.pdf"
    })


async def send_invoice_email(to: str, subject: str, html: str, pdf_bytes: bytes):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = 'noreply@repairshop.local'
    msg['To'] = to
    msg.set_content("Your invoice is attached.")
    msg.add_alternative(html, subtype='html')
    msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename='invoice.pdf')

    with smtplib.SMTP("localhost") as s:
        s.send_message(msg)

@router.post("/invoices/{invoice_id}/email")
async def email_invoice(invoice_id: str, user=Depends(get_current_user)):
    ...
    await send_invoice_email(to=customer.email, subject="Your Invoice", html=html_out, pdf_bytes=pdf)
    return {"message": "Invoice emailed"}


@router.get("/invoices/{invoice_id}/summary")
async def get_invoice_summary(invoice_id: str, user=Depends(get_current_user)):
    await db.connect()
    invoice = await db.invoice.find_unique(
        where={"id": invoice_id},
        include={"estimate": {"include": {"items": True}}}
    )
    payments = await db.payment.find_many(where={"invoiceId": invoice_id})
    await db.disconnect()

    paid = sum(p.amount for p in payments)
    due = round(invoice.total - paid, 2)

    return {
        "invoiceId": invoice_id,
        "total": invoice.total,
        "paid": paid,
        "due": due,
        "status": (
            "PAID" if due == 0 else "PARTIALLY_PAID" if paid > 0 else "UNPAID"
        ),
        "payments": payments
    }

@router.post("/invoices/email-unpaid")
async def email_unpaid(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "MANAGER"])(user)

    await db.connect()
    unpaid = await db.invoice.find_many(where={"status": "UNPAID"}, include={"customer": True})

    for inv in unpaid:
        link = f"https://repairshop.app/pay/{inv.id}"
        send_email(
            inv.customer.email,
            "Unpaid Invoice",
            f"Dear {inv.customer.email},\n\nYou have an unpaid invoice #{inv.id}. Pay now: {link}"
        )

    await db.disconnect()
    return {"message": f"Emailed {len(unpaid)} unpaid invoices"}
