"""Invoice management routes.

This module exposes invoice list/detail endpoints along with
payment handling, PDF exports, and manager-facing analytics.
The implementation intentionally keeps business logic close to
the HTTP layer because integration tests patch the prisma client
with simple in-memory fakes.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence

import stripe
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user, require_role
from app.core.config import settings
from app.db.prisma_client import db


router = APIRouter(prefix="/invoice", tags=["Invoices"])


if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0, description="Amount collected for the invoice")
    method: str = Field(min_length=2, description="Payment method descriptor")


class FinalizeResponse(BaseModel):
    message: str
    status: str
    finalized_at: datetime


def _extract_customer_name(customer: Dict[str, Any] | None) -> str | None:
    if not customer:
        return None
    name = customer.get("name") or customer.get("fullName")
    if name:
        return str(name)
    first = customer.get("firstName")
    last = customer.get("lastName")
    if first or last:
        return " ".join(filter(None, [first, last])).strip() or None
    return None


def _sum_payments(payments: Iterable[Dict[str, Any]]) -> float:
    total = 0.0
    for payment in payments:
        amount = payment.get("amount")
        if isinstance(amount, (int, float)):
            total += float(amount)
    return round(total, 2)


def _coerce_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _invoice_total(invoice: Dict[str, Any]) -> float:
    explicit_total = invoice.get("total")
    if isinstance(explicit_total, (int, float)):
        return float(explicit_total)
    subtotal = _coerce_number(invoice.get("subtotal"))
    tax = _coerce_number(invoice.get("tax"))
    fees = _coerce_number(invoice.get("lateFee"))
    discounts = _coerce_number(invoice.get("discountTotal"))
    total = subtotal + tax + fees - discounts
    return round(total, 2)


def _invoice_balance(invoice: Dict[str, Any]) -> float:
    payments = invoice.get("payments") or []
    late_fee = _coerce_number(invoice.get("lateFee"))
    total = _invoice_total(invoice)
    paid = _sum_payments(payments)
    balance = total + late_fee - paid
    return round(balance, 2)


def _format_invoice_summary(invoice: Dict[str, Any]) -> Dict[str, Any]:
    payments = invoice.get("payments") or []
    return {
        "id": invoice.get("id"),
        "number": invoice.get("number") or invoice.get("id"),
        "status": invoice.get("status") or "DRAFT",
        "issuedDate": invoice.get("issuedDate") or invoice.get("createdAt"),
        "dueDate": invoice.get("dueDate"),
        "total": _invoice_total(invoice),
        "lateFee": _coerce_number(invoice.get("lateFee")),
        "balanceDue": _invoice_balance(invoice),
        "customer": {
            "id": (invoice.get("customer") or {}).get("id") or invoice.get("customerId"),
            "name": _extract_customer_name(invoice.get("customer")),
            "email": (invoice.get("customer") or {}).get("email"),
        },
        "payments": [
            {
                "id": payment.get("id"),
                "amount": _coerce_number(payment.get("amount")),
                "method": payment.get("method"),
                "receivedAt": payment.get("receivedAt") or payment.get("createdAt"),
            }
            for payment in payments
        ],
    }


async def _load_invoice(invoice_id: str, *, include_items: bool = False) -> Dict[str, Any]:
    include = {"customer": True, "payments": True}
    if include_items:
        include["items"] = True
    await db.connect()
    try:
        invoice = await db.invoice.find_unique(where={"id": invoice_id}, include=include)
    finally:
        await db.disconnect()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return dict(invoice)


def _running_balances(invoice: Dict[str, Any]) -> List[Dict[str, Any]]:
    payments = sorted(
        invoice.get("payments") or [],
        key=lambda payment: payment.get("receivedAt") or payment.get("createdAt") or datetime.now(timezone.utc),
    )
    balance = _invoice_total(invoice) + _coerce_number(invoice.get("lateFee"))
    enriched: List[Dict[str, Any]] = []
    for payment in payments:
        amount = _coerce_number(payment.get("amount"))
        balance = round(balance - amount, 2)
        enriched.append(
            {
                "id": payment.get("id"),
                "amount": amount,
                "method": payment.get("method"),
                "receivedAt": payment.get("receivedAt") or payment.get("createdAt"),
                "runningBalance": balance,
            }
        )
    return enriched


def _margin_from_items(items: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    total_cost = 0.0
    total_price = 0.0
    for item in items:
        quantity = _coerce_number(item.get("quantity")) or 1
        total_cost += _coerce_number(item.get("cost")) * quantity
        total_price += _coerce_number(item.get("unitPrice")) * quantity
    margin_percent = 0.0
    if total_price > 0:
        margin_percent = round(((total_price - total_cost) / total_price) * 100, 2)
    return {
        "cost": round(total_cost, 2),
        "price": round(total_price, 2),
        "margin": margin_percent,
    }


def _user_attr(user: Any, attribute: str) -> Any:
    if hasattr(user, attribute):
        return getattr(user, attribute)
    if isinstance(user, dict):
        return user.get(attribute)
    return None


@router.get("", summary="List invoices accessible to the authenticated user")
async def list_invoices(user: Any = Depends(get_current_user)) -> List[Dict[str, Any]]:
    filters: Dict[str, Any] = {}
    include = {"customer": True, "payments": True}
    privileged_roles = {"ADMIN", "MANAGER", "ACCOUNTANT"}
    user_role = _user_attr(user, "role")
    user_id = _user_attr(user, "id")
    if user_role not in privileged_roles:
        filters["customerId"] = user_id
    await db.connect()
    try:
        invoices: Sequence[Dict[str, Any]] = await db.invoice.find_many(
            where=filters or None,
            include=include,
            order_by={"createdAt": "desc"},
        )
    finally:
        await db.disconnect()
    return [_format_invoice_summary(dict(invoice)) for invoice in invoices]


@router.get("/{invoice_id}", summary="Retrieve invoice detail")
async def get_invoice(invoice_id: str, user: Any = Depends(get_current_user)) -> Dict[str, Any]:
    invoice = await _load_invoice(invoice_id, include_items=True)
    privileged_roles = {"ADMIN", "MANAGER", "ACCOUNTANT", "SERVICE_ADVISOR"}
    user_role = _user_attr(user, "role")
    user_id = _user_attr(user, "id")
    if user_role not in privileged_roles and invoice.get("customerId") != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized to view invoice")

    items = [
        {
            "id": item.get("id"),
            "description": item.get("description") or item.get("name"),
            "quantity": _coerce_number(item.get("quantity")) or 1,
            "unitPrice": _coerce_number(item.get("unitPrice")),
            "cost": _coerce_number(item.get("cost")),
        }
        for item in (invoice.get("items") or [])
    ]

    payments = _running_balances(invoice)
    loyalty_snapshot = invoice.get("loyalty") or {}

    summary = _format_invoice_summary(invoice)
    summary.update(
        {
            "items": items,
            "payments": payments,
            "subtotal": _coerce_number(invoice.get("subtotal")),
            "tax": _coerce_number(invoice.get("tax")),
            "discountTotal": _coerce_number(invoice.get("discountTotal")),
            "loyalty": {
                "pointsEarned": int(loyalty_snapshot.get("pointsEarned", 0)),
                "customerBalance": int(loyalty_snapshot.get("customerBalance", 0)),
            },
        }
    )
    return summary


@router.post("/{invoice_id}/pay", summary="Record a manual payment")
async def record_payment(
    invoice_id: str,
    payload: PaymentCreate,
    user: Any = Depends(get_current_user),
) -> Dict[str, Any]:
    invoice = await _load_invoice(invoice_id, include_items=False)
    privileged_roles = {"ADMIN", "MANAGER", "ACCOUNTANT"}
    user_role = _user_attr(user, "role")
    user_id = _user_attr(user, "id")
    if user_role not in privileged_roles and invoice.get("customerId") != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized to record payment")

    await db.connect()
    try:
        payment = await db.payment.create(
            {
                "invoiceId": invoice_id,
                "amount": payload.amount,
                "method": payload.method,
                "receivedAt": datetime.now(timezone.utc),
            }
        )
        payments = await db.payment.find_many(where={"invoiceId": invoice_id})
        paid_total = _sum_payments(payments)
        total_due = _invoice_total(invoice) + _coerce_number(invoice.get("lateFee"))
        remaining = round(total_due - paid_total, 2)
        status = "PAID" if remaining <= 0 else "PARTIALLY_PAID"
        await db.invoice.update(where={"id": invoice_id}, data={"status": status})
    finally:
        await db.disconnect()

    response = await get_invoice(invoice_id, user=user)
    response.update({
        "newPayment": {
            "id": payment.get("id"),
            "amount": payload.amount,
            "method": payload.method,
            "receivedAt": payment.get("receivedAt"),
        }
    })
    return response


@router.post("/{invoice_id}/pay/online", summary="Initiate a Stripe Checkout session")
async def create_checkout_session(invoice_id: str, user: Any = Depends(get_current_user)) -> Dict[str, Any]:
    invoice = await _load_invoice(invoice_id, include_items=False)
    user_role = _user_attr(user, "role")
    user_id = _user_attr(user, "id")
    if invoice.get("customerId") != user_id and user_role not in {"ADMIN", "MANAGER", "ACCOUNTANT"}:
        raise HTTPException(status_code=403, detail="Unauthorized to pay invoice")

    amount_cents = int(round((_invoice_total(invoice) + _coerce_number(invoice.get("lateFee"))) * 100))
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Invoice {invoice.get('number') or invoice_id}"},
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url="https://app.local/portal/invoices/success",
        cancel_url="https://app.local/portal/invoices/cancel",
        metadata={"invoice_id": invoice_id},
    )
    return {"checkout_url": session.get("url")}


@router.post("/{invoice_id}/finalize", response_model=FinalizeResponse, summary="Finalize an invoice")
async def finalize_invoice(invoice_id: str, user: Any = Depends(get_current_user)) -> FinalizeResponse:
    require_role(["MANAGER", "ADMIN"])(user)
    finalized_at = datetime.now(timezone.utc)
    await db.connect()
    try:
        invoice = await db.invoice.find_unique(where={"id": invoice_id})
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        await db.invoice.update(
            where={"id": invoice_id},
            data={"status": "FINALIZED", "finalizedAt": finalized_at},
        )
    finally:
        await db.disconnect()
    return FinalizeResponse(message="Invoice finalized", status="FINALIZED", finalized_at=finalized_at)


@router.get("/{invoice_id}/margin", summary="Calculate invoice gross margin")
async def get_invoice_margin(invoice_id: str, user: Any = Depends(get_current_user)) -> Dict[str, Any]:
    require_role(["MANAGER", "ADMIN"])(user)
    invoice = await _load_invoice(invoice_id, include_items=True)
    items = invoice.get("items") or []
    margin_values = _margin_from_items(items)
    return {
        "invoiceId": invoice_id,
        "total_cost": margin_values["cost"],
        "total_price": margin_values["price"],
        "gross_margin_percent": margin_values["margin"],
        "threshold": settings.thresholds.invoice_margin_alert_percent,
        "is_below_threshold": margin_values["margin"] < settings.thresholds.invoice_margin_alert_percent,
    }


@router.get("/analytics/margin", summary="Aggregate margin analytics for finalized invoices")
async def get_margin_analytics(user: Any = Depends(get_current_user)) -> Dict[str, Any]:
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    try:
        invoices: Sequence[Dict[str, Any]] = await db.invoice.find_many(
            where={"status": "FINALIZED"},
            include={"items": True, "customer": True},
            order_by={"finalizedAt": "desc"},
        )
    finally:
        await db.disconnect()

    series: List[Dict[str, Any]] = []
    total_margin_percent = 0.0
    below_threshold = 0

    for invoice in invoices:
        invoice_dict = dict(invoice)
        margin_values = _margin_from_items(invoice_dict.get("items") or [])
        margin_percent = margin_values["margin"]
        series.append(
            {
                "invoiceId": invoice_dict.get("id"),
                "number": invoice_dict.get("number") or invoice_dict.get("id"),
                "customer": _extract_customer_name(invoice_dict.get("customer")),
                "finalizedAt": invoice_dict.get("finalizedAt"),
                "grossMarginPercent": margin_percent,
                "isBelowThreshold": margin_percent < settings.thresholds.invoice_margin_alert_percent,
            }
        )
        total_margin_percent += margin_percent
        if margin_percent < settings.thresholds.invoice_margin_alert_percent:
            below_threshold += 1

    average_margin = round(total_margin_percent / len(invoices), 2) if invoices else 0.0

    return {
        "averageMarginPercent": average_margin,
        "lowMarginInvoices": below_threshold,
        "threshold": settings.thresholds.invoice_margin_alert_percent,
        "series": series,
    }


@router.get("/{invoice_id}/pdf", summary="Download invoice PDF placeholder")
async def download_invoice_pdf(invoice_id: str, user: Any = Depends(get_current_user)) -> StreamingResponse:
    invoice = await _load_invoice(invoice_id, include_items=False)
    privileged_roles = {"ADMIN", "MANAGER", "ACCOUNTANT"}
    user_role = _user_attr(user, "role")
    user_id = _user_attr(user, "id")
    if invoice.get("customerId") != user_id and user_role not in privileged_roles:
        raise HTTPException(status_code=403, detail="Unauthorized to download invoice")

    content = f"Invoice {invoice.get('number') or invoice_id} — Total ${_invoice_total(invoice):.2f}".encode()
    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4\n1 0 obj<</Length 44>>stream\nBT /F1 12 Tf 50 750 Td (")
    buffer.write(content.replace(b"(", b"[").replace(b")", b"]"))
    buffer.write(b") Tj ET\nendstream endobj\ntrailer<</Root 1 0 R>>\n%%EOF")
    buffer.seek(0)
    headers = {"Content-Disposition": f"attachment; filename=invoice-{invoice_id}.pdf"}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
