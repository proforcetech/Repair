from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from fastapi import Depends
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta

router = APIRouter(prefix="/admin", tags=["admin"])

# Financial Dashboard and Reporting Endpoints 
@router.get("/admin/metrics")
async def financial_dashboard(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()

    invoices = await db.invoice.aggregate(_sum={"total": True})
    payments = await db.payment.aggregate(_sum={"amount": True})
    total_rev = invoices._sum.total or 0
    total_paid = payments._sum.amount or 0

    # Placeholder COGS logic; later link to part cost per order
    cogs = round(total_rev * 0.4, 2)
    gross_margin = round(total_rev - cogs, 2)
    margin_percent = round((gross_margin / total_rev * 100), 2) if total_rev else 0

    await db.disconnect()

    return {
        "total_revenue": total_rev,
        "total_collected": total_paid,
        "cogs": cogs,
        "gross_margin": gross_margin,
        "margin_percent": margin_percent
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
    claim = await db.warrantyclaim.update(
        where={"id": claim_id},
        data={"status": data.status}
    )
    await db.disconnect()
    return {"message": f"Claim {data.status.lower()}", "claim": claim}


if claim.customer.email:
    await send_email(
        to=claim.customer.email,
        subject="Warranty Claim Status Update",
        body=f"Your claim for Work Order #{claim.workOrderId} has been {data.status.lower()}."
    )

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
