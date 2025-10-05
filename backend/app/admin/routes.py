from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user, require_role
from app.core.notifier import send_email
from app.db.prisma_client import db

router = APIRouter(prefix="/admin", tags=["admin"])

# Financial Dashboard and Reporting Endpoints 
@router.get("/admin/metrics")
async def financial_dashboard(user: Any = Depends(get_current_user)):
    """Return headline metrics for the admin dashboard."""

    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()

    try:
        invoice_agg = await db.invoice.aggregate(
            _sum={"total": True},
            _count={"_all": True},
        )
        payment_agg = await db.payment.aggregate(_sum={"amount": True})
        user_agg = await db.user.aggregate(_count={"_all": True})
        technician_agg = await db.user.aggregate(
            where={"role": "TECHNICIAN"},
            _count={"_all": True},
        )
        vehicle_agg = await db.vehicle.aggregate(_count={"_all": True})
        customer_agg = await db.customer.aggregate(_count={"_all": True})
        job_agg = await db.job.aggregate(_count={"_all": True})
        completed_job_agg = await db.job.aggregate(
            where={"status": "COMPLETED"},
            _count={"_all": True},
        )
        outstanding_invoice_agg = await db.invoice.aggregate(
            where={"status": {"in": ["UNPAID", "PARTIALLY_PAID"]}},
            _count={"_all": True},
        )
        warranty_agg = await db.warrantyclaim.aggregate(_count={"_all": True})
        open_warranty_agg = await db.warrantyclaim.aggregate(
            where={"status": {"notIn": ["APPROVED", "REJECTED"]}},
            _count={"_all": True},
        )
    finally:
        await db.disconnect()

    def _count(agg: Any) -> int:
        count_block = getattr(agg, "_count", None)
        if not count_block:
            return 0
        value = getattr(count_block, "_all", 0)
        return value or 0

    def _sum(agg: Any, field: str) -> float:
        sum_block = getattr(agg, "_sum", None)
        if not sum_block:
            return 0.0
        value = getattr(sum_block, field, 0.0)
        return float(value or 0.0)

    total_revenue = _sum(invoice_agg, "total")
    total_collected = _sum(payment_agg, "amount")

    # Placeholder COGS logic; later link to part cost per order
    cogs = round(total_revenue * 0.4, 2)
    gross_margin = round(total_revenue - cogs, 2)
    margin_percent = round((gross_margin / total_revenue * 100), 2) if total_revenue else 0.0

    return {
        "financial": {
            "total_revenue": total_revenue,
            "total_collected": total_collected,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "margin_percent": margin_percent,
        },
        "counts": {
            "users": _count(user_agg),
            "technicians": _count(technician_agg),
            "customers": _count(customer_agg),
            "vehicles": _count(vehicle_agg),
            "jobs": {
                "total": _count(job_agg),
                "completed": _count(completed_job_agg),
            },
            "invoices": {
                "total": _count(invoice_agg),
                "outstanding": _count(outstanding_invoice_agg),
            },
            "warranty_claims": {
                "total": _count(warranty_agg),
                "open": _count(open_warranty_agg),
            },
        },
    }
    
# Technician Performance Summary Endpoint
@router.get("/admin/technicians/performance")
async def technician_summary(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    jobs = await db.job.find_many()

    summary = {}
    for tech in techs:
        user_jobs = [j for j in jobs if j.technicianId == tech.id]
        billed = sum(j.billedHours for j in user_jobs)
        actual = sum(j.actualHours for j in user_jobs)
        efficiency = round((billed / actual * 100), 2) if actual else 0
        summary[tech.email] = {
            "billed_hours": billed,
            "actual_hours": actual,
            "efficiency_percent": efficiency
        }

    await db.disconnect()
    return summary

# Inventory Cost of Goods Sold (COGS) Report Endpoint
@router.get("/admin/cogs")
async def cogs_report(user = Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    await db.connect()
    usage = await db.partusage.find_many()
    total_cogs = sum(u.cost * u.quantity for u in usage)
    await db.disconnect()
    return {"total_cogs": total_cogs}

# Financial Report Endpoint
@router.get("/admin/financials/report")
async def financial_report(user = Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    await db.connect()

    invoices = await db.invoice.aggregate(_sum={"total": True})
    payments = await db.payment.aggregate(_sum={"amount": True})
    cogs_usage = await db.partusage.find_many()
    expenses = await db.expense.aggregate(_sum={"amount": True})

    total_revenue = invoices._sum.total or 0
    total_collected = payments._sum.amount or 0
    total_cogs = sum(u.cost * u.quantity for u in cogs_usage)
    total_expenses = expenses._sum.amount or 0

    gross_profit = total_revenue - total_cogs
    net_profit = gross_profit - total_expenses
    sales_tax = round(total_revenue * 0.07, 2)  # example 7% tax

    await db.disconnect()

    return {
        "total_revenue": total_revenue,
        "total_collected": total_collected,
        "total_cogs": total_cogs,
        "total_expenses": total_expenses,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "sales_tax_collected": sales_tax
    }

# Warranty Claim Management Endpoints
@router.get("/warranty")
async def list_all_claims(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK"])(user)

    await db.connect()
    claims = await db.warrantyclaim.find_many(
        include={"customer": True, "workOrder": True},
        order={"createdAt": "desc"}
    )
    await db.disconnect()
    return claims

class ClaimStatusUpdate(BaseModel):
    status: str  # "APPROVED" or "DENIED"

# Update Claim Status Endpoint
@router.put("/warranty/{claim_id}/status")
async def update_claim_status(claim_id: str, data: ClaimStatusUpdate, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    if data.status not in ["APPROVED", "DENIED"]:
        raise HTTPException(400, "Invalid status")

    await db.connect()
    try:
        claim = await db.warrantyclaim.update(
            where={"id": claim_id},
            data={"status": data.status},
            include={"customer": True, "workOrder": True},
        )
    finally:
        await db.disconnect()

    if getattr(claim, "customer", None) and getattr(claim.customer, "email", None):
        await send_email(
            claim.customer.email,
            "Warranty Claim Status Update",
            f"Your claim for Work Order #{getattr(claim, 'workOrderId', '')} has been {data.status.lower()}.",
        )

    return {"message": f"Claim {data.status.lower()}", "claim": claim}


class AuditLogPurgeRequest(BaseModel):
    older_than_days: int = Field(365, gt=0, le=1825)


@router.get("/admin/audit/logs")
async def list_audit_logs(
    page: int = 1,
    page_size: int = 50,
    user: Any = Depends(get_current_user),
):
    require_role(["ADMIN"])(user)

    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)

    await db.connect()
    try:
        total_agg = await db.auditlog.aggregate(_count={"_all": True})
        logs = await db.auditlog.find_many(
            order={"timestamp": "desc"},
            skip=(page - 1) * page_size,
            take=page_size,
        )
    finally:
        await db.disconnect()

    total = 0
    if getattr(total_agg, "_count", None):
        total = getattr(total_agg._count, "_all", 0) or 0

    return {
        "items": logs,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    }


@router.post("/admin/audit/purge")
async def purge_audit_logs(
    payload: AuditLogPurgeRequest,
    user: Any = Depends(get_current_user),
):
    require_role(["ADMIN"])(user)

    cutoff = datetime.utcnow() - timedelta(days=payload.older_than_days)

    await db.connect()
    try:
        deleted = await db.auditlog.delete_many(where={"timestamp": {"lt": cutoff}})
    finally:
        await db.disconnect()

    deleted_count = getattr(deleted, "count", None)
    if deleted_count is None:
        # Prisma returns a dictionary-like object in older versions
        deleted_count = deleted.get("count", 0) if isinstance(deleted, dict) else 0

    return {"deleted": deleted_count, "cutoff": cutoff.isoformat()}

# Exports Warranty Claims as CSVF
@router.get("/warranty/export.csv")
async def export_claims_csv(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    claims = await db.warrantyclaim.find_many(include={"customer": True, "workOrder": True})
    await db.disconnect()

    from io import StringIO
    import pandas as pd

    rows = [
        {
            "Customer": c.customer.fullName,
            "Work Order": c.workOrderId,
            "Status": c.status,
            "Submitted": c.createdAt,
            "Attachment": c.attachmentUrl or "",
            "Notes": c.resolutionNotes or ""
        } for c in claims
    ]

    df = pd.DataFrame(rows)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=warranty_claims.csv"}
    )

# Export Warranty Claims as PDF
@router.get("/warranty/export.pdf")
async def export_claims_pdf(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    claims = await db.warrantyclaim.find_many(include={"customer": True, "workOrder": True})
    await db.disconnect()

    rows = ''.join(
        f"<tr><td>{c.customer.fullName}</td><td>{c.workOrderId}</td><td>{c.status}</td>"
        f"<td>{c.createdAt.date()}</td><td>{c.resolutionNotes or ''}</td></tr>"
        for c in claims
    )

    html = f"""
    <h1>Warranty Claims Report</h1>
    <table border="1">
        <tr><th>Customer</th><th>Work Order</th><th>Status</th><th>Date</th><th>Resolution Notes</th></tr>
        {rows}
    </table>
    """

    from weasyprint import HTML
    pdf = HTML(string=html).write_pdf()

    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=warranty_claims.pdf"}
    )

# List Claims with SLA Breach
# This will list all open warranty claims that have breached the SLA of 48 hours without first response
@router.get("/warranty-sla")
async def list_claims_with_sla(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK"])(user)

    SLA_HOURS = 48
    now = datetime.utcnow()

    await db.connect()
    claims = await db.warrantyclaim.find_many(
        where={"status": "OPEN"},
        include={"customer": True, "assignedTo": True},
        order={"createdAt": "desc"}
    )
    await db.disconnect()

    enriched = []
    for c in claims:
        hours_open = (now - c.createdAt).total_seconds() / 3600
        is_breached = c.firstResponseAt is None and hours_open > SLA_HOURS
        is_warning = c.firstResponseAt is None and SLA_HOURS - hours_open <= 6

        enriched.append({
            "id": c.id,
            "customer": c.customer.fullName,
            "status": c.status,
            "createdAt": c.createdAt,
            "assignedTo": c.assignedTo.email if c.assignedTo else None,
            "slaBreached": is_breached,
            "slaWarning": is_warning
        })

    return enriched


@router.get("/warranty")
async def list_claims(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    claims = await db.warrantyclaim.find_many()
    await db.disconnect()
    return claims
