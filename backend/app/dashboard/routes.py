# File dashboard/routes.py
# This file contains dashboard routes for different user roles, including technicians, customers, and admins.

from fastapi import APIRouter, Depends, Query
from collections import Counter
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Query
from fastapi.responses import StreamingResponse
from io import StringIO
from statistics import mean
import csv
import datetime
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# Dashboard routes for different user roles
@router.get("/dashboard")
async def technician_dashboard(user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()

    jobs = await db.job.find_many(where={"technicianId": user.id})
    active_logs = await db.jobtimelog.find_many(
        where={"techId": user.id, "endedAt": None},
        include={"job": True}
    )

    timers = []
    for log in active_logs:
        duration = (datetime.utcnow() - log.startedAt).total_seconds()
        timers.append({
            "jobId": log.jobId,
            "startedAt": log.startedAt,
            "elapsedSeconds": int(duration),
            "jobTitle": log.job.title if log.job else None
        })

    await db.disconnect()
    return {
        "assigned_jobs": jobs,
        "active_timers": timers
    }

# This route provides a dashboard for customers to view their vehicles, estimates, and invoices.
@router.get("/dashboard")
async def customer_dashboard(user = Depends(get_current_user)):
    await db.connect()
    vehicles = await db.vehicle.find_many(where={"ownerId": user.id})
    estimates = await db.estimate.find_many(where={"customerId": user.id})
    invoices = await db.invoice.find_many(where={"customerId": user.id})
    await db.disconnect()

    return {
        "vehicles": vehicles,
        "estimates": estimates,
        "invoices": invoices
    }
# This route provides a summary dashboard for admins and managers.
@router.get("/admin/summary")
async def dashboard_summary(
    job_status: Optional[str] = Query(None),
    overdue_only: bool = False,
    technician_id: Optional[str] = None,
    user = Depends(get_current_user)
):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()

    # Jobs
    job_filters = {}
    if job_status:
        job_filters["status"] = job_status
    if technician_id:
        job_filters["technicianId"] = technician_id
    open_jobs = await db.job.find_many(where=job_filters)

    # Overdue invoices
    invoice_filters = {}
    if overdue_only:
        invoice_filters = {
            "dueDate": {"lt": datetime.utcnow()},
            "status": {"not": "PAID"}
        }
    overdue_invoices = await db.invoice.find_many(where=invoice_filters)

    # Parts low in stock
    parts = await db.part.find_many()
    low_stock_parts = [p for p in parts if p.reorderMin and p.quantity < p.reorderMin]

    await db.disconnect()
    return {
        "open_jobs": len(open_jobs),
        "overdue_invoices": len(overdue_invoices),
        "parts_to_reorder": len(low_stock_parts)
    }
# This route provides a performance overview for technicians.
@router.get("/admin/technicians/performance")
async def technician_efficiency(user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()

    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    jobs = await db.job.find_many()
    logs = await db.jobtimelog.find_many()

    result = {}
    for tech in techs:
        billed = sum(j.billedHours for j in jobs if j.technicianId == tech.id)
        time_logs = [l for l in logs if l.techId == tech.id and l.endedAt]
        actual = sum((l.endedAt - l.startedAt).total_seconds() / 3600 for l in time_logs)
        efficiency = round(billed / actual * 100, 2) if actual else 0

        result[tech.email] = {
            "billed_hours": billed,
            "actual_hours": round(actual, 2),
            "efficiency_percent": efficiency
        }

    await db.disconnect()
    return result
# This route provides a cost of goods sold (COGS) report for the admin.
@router.get("/admin/financials/breakdown")
async def revenue_breakdown(user = Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    await db.connect()

    invoices = await db.invoice.find_many(include={"items": True})
    labor_total = 0
    parts_total = 0

    for inv in invoices:
        for item in inv.items:
            if item.type == "LABOR":
                labor_total += item.amount
            elif item.type == "PART":
                parts_total += item.amount

    await db.disconnect()
    return {
        "labor_revenue": labor_total,
        "parts_revenue": parts_total,
        "total_revenue": labor_total + parts_total
    }

# This route provides a financial report for the admin.
@router.get("/admin/job-margins")
async def job_margin_kpi(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    jobs = await db.job.find_many(include={"invoice": True})
    logs = await db.jobtimelog.find_many()
    parts = await db.partusage.find_many()

    job_cost_map = {}
    for job in jobs:
        part_cost = sum(p.cost * p.quantity for p in parts if p.jobId == job.id)
        labor_hours = sum(
            (l.endedAt - l.startedAt).total_seconds() / 3600
            for l in logs if l.jobId == job.id and l.endedAt
        )
        labor_cost = labor_hours * 25
        cost = part_cost + labor_cost
        revenue = job.invoice.total if job.invoice else 0
        if revenue:
            job_cost_map[job.id] = (revenue, cost)

    margin_list = [
        (rev - cost) / rev * 100
        for rev, cost in job_cost_map.values()
        if rev > 0
    ]

    avg_margin = round(sum(margin_list) / len(margin_list), 2) if margin_list else 0
    await db.disconnect()
    return {"average_margin_percent": avg_margin}
# This route provides a cost of goods sold (COGS) report for the admin.
@router.get("/admin/job-margins")
async def job_margin_kpi(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    jobs = await db.job.find_many(include={"invoice": True})
    logs = await db.jobtimelog.find_many()
    parts = await db.partusage.find_many()

    job_cost_map = {}
    for job in jobs:
        part_cost = sum(p.cost * p.quantity for p in parts if p.jobId == job.id)
        labor_hours = sum(
            (l.endedAt - l.startedAt).total_seconds() / 3600
            for l in logs if l.jobId == job.id and l.endedAt
        )
        labor_cost = labor_hours * 25
        cost = part_cost + labor_cost
        revenue = job.invoice.total if job.invoice else 0
        if revenue:
            job_cost_map[job.id] = (revenue, cost)

    margin_list = [
        (rev - cost) / rev * 100
        for rev, cost in job_cost_map.values()
        if rev > 0
    ]

    avg_margin = round(sum(margin_list) / len(margin_list), 2) if margin_list else 0
    await db.disconnect()
    return {"average_margin_percent": avg_margin}

# This route provides a summary of parts scanned by technicians.
@router.get("/tech/parts-summary")
async def parts_scanned_summary(user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = today_start - timedelta(days=now.weekday())

    today_logs = await db.inventoryevent.find_many(
        where={"userId": user.id, "timestamp": {"gte": today_start}, "type": "RECEIVE"}
    )

    week_logs = await db.inventoryevent.find_many(
        where={"userId": user.id, "timestamp": {"gte": week_start}, "type": "RECEIVE"}
    )

    await db.disconnect()

    return {
        "parts_received_today": sum(log.quantity for log in today_logs),
        "parts_received_week": sum(log.quantity for log in week_logs),
        "events_today": len(today_logs),
        "events_week": len(week_logs)
    }


# This route exports inventory events as a CSV file.
@router.get("/inventory-events/export")
async def export_inventory_events_csv(
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    events = await db.inventoryevent.find_many(include={"part": True})
    await db.disconnect()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "User ID", "Event Type", "Part Name", "SKU", "Quantity", "Location", "Note"])

    for e in events:
        writer.writerow([
            e.timestamp.isoformat(),
            e.userId,
            e.type,
            e.part.name if e.part else "-",
            e.part.sku if e.part else "-",
            e.quantity,
            e.location,
            e.note or ""
        ])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=inventory_events.csv"
    })
# This route retrieves detailed inventory events with part information.
@router.get("/inventory-events/detailed")
async def detailed_inventory_events(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    events = await db.inventoryevent.find_many(include={"part": True})
    await db.disconnect()

    return [
        {
            "timestamp": e.timestamp,
            "type": e.type,
            "quantity": e.quantity,
            "location": e.location,
            "note": e.note,
            "part": {
                "name": e.part.name if e.part else None,
                "sku": e.part.sku if e.part else None,
                "vendor": e.part.vendor if e.part else None
            },
            "userId": e.userId
        }
        for e in events
    ]
# This route allows managers to mark part requests as filled.
@router.post("/part-requests/{request_id}/mark-filled")
async def mark_filled(request_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    updated = await db.partrequest.update(
        where={"id": request_id},
        data={"filledAt": datetime.utcnow()}
    )
    await db.disconnect()
    return {"message": "Marked as filled", "request": updated}
# This route retrieves the fill rate KPI for part requests.
@router.get("/kpis/fill-rate")
async def fill_rate_kpi(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    requests = await db.partrequest.find_many(where={"status": "APPROVED", "filledAt": {"not": None}})
    timely = [r for r in requests if (r.filledAt - r.createdAt).total_seconds() <= 48 * 3600]
    rate = round(len(timely) / len(requests) * 100, 2) if requests else 0

    await db.disconnect()
    return {"fill_rate_percent": rate}
# This route allows managers to list part requests with optional filters.
@router.get("/part-requests/filtered")
async def list_part_requests_filtered(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)
    filters = {}
    if status:
        filters["status"] = status.upper()
    if user_id:
        filters["userId"] = user_id

    await db.connect()
    total = await db.partrequest.count(where=filters)
    requests = await db.partrequest.find_many(
        where=filters,
        skip=skip,
        take=limit,
        order={"createdAt": "desc"}
    )
    await db.disconnect()

    return {"total": total, "items": requests}

# This route retrieves the fill rate trend for part requests over time.
@router.get("/kpis/fill-rate/trend")
async def fill_rate_trend(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    requests = await db.partrequest.find_many(
        where={"status": "APPROVED", "filledAt": {"not": None}},
        order={"createdAt": "asc"}
    )
    await db.disconnect()

    trend = defaultdict(lambda: {"filled": 0, "timely": 0})
    for r in requests:
        key = r.createdAt.strftime("%Y-%m")
        trend[key]["filled"] += 1
        if (r.filledAt - r.createdAt).total_seconds() <= 48 * 3600:
            trend[key]["timely"] += 1

    return [
        {
            "month": month,
            "fill_rate_percent": round((data["timely"] / data["filled"]) * 100, 2)
        }
        for month, data in sorted(trend.items())
    ]

# This route retrieves unacknowledged part requests by technicians.
@router.get("/tech/unacknowledged")
async def unacknowledged_requests_summary(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    requests = await db.partrequest.find_many(
        where={
            "status": "APPROVED",
            "acknowledgedAt": None
        }
    )

    summary = {}
    for r in requests:
        summary[r.userId] = summary.get(r.userId, 0) + 1

    # Optionally enrich with user info
    users = await db.user.find_many(where={"id": {"in": list(summary.keys())}})
    await db.disconnect()

    return [
        {
            "technician": u.email,
            "open_requests": summary[u.id]
        } for u in users
    ]

# This route retrieves the number of parts used per technician.
@router.get("/kpis/parts-per-tech")
async def parts_per_technician(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    parts = await db.jobpart.find_many(where={"used": True})
    users = await db.user.find_many()

    summary = {}
    for u in users:
        summary[u.id] = {
            "email": u.email,
            "total_parts": 0,
            "total_quantity": 0
        }

    for p in parts:
        if p.jobId:
            job = await db.job.find_unique(where={"id": p.jobId})
            if job and job.technicianId in summary:
                summary[job.technicianId]["total_parts"] += 1
                summary[job.technicianId]["total_quantity"] += p.quantity

    await db.disconnect()
    return list(summary.values())

# This route retrieves the average time taken to complete parts.
@router.get("/kpis/part-completion-time")
async def part_completion_kpi(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    parts = await db.jobpart.find_many(
        where={"assignedAt": {"not": None}, "usedAt": {"not": None}}
    )
    await db.disconnect()

    durations = [
        (p.usedAt - p.assignedAt).total_seconds() / 3600
        for p in parts if p.usedAt > p.assignedAt
    ]

    avg_hours = round(mean(durations), 2) if durations else 0

    return {"average_completion_hours": avg_hours, "count": len(durations)}

# This route retrieves technician performance data for the dashboard.
@router.get("/dashboard/tech-performance")
async def tech_dashboard_data(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    jobs = await db.job.find_many()
    parts = await db.jobpart.find_many()

    await db.disconnect()
    
    stats = defaultdict(lambda: {"jobs": 0, "parts": 0, "subs": 0})

    for j in jobs:
        stats[j.technicianId]["jobs"] += 1
    for p in parts:
        job = next((j for j in jobs if j.id == p.jobId), None)
        if job:
            stats[job.technicianId]["parts"] += 1
            if p.substituted:
                stats[job.technicianId]["subs"] += 1

    return [
        {
            "technician": t.email,
            "jobs_completed": stats[t.id]["jobs"],
            "parts_installed": stats[t.id]["parts"],
            "substitutions": stats[t.id]["subs"]
        }
        for t in techs
    ]

# This route retrieves filtered technician performance data for the dashboard.
@router.get("/dashboard/tech-performance/filtered")
async def tech_dashboard_filtered(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bay_id: Optional[str] = None,
    job_type: Optional[str] = None,
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    jobs = await db.job.find_many()
    parts = await db.jobpart.find_many()

    await db.disconnect()

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    stats = defaultdict(lambda: {"jobs": 0, "parts": 0, "subs": 0})

    for j in jobs:
        if start and j.createdAt < start:
            continue
        if end and j.createdAt > end:
            continue
        if bay_id and j.bayId != bay_id:
            continue
        if job_type and j.type != job_type:
            continue
        stats[j.technicianId]["jobs"] += 1

    for p in parts:
        job = next((j for j in jobs if j.id == p.jobId), None)
        if job:
            stats[job.technicianId]["parts"] += 1
            if p.substituted:
                stats[job.technicianId]["subs"] += 1

    return [
        {
            "technician": t.email,
            "jobs_completed": stats[t.id]["jobs"],
            "parts_installed": stats[t.id]["parts"],
            "substitutions": stats[t.id]["subs"]
        }
        for t in techs
    ]

# This route flags technicians with high substitution counts.
@router.get("/dashboard/tech-flag/substitution")
async def flag_high_subs(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    parts = await db.jobpart.find_many(where={"substituted": True})
    jobs = await db.job.find_many()

    await db.disconnect()

    job_map = {j.id: j.technicianId for j in jobs}
    counts = Counter([job_map[p.jobId] for p in parts if p.jobId in job_map])

    flagged = []
    for t in techs:
        if counts[t.id] >= 5:  # arbitrary flag threshold
            flagged.append({
                "technician": t.email,
                "substitution_count": counts[t.id]
            })

    return {"flagged_techs": flagged}

# This route retrieves the install time trend for job parts.
@router.get("/kpis/install-time-trend")
async def install_time_trend(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    parts = await db.jobpart.find_many(
        where={"assignedAt": {"not": None}, "usedAt": {"not": None}}
    )
    await db.disconnect()

    trends = defaultdict(list)

    for p in parts:
        if p.usedAt > p.assignedAt:
            key = p.usedAt.strftime("%Y-%m")
            duration = (p.usedAt - p.assignedAt).total_seconds() / 3600
            trends[key].append(duration)

    results = [
        {"month": month, "average_install_hours": round(sum(times) / len(times), 2)}
        for month, times in sorted(trends.items())
    ]

    return results

# This route exports technician performance data as a CSV file.
@router.get("/export/tech-performance")
async def export_tech_performance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    job_type: Optional[str] = None,
    bay_id: Optional[str] = None,
    user = Depends(get_current_user)
):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    jobs = await db.job.find_many()
    parts = await db.jobpart.find_many()
    await db.disconnect()

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    stats = defaultdict(lambda: {"jobs": 0, "parts": 0, "subs": 0})

    for j in jobs:
        if start and j.createdAt < start:
            continue
        if end and j.createdAt > end:
            continue
        if bay_id and j.bayId != bay_id:
            continue
        if job_type and j.type != job_type:
            continue
        stats[j.technicianId]["jobs"] += 1

    for p in parts:
        job = next((j for j in jobs if j.id == p.jobId), None)
        if job and job.technicianId in stats:
            stats[job.technicianId]["parts"] += 1
            if p.substituted:
                stats[job.technicianId]["subs"] += 1

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Technician", "Jobs", "Parts Installed", "Substitutions"])
    for t in techs:
        data = stats[t.id]
        writer.writerow([t.email, data["jobs"], data["parts"], data["subs"]])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=tech_performance.csv"
    })
    
# This route retrieves technician performance data with reviews.
@router.get("/dashboard/tech-performance/with-reviews")
async def tech_performance_with_reviews(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    reviews = await db.userreview.find_many()
    await db.disconnect()

    notes = defaultdict(list)
    for r in reviews:
        notes[r.techId].append({
            "note": r.note,
            "by": r.reviewerId,
            "date": r.createdAt
        })

    return [
        {
            "technician": t.email,
            "reviews": notes.get(t.id, [])
        } for t in techs
    ]
    
# This route retrieves technician performance data filtered by role.
@router.get("/dashboard/tech-performance/role-filtered")
async def tech_dashboard_by_role(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    jobs = await db.job.find_many()
    parts = await db.jobpart.find_many()
    await db.disconnect()

    if user.role == "MANAGER" and user.assignedBay:
        jobs = [j for j in jobs if j.bayId == user.assignedBay]
        parts = [p for p in parts if any(j.id == p.jobId and j.bayId == user.assignedBay for j in jobs)]

    # Build summary as before...

    return [...summary...]

# This route retrieves bay utilization data for KPIs.
@router.get("/kpis/bay-utilization")
async def bay_utilization(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    jobs = await db.job.find_many()
    await db.disconnect()

    utilization = defaultdict(lambda: defaultdict(int))

    for job in jobs:
        if job.bayId and job.createdAt:
            key = job.createdAt.strftime("%Y-%m")
            utilization[key][job.bayId] += 1

    return [
        {"month": month, "bays": dict(counts)}
        for month, counts in sorted(utilization.items())
    ]

# This route retrieves a heatmap of bay usage by day and hour.
@router.get("/kpis/bay-heatmap")
async def bay_usage_heatmap(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    jobs = await db.job.find_many()
    await db.disconnect()

    heatmap = defaultdict(lambda: defaultdict(int))  # weekday -> hour -> count

    for job in jobs:
        dt = job.createdAt
        weekday = dt.strftime("%A")  # e.g. 'Monday'
        hour = dt.hour
        heatmap[weekday][hour] += 1

    return [
        {"day": day, "hourly": dict(hourly)}
        for day, hourly in heatmap.items()
    ]

# This route allows technicians to create warranty claims.
@router.get("/warranty")
async def list_all_claims(
    status: Optional[str] = None,
    user=Depends(get_current_user)
):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK"])(user)

    await db.connect()
    where_clause = {"status": status.upper()} if status else {}
    claims = await db.warrantyclaim.find_many(
        where=where_clause,
        include={"customer": True, "workOrder": True},
        order={"createdAt": "desc"}
    )
    await db.disconnect()
    return claims

class ClaimCreate(BaseModel):
    work_order_id: str
    description: str
    invoice_item_ids: Optional[List[str]] = []
    
# This route allows technicians to create a new warranty claim.
    @router.get("/warranty/{claim_id}")
async def get_claim_detail(claim_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK"])(user)

    await db.connect()
    claim = await db.warrantyclaim.find_unique(where={"id": claim_id}, include={"customer": True, "workOrder": True})
    comments = await db.warrantyclaimcomment.find_many(
        where={"claimId": claim_id},
        order={"createdAt": "asc"}
    )
    await db.disconnect()

    return {
        "claim": claim,
        "comments": comments
    }

@router.get("/users")
async def list_users(...):
    ...
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "isActive": u.isActive,
            "twoFactorEnabled": u.twoFactorEnabled
        } for u in users
    ]

@router.get("/dashboard/summary")
async def dashboard_summary(user=Depends(get_current_user)):
    await db.connect()
    customers = await db.customer.count()
    vehicles = await db.vehicle.count(where={"isArchived": False})
    invoices = await db.invoice.find_many()
    appointments = await db.appointment.find_many(where={"status": "SCHEDULED"})
    await db.disconnect()

    total_revenue = sum(i.total for i in invoices)
    average_repair = total_revenue / len(invoices) if invoices else 0

    return {
        "customerCount": customers,
        "activeVehicles": vehicles,
        "scheduledAppointments": len(appointments),
        "totalRevenue": round(total_revenue, 2),
        "averageRepairOrder": round(average_repair, 2)
    }


@router.get("/bays/schedule")
async def bay_schedule(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    today = datetime.utcnow().date()

    await db.connect()
    bays = await db.bay.find_many(include={"currentAppointment": True})
    await db.disconnect()

    return [
        {
            "bay": bay.name,
            "occupied": bay.inUse,
            "appointment": bay.currentAppointment
        }
        for bay in bays
    ]

@router.get("/dashboard/tech-kpis")
async def tech_dashboard_summary(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    data = []

    for tech in techs:
        jobs = await db.jobitem.find_many(where={"technicianId": tech.id})
        if not jobs:
            continue
        avg_rating = sum(j.customerRating or 0 for j in jobs) / len(jobs)
        billed = sum(j.hoursBilled for j in jobs)
        commission = sum(j.commission or 0 for j in jobs)

        data.append({
            "technicianId": tech.id,
            "name": tech.email,
            "avgRating": round(avg_rating, 2),
            "totalBilledHours": round(billed, 2),
            "totalCommission": round(commission, 2),
        })

    await db.disconnect()
    return data

@router.get("/dashboard/labor")
async def labor_metrics_summary(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()

    jobs = await db.jobitem.find_many()
    total_billed = sum(j.hoursBilled for j in jobs)
    total_cost = sum(j.laborCost or 0 for j in jobs)

    await db.disconnect()
    return {
        "totalBilledHours": round(total_billed, 2),
        "totalLaborCost": round(total_cost, 2),
        "efficiencyRatio": round(total_billed / total_cost, 2) if total_cost else None
    }

@router.get("/dashboard/job-progress")
async def job_progress(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    clocks = await db.jobclock.find_many(
        where={"clockOut": None},
        include={"appointment": True}
    )
    await db.disconnect()

    return [{
        "technicianId": c.technicianId,
        "jobId": c.appointmentId,
        "clockIn": c.clockIn,
        "elapsedMinutes": (datetime.utcnow() - c.clockIn).total_seconds() // 60,
        "appointment": c.appointment
    } for c in clocks]

@router.get("/dashboard/tech-efficiency")
async def tech_efficiency(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    result = []

    for tech in techs:
        jobs = await db.jobclock.find_many(where={"technicianId": tech.id})
        total_minutes = sum(
            (j.clockOut - j.clockIn).total_seconds() / 60 for j in jobs if j.clockOut
        )

        billed_minutes = await db.appointment.aggregate(_sum={"duration": True}, where={
            "technicianId": tech.id
        })

        result.append({
            "technicianId": tech.id,
            "name": tech.email,
            "clockedMinutes": total_minutes,
            "billedMinutes": billed_minutes["_sum"]["duration"] or 0,
            "efficiencyPercent": round(
                (billed_minutes["_sum"]["duration"] or 0) / total_minutes * 100, 2
            ) if total_minutes else 0
        })

    await db.disconnect()
    return result

@router.get("/dashboard/return-jobs")
async def return_jobs(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    jobs = await db.appointment.find_many()

    visit_map = {}
    for job in jobs:
        key = f"{job.vehicleId}_{job.type.lower()}"
        visit_map.setdefault(key, []).append(job)

    repeated = {
        k: v for k, v in visit_map.items() if len(v) > 1 and (v[-1].scheduledAt - v[-2].scheduledAt).days < 30
    }

    await db.disconnect()
    return repeated

@router.get("/dashboard/finance/cashflow")
async def cashflow_summary(user=Depends(get_current_user)):
    require_role(["ADMIN", "ACCOUNTANT"])(user)

    today = datetime.utcnow()
    start = datetime(today.year, today.month - 2, 1)

    await db.connect()
    invoices = await db.invoice.find_many(where={"createdAt": {"gte": start}})
    expenses = await db.vendorbill.find_many(where={"date": {"gte": start}})
    await db.disconnect()

    summary = {"monthly": {}}
    for i in range(3):
        month = (today.month - i - 1) % 12 + 1
        key = f"{today.year}-{month:02d}"
        summary["monthly"][key] = {
            "income": sum(i.totalAmount for i in invoices if i.createdAt.month == month),
            "expenses": sum(e.amount for e in expenses if e.date.month == month)
        }

    return summary

@router.get("/dashboard/finance/net-profit")
async def profit(user=Depends(get_current_user)):
    ...
    net = {m: d["income"] - d["expenses"] for m, d in summary["monthly"].items()}
    return {"monthlyProfit": net}

@router.get("/dashboard/mobile/overview")
async def mobile_overview(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    today = datetime.utcnow().date()
    start = datetime(today.year, today.month, today.day)
    end = start + timedelta(days=1)

    await db.connect()
    jobs_today = await db.appointment.count(where={
        "scheduledAt": {"gte": start, "lt": end}
    })
    pending_estimates = await db.estimate.count(where={"approvedAt": None})
    open_warranty = await db.warrantyclaim.count(where={"status": "PENDING"})
    await db.disconnect()

    return {
        "jobsToday": jobs_today,
        "pendingEstimates": pending_estimates,
        "openWarrantyClaims": open_warranty,
    }


@router.get("/dashboard/load")
async def current_load(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN", "FRONT-DESK"])(user)

    today = datetime.utcnow().date()
    await db.connect()
    bays = await db.bay.find_many(where={"isActive": True})
    techs = await db.user.find_many(where={"role": "TECHNICIAN"})

    appointments = await db.appointment.find_many(
        where={
            "scheduledAt": {
                "gte": datetime(today.year, today.month, today.day),
                "lt": datetime(today.year, today.month, today.day + 1)
            }
        }
    )
    await db.disconnect()

    return {
        "bays": [{
            "id": b.id,
            "label": b.label,
            "inUse": any(a.bayId == b.id for a in appointments)
        } for b in bays],
        "technicians": [{
            "id": t.id,
            "email": t.email,
            "assignments": sum(1 for a in appointments if a.technicianId == t.id)
        } for t in techs]
    }

@router.get("/dashboard/admin")
async def admin_dashboard(user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    await db.connect()
    totals = {
        "users": await db.user.count(),
        "customers": await db.customer.count(),
        "appointments": await db.appointment.count(),
        "revenue": sum(inv.total for inv in await db.invoice.find_many())
    }
    await db.disconnect()
    return totals

@router.get("/dashboard/technician")
async def tech_dashboard(user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()
    today = datetime.utcnow().date()
    queue = await db.appointment.find_many(
        where={
            "technicianId": user.id,
            "scheduledAt": {"gte": today.isoformat()}
        }
    )
    await db.disconnect()
    return {"appointmentsToday": len(queue), "appointments": queue}
