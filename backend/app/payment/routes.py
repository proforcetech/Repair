# backend/app/payment/routes.py
# This file contains payment management routes for handling customer payments and invoice processing.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db

router = APIRouter(prefix="/payment", tags=["payment"])

class PaymentCreate(BaseModel):
    amount: float
    method: str

# Route to add a payment to an invoice
@router.post("/invoice/{id}/pay")
async def add_payment(id: str, data: PaymentCreate, user = Depends(get_current_user)):
    await db.connect()
    invoice = await db.invoice.find_unique(where={"id": id})
    if not invoice or invoice.customerId != user.id:
        await db.disconnect()
        raise HTTPException(status_code=403, detail="Unauthorized")

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

class PaymentCreate(BaseModel):
    invoiceId: str
    amount: float
    method: str  # e.g. "CASH", "CREDIT_CARD"

# Route to record a payment
@router.post("/payments")
async def record_payment(data: PaymentCreate, user=Depends(get_current_user)):
    await db.connect()
    payment = await db.payment.create(data=data.dict())
    await db.disconnect()
    return {"message": "Payment recorded", "payment": payment}

import stripe
stripe.api_key = "sk_test_..."

# Route to create a Stripe payment link for an invoice
@router.post("/invoices/{invoice_id}/paylink")
async def create_stripe_payment_link(invoice_id: str, user=Depends(get_current_user)):
    await db.connect()
    invoice = await db.invoice.find_unique(
        where={"id": invoice_id},
        include={"estimate": {"include": {"vehicle": {"include": {"customer": True}}}}
    })
    await db.disconnect()

    customer_email = invoice.estimate.vehicle.customer.email

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Invoice #{invoice.id}"},
                "unit_amount": int(invoice.total * 100)
            },
            "quantity": 1
        }],
        mode="payment",
        success_url="https://yourshop.com/thank-you",
        cancel_url="https://yourshop.com/cancel",
        customer_email=customer_email
    )
    return {"url": session.url}

import stripe
from fastapi import Request

# Route to handle Stripe webhook events
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = "your_stripe_webhook_secret"

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, detail="Invalid signature")

    if event['type'] == "checkout.session.completed":
        session = event['data']['object']
        metadata = session.get("metadata", {})
        invoice_id = metadata.get("invoice_id")

        if invoice_id:
            await db.connect()
            await db.payment.create(data={
                "invoiceId": invoice_id,
                "amount": session['amount_total'] / 100,
                "method": "STRIPE"
            })
            await db.disconnect()

    return {"received": True}

# Route to list all invoices with their payment status
@router.get("/invoices")
async def list_invoices(status: Optional[str] = None, user=Depends(get_current_user)):
    await db.connect()
    all = await db.invoice.find_many(include={"payments": True})
    await db.disconnect()

    def calc_status(inv):
        paid = sum(p.amount for p in inv.payments)
        due = inv.total - paid
        if due <= 0:
            return "PAID"
        elif inv.dueDate and inv.dueDate < datetime.utcnow():
            return "OVERDUE"
        elif paid > 0:
            return "PARTIALLY_PAID"
        return "UNPAID"

    filtered = [i for i in all if status is None or calc_status(i) == status.upper()]
    return [{"id": i.id, "status": calc_status(i), "total": i.total} for i in filtered]

# Route to create a checkout session for Stripe payments
@router.post("/payments/checkout")
async def create_checkout(invoice_id: str, user=Depends(get_current_user)):
    await db.connect()
    invoice = await db.invoice.find_unique(where={"id": invoice_id})
    await db.disconnect()

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Invoice {invoice.id}"},
                "unit_amount": int(invoice.total * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url="https://yourdomain.com/payment-success",
        cancel_url="https://yourdomain.com/payment-cancelled",
    )

    return {"checkout_url": session.url}

# Route to handle Stripe webhook events
@router.post("/payments/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        invoice_id = session["metadata"]["invoice_id"]
        await db.connect()
        await db.invoice.update(where={"id": invoice_id}, data={"status": "PAID"})
        await db.disconnect()

    return {"status": "success"}
