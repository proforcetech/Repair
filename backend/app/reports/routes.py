# backend/app/reports/routes.py
# This file contains various reporting and analytics endpoints for the application.

import pandas as pd
from fastapi.responses import StreamingResponse
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from collections import defaultdict

router = APIRouter(prefix="/reports", tags=["reports"])

# Generate revenue trends CSV
@router.get("/admin/revenue/trends.csv")
async def export_revenue_trend_csv(
    period: str = "monthly",
    user = Depends(get_current_user)
):
    require_role(["ADMIN"])(user)
    await db.connect()
    invoices = await db.invoice.find_many()
    await db.disconnect()

    from collections import defaultdict
    trend = defaultdict(float)

    for inv in invoices:
        dt = inv.createdAt
        if period == "monthly":
            key = f"{dt.year}-{dt.month:02}"
        elif period == "weekly":
            key = f"{dt.year}-W{dt.isocalendar().week:02}"
        elif period == "yearly":
            key = str(dt.year)
        else:
            continue
        trend[key] += inv.total

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Period", "Total Revenue"])
    for key in sorted(trend):
        writer.writerow([key, round(trend[key], 2)])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename=revenue_{period}_trend.csv"
    })

# Generate revenue trends data for dashboard
@router.get("/admin/revenue/trends")
async def revenue_trends(user = Depends(get_current_user), period: str = "monthly"):
    require_role(["ADMIN"])(user)
    await db.connect()

    invoices = await db.invoice.find_many()
    await db.disconnect()

    trend = defaultdict(float)

    for inv in invoices:
        dt = inv.createdAt
        key = None
        if period == "monthly":
            key = f"{dt.year}-{dt.month:02}"
        elif period == "weekly":
            key = f"{dt.year}-W{dt.isocalendar().week:02}"
        elif period == "yearly":
            key = str(dt.year)

        if key:
            trend[key] += inv.total

    sorted_data = dict(sorted(trend.items()))
    return {"period": period, "totals": sorted_data}

#Exports PO information in CSV Format
@router.get("/export/pos.csv")
async def export_purchase_orders_csv(user = Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    await db.connect()
    pos = await db.purchaseorder.find_many(include={"items": {"include": {"part": True}}})
    await db.disconnect()

    flat_data = []
    for po in pos:
        for item in po.items:
            flat_data.append({
                "PO ID": po.id,
                "Vendor": po.vendor,
                "Status": po.status,
                "Date": po.createdAt.isoformat(),
                "SKU": item.part.sku,
                "Description": item.part.description,
                "Qty": item.qty
            })

    df = pd.DataFrame(flat_data)
    stream = StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)
    return StreamingResponse(stream, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=purchase_orders.csv"
    })

# Audit Trail for Part Requests
@router.get("/audit/part-trail")
async def trace_part_request_flow(sku: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    part = await db.part.find_first(where={"sku": sku})
    if not part:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Part not found")

    requests = await db.partrequest.find_many(where={"sku": sku})
    items = await db.purchaseitem.find_many(where={"partId": part.id})
    events = await db.inventoryevent.find_many(where={"partId": part.id})

    await db.disconnect()
    return {
        "part": part,
        "requests": requests,
        "po_items": items,
        "received_logs": events
    }

#
@router.get("/template-usage/trends")
async def get_template_usage_trends(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    templates = await db.partrequesttemplate.find_many(
        include={"items": True},
        order={"createdAt": "asc"}
    )

    from collections import defaultdict

    trends = defaultdict(lambda: defaultdict(int))
    for t in templates:
        month = t.createdAt.strftime("%Y-%m")
        trends[month][t.name] += t.usageCount

    await db.disconnect()
    return [
        {"month": month, "templates": dict(usage)}
        for month, usage in sorted(trends.items())
    ]

@router.get("/alerts/frequent-substitutes")
async def frequent_substitutes(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    parts = await db.jobpart.find_many(
        where={"techNote": {"contains": "substitute", "mode": "insensitive"}}
    )
    await db.disconnect()

    from collections import Counter
    counter = Counter([p.sku for p in parts])
    frequent = [
        {"sku": sku, "count": count}
        for sku, count in counter.items()
        if count >= 3
    ]

    return {"frequent_substitutes": frequent}

@router.get("/kpis/parts-per-tech/filtered")
async def parts_per_tech_filtered(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    where = {"used": True}
    if start_date and end_date:
        where["usedAt"] = {
            "gte": start_date,
            "lte": end_date
        }

    parts = await db.jobpart.find_many(where=where)
    users = await db.user.find_many()

    summary = {}
    for u in users:
        summary[u.id] = {
            "email": u.email,
            "total_parts": 0,
            "total_quantity": 0
        }

    for p in parts:
        job = await db.job.find_unique(where={"id": p.jobId})
        if job:
            if vehicle_type and vehicle_type not in (job.vehicleType or ""):
                continue
            if job.technicianId in summary:
                summary[job.technicianId]["total_parts"] += 1
                summary[job.technicianId]["total_quantity"] += p.quantity

    await db.disconnect()
    return list(summary.values())

@router.get("/export/parts-per-tech")
async def export_parts_per_tech(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    parts = await db.jobpart.find_many(where={"used": True})
    jobs = await db.job.find_many()
    users = await db.user.find_many()
    await db.disconnect()

    job_map = {j.id: j.technicianId for j in jobs}
    user_map = {u.id: u.email for u in users}

    from collections import defaultdict
    from io import StringIO
    import csv
    from fastapi.responses import StreamingResponse

    totals = defaultdict(lambda: {"parts": 0, "quantity": 0})
    for p in parts:
        tech_id = job_map.get(p.jobId)
        if tech_id:
            totals[tech_id]["parts"] += 1
            totals[tech_id]["quantity"] += p.quantity

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Technician", "Total Parts", "Total Quantity"])
    for tid, vals in totals.items():
        writer.writerow([user_map.get(tid, tid), vals["parts"], vals["quantity"]])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=parts_per_tech.csv"
    })

@router.get("/reports/po-rejections")
async def po_rejection_trends(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    pos = await db.purchaseorder.find_many(where={"status": "REJECTED"})
    await db.disconnect()

    from collections import defaultdict
    trend = defaultdict(int)
    reasons = defaultdict(int)

    for po in pos:
        month = po.createdAt.strftime("%Y-%m")
        trend[month] += 1
        if po.rejectionReason:
            reasons[po.rejectionReason] += 1

    return {
        "monthly_rejections": dict(trend),
        "top_rejection_reasons": dict(reasons)
    }

@router.get("/export/tech-bay-schedule")
async def export_tech_bay_schedule(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    await db.disconnect()

    from io import StringIO
    import csv
    from fastapi.responses import StreamingResponse

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Technician", "Assigned Bay"])

    for t in techs:
        writer.writerow([t.email, t.assignedBay or "Unassigned"])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=tech_bay_schedule.csv"
    })

@router.get("/export/pos")
async def export_purchase_orders(user = Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    await db.connect()
    pos = await db.purchaseorder.find_many(include={"items": {"include": {"part": True}}})
    await db.disconnect()

    return [
        {
            "poId": po.id,
            "vendor": po.vendor,
            "status": po.status,
            "createdAt": po.createdAt,
            "items": [
                {
                    "sku": i.part.sku,
                    "description": i.part.description,
                    "qty": i.qty
                } for i in po.items
            ]
        } for po in pos
    ]

from fastapi.responses import Response
from weasyprint import HTML

@router.get("/export/pos.pdf")
async def export_purchase_orders_pdf(user = Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    await db.connect()
    pos = await db.purchaseorder.find_many(include={"items": {"include": {"part": True}}})
    await db.disconnect()

    rows = ""
    for po in pos:
        for item in po.items:
            rows += f"""
            <tr><td>{po.id}</td><td>{po.vendor}</td><td>{po.status}</td>
            <td>{item.part.sku}</td><td>{item.part.description}</td><td>{item.qty}</td></tr>
            """

    html = f"""
    <html><body>
    <h2>Purchase Orders</h2>
    <table border="1">
    <tr><th>PO ID</th><th>Vendor</th><th>Status</th><th>SKU</th><th>Description</th><th>Qty</th></tr>
    {rows}
    </table>
    </body></html>
    """

    pdf = HTML(string=html).write_pdf()
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": "inline; filename=purchase_orders.pdf"
    })

from datetime import datetime, timedelta

async def alert_stale_purchase_orders():
    await db.connect()
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    stale_pos = await db.purchaseorder.find_many(
        where={
            "status": "PENDING",
            "createdAt": {"lt": seven_days_ago}
        }
    )
    await db.disconnect()

    if stale_pos:
        emails = await get_admin_emails()
        for email in emails:
            await send_email(email, subject="Stale POs",
                body=f"{len(stale_pos)} purchase orders have been pending for over 7 days.")

from collections import defaultdict
from datetime import datetime

@router.get("/cogs/monthly")
async def monthly_cogs(user = Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    await db.connect()
    invoices = await db.vendorinvoice.find_many()
    await db.disconnect()

    result = defaultdict(lambda: defaultdict(float))
    for inv in invoices:
        key = inv.receivedAt.strftime("%Y-%m")
        result[key][inv.vendor] += inv.amount

    return [
        {"month": month, "vendors": dict(vendor_data)}
        for month, vendor_data in sorted(result.items(), reverse=True)
    ]
@router.get("/inventory/summary")
async def inventory_summary(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    parts = await db.part.find_many()
    await db.disconnect()

    total_value = sum(p.quantity * p.cost for p in parts)
    total_parts = len(parts)
    expired = sum(1 for p in parts if p.expiryDate and p.expiryDate < datetime.utcnow())

    return {
        "total_parts": total_parts,
        "expired_parts": expired,
        "expired_pct": round((expired / total_parts) * 100, 2) if total_parts else 0,
        "stock_value": round(total_value, 2)
    }

@router.get("/reports/po-kpis")
async def po_kpis(user = Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT", "MANAGER"])(user)

    now = datetime.utcnow()
    start = datetime(now.year, now.month, 1)

    await db.connect()
    this_month = await db.purchaseorderitem.find_many(
        where={"createdAt": {"gte": start}}
    )
    flagged = [i for i in this_month if i.invoiceOverageFlag or i.isDamaged or i.isMismatched]
    await db.disconnect()

    total = len(this_month)
    percent_flagged = round(len(flagged) / total * 100, 2) if total else 0

    return {
        "total_PO_items": total,
        "flagged_PO_items": len(flagged),
        "percent_flagged": percent_flagged
    }

@router.get("/reports/po-kpis")
async def po_kpis(user = Depends(get_current_user), alert: bool = False):
    require_role(["ADMIN", "ACCOUNTANT", "MANAGER"])(user)

    now = datetime.utcnow()
    start = datetime(now.year, now.month, 1)

    await db.connect()
    all_items = await db.purchaseorderitem.find_many(where={"createdAt": {"gte": start}})
    await db.disconnect()

    flagged = [i for i in all_items if i.invoiceOverageFlag or i.isDamaged or i.isMismatched]
    total = len(all_items)
    percent_flagged = round(len(flagged) / total * 100, 2) if total else 0

    if alert and percent_flagged > 10:
        await send_email(
            to="accounting@shop.com",
            subject="⚠️ Alert: High Percentage of Flagged POs",
            body=f"{percent_flagged}% of POs flagged this month. Please review."
        )

    return {
        "total_PO_items": total,
        "flagged_PO_items": len(flagged),
        "percent_flagged": percent_flagged
    }

@router.get("/reports/flagged-pos-by-vendor")
async def flagged_by_vendor(user = Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT", "MANAGER"])(user)

    await db.connect()
    items = await db.purchaseorderitem.find_many(
        where={
            "OR": [
                {"invoiceOverageFlag": True},
                {"isDamaged": True},
                {"isMismatched": True}
            ]
        },
        include={"po": True}
    )
    await db.disconnect()

    from collections import Counter
    count_by_vendor = Counter(i.po.vendor for i in items)

    return [{"vendor": v, "flagged": c} for v, c in count_by_vendor.items()]

@router.get("/reports/po-resolution-time")
async def po_resolution_kpi(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "ACCOUNTANT"])(user)

    await db.connect()
    items = await db.purchaseorderitem.find_many(where={
        "flaggedAt": {"not": None},
        "resolvedAt": {"not": None}
    })
    await db.disconnect()

    if not items:
        return {"avg_resolution_days": 0.0}

    from statistics import mean
    durations = [
        (i.resolvedAt - i.flaggedAt).total_seconds() / 86400
        for i in items if i.flaggedAt and i.resolvedAt
    ]

    return {"avg_resolution_days": round(mean(durations), 2)}

@router.get("/reports/vendor-delivery-performance")
async def vendor_delivery_performance(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    items = await db.purchaseorderitem.find_many(
        where={"deliveredAt": {"not": None}},
        include={"po": True}
    )
    await db.disconnect()

    from collections import defaultdict
    metrics = defaultdict(lambda: {"total": 0, "late": 0})

    for i in items:
        vendor = i.po.vendor
        metrics[vendor]["total"] += 1
        if i.wasLate:
            metrics[vendor]["late"] += 1

    return [
        {
            "vendor": vendor,
            "on_time_pct": round((1 - d["late"] / d["total"]) * 100, 2) if d["total"] else 0
        } for vendor, d in metrics.items()
    ]


from weasyprint import HTML
from fastapi.responses import StreamingResponse
from jinja2 import Template

@router.get("/audit/report.pdf")
async def export_audit_pdf(month: str, user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    start = datetime.strptime(month, "%Y-%m")
    end = start.replace(day=28) + timedelta(days=4)
    end = end.replace(day=1)

    await db.connect()
    logs = await db.warrantyaudit.find_many(
        where={"timestamp": {"gte": start, "lt": end}},
        include={"claim": True}
    )
    await db.disconnect()

    html_template = Template("""
    <h1>Audit Report – {{ month }}</h1>
    <table border="1" cellspacing="0" cellpadding="4">
      <tr><th>Date</th><th>Action</th><th>Actor</th><th>Claim ID</th><th>Detail</th></tr>
      {% for log in logs %}
      <tr>
        <td>{{ log.timestamp }}</td>
        <td>{{ log.action }}</td>
        <td>{{ log.actorId }}</td>
        <td>{{ log.claimId or '' }}</td>
        <td>{{ log.detail or '' }}</td>
      </tr>
      {% endfor %}
    </table>
    """)

    rendered = html_template.render(month=month, logs=logs)
    pdf = HTML(string=rendered).write_pdf()

    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=audit_{month}.pdf"}
    )

@router.get("/audit/stats")
async def audit_analytics(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    now = datetime.utcnow()
    start = now.replace(day=1)
    end = now

    await db.connect()
    logs = await db.warrantyaudit.find_many(
        where={"timestamp": {"gte": start, "lt": end}}
    )
    await db.disconnect()

    from collections import Counter
    by_action = Counter(log.action for log in logs)
    by_day = Counter(log.timestamp.date() for log in logs)

    return {
        "action_counts": dict(by_action),
        "daily_activity": dict(by_day)
    }

@router.get("/audit/logins/location-summary")
async def login_location_summary(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    logs = await db.warrantyaudit.find_many(
        where={"action": "LOGIN"},
        order={"timestamp": "desc"}
    )
    await db.disconnect()

    from collections import Counter
    locations = Counter()

    for log in logs:
        if log.detail:
            parts = log.detail.split("(")
            if len(parts) > 1:
                loc = parts[-1].rstrip(")")
                locations[loc.strip()] += 1

    return dict(locations)

@router.get("/me/security/logins")
async def my_login_history(user=Depends(get_current_user)):
    await db.connect()
    logs = await db.warrantyaudit.find_many(
        where={"actorId": user.id, "action": "LOGIN"},
        order={"timestamp": "desc"}
    )
    await db.disconnect()

    return [
        {
            "timestamp": log.timestamp,
            "location": log.detail or "Unknown"
        }
        for log in logs
    ]

@router.get("/audit/login-failures")
async def failed_login_stats(user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    await db.connect()
    logs = await db.warrantyaudit.find_many(where={"action": "LOGIN_FAILED"})
    await db.disconnect()

    from collections import Counter
    regions = Counter()

    for log in logs:
        loc = log.detail.split("(")[-1].strip(")") if "(" in log.detail else "Unknown"
        regions[loc] += 1

    return dict(regions)

@router.get("/audit/login-heatmap")
async def login_heatmap(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    logs = await db.warrantyaudit.find_many(where={"action": "LOGIN"})
    await db.disconnect()

    from collections import Counter
    matrix = Counter()
    for log in logs:
        dt = log.timestamp
        day = dt.strftime("%A")  # Monday, Tuesday, ...
        hour = dt.hour
        matrix[(day, hour)] += 1

    return [{"day": d, "hour": h, "count": c} for (d, h), c in matrix.items()]


@router.get("/reports/pnl")
async def profit_loss_report(user=Depends(get_current_user)):
    await db.connect()
    invoices = await db.invoice.find_many(include={"payments": True})
    vendor_bills = await db.vendorbill.find_many(where={"paid": True})
    await db.disconnect()

    revenue = sum(inv.total for inv in invoices)
    expenses = sum(b.amount for b in vendor_bills)
    cogs = 0  # to be summed from parts as implemented

    return {
        "revenue": revenue,
        "expenses": expenses,
        "gross_profit": revenue - cogs,
        "net_profit": revenue - (cogs + expenses)
    }

from collections import defaultdict
from datetime import datetime

@router.get("/reports/cash-flow")
async def cash_flow(user=Depends(get_current_user)):
    await db.connect()
    invoices = await db.invoice.find_many(include={"payments": True})
    bills = await db.vendorbill.find_many(where={"paid": True})
    await db.disconnect()

    inflow = defaultdict(float)
    outflow = defaultdict(float)

    for inv in invoices:
        month = inv.createdAt.strftime("%Y-%m")
        inflow[month] += inv.total

    for bill in bills:
        month = bill.createdAt.strftime("%Y-%m")
        outflow[month] += bill.amount

    all_months = sorted(set(inflow.keys()).union(outflow.keys()))

    return [
        {
            "month": m,
            "inflow": inflow.get(m, 0),
            "outflow": outflow.get(m, 0),
            "net": inflow.get(m, 0) - outflow.get(m, 0)
        } for m in all_months
    ]

@router.get("/reports/technicians/performance")
async def technician_performance(user=Depends(get_current_user)):
    await db.connect()
    items = await db.estimateitem.find_many(
        where={"hoursBilled": {"not": None}},
        include={"technician": True}
    )
    await db.disconnect()

    perf = {}
    for i in items:
        tech = i.technician
        if not tech:
            continue
        if tech.id not in perf:
            perf[tech.id] = {"name": tech.email, "hours": 0}
        perf[tech.id]["hours"] += i.hoursBilled

    return list(perf.values())

@router.get("/analytics/aro")
async def avg_repair_order(user=Depends(get_current_user)):
    await db.connect()
    invoices = await db.invoice.find_many()
    await db.disconnect()

    total = sum(i.total for i in invoices)
    count = len(invoices)
    return {"averageRepairOrder": round(total / count, 2) if count else 0}

@router.get("/analytics/top-customers")
async def top_customers(user=Depends(get_current_user)):
    await db.connect()
    invoices = await db.invoice.find_many(include={"estimate": {"include": {"vehicle": {"include": {"customer": True}}}}})
    await db.disconnect()

    spend = {}
    for inv in invoices:
        cust = inv.estimate.vehicle.customer
        spend[cust.id] = spend.get(cust.id, {"name": cust.email, "total": 0})
        spend[cust.id]["total"] += inv.total

    ranked = sorted(spend.values(), key=lambda x: x["total"], reverse=True)
    return ranked[:10]

@router.get("/audit-logs/export")
async def export_audit_logs(
    user_id: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    user=Depends(get_current_user)
):
    require_role(["ADMIN"])(user)
    filters = {}
    if user_id:
        filters["userId"] = user_id
    if start and end:
        filters["timestamp"] = {"gte": start, "lte": end}

    await db.connect()
    logs = await db.auditlog.find_many(where=filters, order={"timestamp": "desc"})
    await db.disconnect()

    return [
        {
            "timestamp": log.timestamp,
            "userId": log.userId,
            "action": log.action,
            "details": log.details,
            "ip": log.ip
        } for log in logs
    ]

@router.get("/reports/pnl")
async def profit_loss(start: date, end: date, user=Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)

    await db.connect()
    entries = await db.journalentry.find_many(
        where={"postedAt": {"gte": start, "lte": end}},
        include={"account": True}
    )
    await db.disconnect()

    revenue, expense = 0, 0
    for e in entries:
        if e.account.type == "REVENUE":
            revenue += e.amount if not e.debit else -e.amount
        elif e.account.type == "EXPENSE":
            expense += e.amount if e.debit else -e.amount

    return {
        "revenue": round(revenue, 2),
        "expenses": round(expense, 2),
        "netIncome": round(revenue - expense, 2)
    }

@router.get("/reports/balance-sheet")
async def balance_sheet(as_of: date, user=Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)

    await db.connect()
    entries = await db.journalentry.find_many(
        where={"postedAt": {"lte": as_of}},
        include={"account": True}
    )
    await db.disconnect()

    balances = {"ASSET": 0, "LIABILITY": 0, "EQUITY": 0}
    for e in entries:
        amt = e.amount if e.debit else -e.amount
        balances[e.account.type] += amt

    return balances

@router.get("/reports/tax-summary")
async def tax_summary(year: int, user=Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31)

    await db.connect()
    sales_tax = await db.invoice.aggregate(
        where={"postedAt": {"gte": start, "lte": end}},
        _sum={"tax": True}
    )
    expense_tax = await db.bill.aggregate(
        where={"postedAt": {"gte": start, "lte": end}},
        _sum={"tax": True}
    )
    await db.disconnect()

    return {
        "salesTaxCollected": round(sales_tax._sum.tax or 0, 2),
        "taxPaidOnExpenses": round(expense_tax._sum.tax or 0, 2)
    }

class MatchTxn(BaseModel):
    invoice_id: Optional[str]
    bill_id: Optional[str]

@router.post("/bank/transactions/{txn_id}/match")
async def match_transaction(txn_id: str, match: MatchTxn, user=Depends(get_current_user)):
    require_role(["ACCOUNTANT"])(user)

    data = {}
    if match.invoice_id:
        data["matchedInvoiceId"] = match.invoice_id
    if match.bill_id:
        data["matchedBillId"] = match.bill_id
    data["reconciled"] = True

    await db.connect()
    updated = await db.banktransaction.update(where={"id": txn_id}, data=data)
    await db.disconnect()

    return {"message": "Transaction matched", "transaction": updated}

@router.get("/bank/transactions/unmatched")
async def list_unmatched(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT"])(user)

    await db.connect()
    txns = await db.banktransaction.find_many(where={"reconciled": False})
    await db.disconnect()
    return txns

from weasyprint import HTML

@router.get("/reports/monthly/pdf")
async def monthly_report_pdf(month: int, year: int, user=Depends(get_current_user)):
    require_role(["ACCOUNTANT"])(user)

    start = datetime(year, month, 1)
    end = start + relativedelta(months=1)

    # Get revenue/expenses
    pnl = await profit_loss(start.date(), end.date(), user)

    html = f"""
    <h1>Monthly Report – {start.strftime('%B %Y')}</h1>
    <p>Revenue: ${pnl['revenue']}</p>
    <p>Expenses: ${pnl['expenses']}</p>
    <p>Net Income: ${pnl['netIncome']}</p>
    """

    pdf = HTML(string=html).write_pdf()
    return Response(content=pdf, media_type="application/pdf")


@router.get("/reports/technician-efficiency")
async def technician_efficiency(month: int, year: int, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    start = datetime(year, month, 1)
    end = start + relativedelta(months=1)

    await db.connect()
    appointments = await db.appointment.find_many(
        where={"startTime": {"gte": start, "lte": end}},
    )
    jobs = await db.jobitem.find_many(
        where={"createdAt": {"gte": start, "lte": end}},
    )
    await db.disconnect()

    workload = {}
    for appt in appointments:
        delta = (appt.endTime - appt.startTime).total_seconds() / 3600
        workload.setdefault(appt.technicianId, 0)
        workload[appt.technicianId] += delta

    billed = {}
    for job in jobs:
        billed.setdefault(job.technicianId, 0)
        billed[job.technicianId] += job.hoursBilled

    return [
        {
            "technicianId": tech,
            "hoursWorked": round(workload.get(tech, 0), 2),
            "hoursBilled": round(billed.get(tech, 0), 2),
            "efficiency": round((billed.get(tech, 0) / workload.get(tech, 1)) * 100, 1)
        }
        for tech in set(workload) | set(billed)
    ]


@router.get("/reports/payroll")
async def generate_payroll(start: datetime, end: datetime, user=Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)

    await db.connect()
    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    payroll = []

    for tech in techs:
        logs = await db.jobtimelog.find_many(
            where={
                "technicianId": tech.id,
                "startTime": {"gte": start, "lte": end},
                "endTime": {"not": None}
            }
        )
        total_hours = sum((l.endTime - l.startTime).total_seconds() for l in logs) / 3600
        total_pay = round(total_hours * (tech.hourlyRate or 0), 2)
        payroll.append({
            "technicianId": tech.id,
            "email": tech.email,
            "hoursWorked": round(total_hours, 2),
            "totalPay": total_pay
        })

    await db.disconnect()
    return payroll

import csv
from fastapi.responses import StreamingResponse
from io import StringIO

@router.get("/reports/payroll/export")
async def export_payroll_csv(start: datetime, end: datetime, user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)
    data = await generate_payroll(start, end, user)

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=payroll.csv"})

@router.get("/reports/expenses/summary")
async def expense_summary(start: datetime, end: datetime, user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    expenses = await db.vendorbill.group_by(
        by=["category"],
        where={"uploadedAt": {"gte": start, "lte": end}},
        _sum={"amount": True}
    )
    await db.disconnect()

    return [
        {"category": e["category"], "total": e["_sum"]["amount"]} for e in expenses
    ]

@router.get("/reports/sales-tax")
async def sales_tax_report(start: datetime, end: datetime, user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    invoices = await db.invoice.find_many(
        where={"createdAt": {"gte": start, "lte": end}, "status": "PAID"}
    )
    await db.disconnect()

    total_collected = sum(i.taxAmount for i in invoices)
    return {"period": f"{start.date()} - {end.date()}", "totalSalesTaxCollected": total_collected}

@router.get("/inventory/dead-stock")
async def dead_stock(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN", "INVENTORY"])(user)

    threshold = datetime.utcnow() - timedelta(days=90)

    await db.connect()
    parts = await db.part.find_many(where={
        "lastUsedAt": {"lt": threshold}
    })
    await db.disconnect()
    return parts

from weasyprint import HTML
from fastapi.responses import FileResponse

@router.get("/reports/profit/pdf")
async def export_profit_pdf(user=Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)

    summary = await profit(user)
    html = f"""
    <h1>Monthly Profit Summary</h1>
    <table>
      <tr><th>Month</th><th>Profit</th></tr>
      {''.join(f'<tr><td>{k}</td><td>${v}</td></tr>' for k,v in summary['monthlyProfit'].items())}
    </table>
    """
    path = "/tmp/profit-report.pdf"
    HTML(string=html).write_pdf(path)
    return FileResponse(path, filename="profit-report.pdf")

@router.get("/reports/tax/sales-tax")
async def sales_tax(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    invoices = await db.invoice.find_many(where={"status": "PAID"})
    await db.disconnect()

    by_state = {}
    for i in invoices:
        state = i.billingState or "UNKNOWN"
        by_state.setdefault(state, 0)
        by_state[state] += i.salesTax or 0

    return by_state

import csv

@router.get("/reports/vendor/1099")
async def export_1099(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    bills = await db.vendorbill.find_many()
    await db.disconnect()

    path = "/tmp/vendor-1099.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Vendor", "Total Paid"])
        vendors = {}
        for b in bills:
            vendors.setdefault(b.vendor, 0)
            vendors[b.vendor] += b.amount
        for v, amt in vendors.items():
            writer.writerow([v, amt])

    return FileResponse(path, filename="vendor-1099.csv")

@router.get("/analytics/technicians/{id}/performance")
async def technician_performance(id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    timers = await db.jobtimer.find_many(where={"technicianId": id, "endedAt": {"not": None}})
    estimates = await db.estimate.find_many(where={"technicianId": id})

    total_clocked = sum([(t.endedAt - t.startedAt).total_seconds() for t in timers]) / 3600  # in hours
    total_estimated = sum([e.estimatedHours for e in estimates]) if estimates else 0

    await db.disconnect()

    return {
        "technicianId": id,
        "clockedHours": round(total_clocked, 2),
        "estimatedHours": round(total_estimated, 2),
        "efficiency": round((total_estimated / total_clocked) * 100, 2) if total_clocked else 0
    }

@router.get("/analytics/revenue-calendar")
async def revenue_calendar(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "ACCOUNTANT"])(user)

    await db.connect()
    invoices = await db.invoice.find_many(where={"status": "PAID"})
    await db.disconnect()

    by_day = {}
    for i in invoices:
        day = i.paidAt.strftime("%Y-%m-%d")
        by_day.setdefault(day, 0)
        by_day[day] += i.total

    return by_day

@router.get("/reports/contracts/expiring")
async def contracts_expiring(days: int = 30, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    cutoff = datetime.utcnow() + timedelta(days=days)
    await db.connect()
    expiring = await db.vehiclecontract.find_many(where={"endDate": {"lte": cutoff}})
    await db.disconnect()
    return expiring
@router.get("/reports/work-time")
async def technician_work_report(
    start: datetime,
    end: datetime,
    user=Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    timers = await db.jobtimer.find_many(
        where={
            "startedAt": {"gte": start},
            "endedAt": {"lte": end}
        },
        include={"technician": True}
    )
    await db.disconnect()

    report = {}
    for t in timers:
        tech_id = t.technicianId
        duration = (t.endedAt - t.startedAt).total_seconds() / 3600
        if tech_id not in report:
            report[tech_id] = {
                "name": t.technician.email,
                "totalHours": 0,
                "entries": 0
            }
        report[tech_id]["totalHours"] += duration
        report[tech_id]["entries"] += 1

    return report
@router.get("/reports/reviews/technicians")
async def technician_review_summary(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    reviews = await db.review.find_many(include={"appointment": {"include": {"technician": True}}})
    await db.disconnect()

    summary = {}
    for review in reviews:
        tech_id = review.appointment.technicianId
        tech_name = review.appointment.technician.email
        if tech_id not in summary:
            summary[tech_id] = {"technician": tech_name, "ratings": [], "count": 0}
        summary[tech_id]["ratings"].append(review.rating)
        summary[tech_id]["count"] += 1

    for item in summary.values():
        item["average"] = round(sum(item["ratings"]) / item["count"], 2)

    return list(summary.values())

@router.get("/reports/revenue-by-category")
async def revenue_by_category(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    invoices = await db.invoice.find_many(include={"estimate": True})
    await db.disconnect()

    result = {}
    for inv in invoices:
        cat = inv.estimate.category or "UNCATEGORIZED"
        result.setdefault(cat, 0)
        result[cat] += float(inv.total)

    return result
