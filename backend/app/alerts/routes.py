# backend/app/alerts/routes.py
# This file contains alert routes for monitoring system health and notifying users of issues.
import smtplib
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta
from email.message import EmailMessage
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, require_role
from app.core.config import settings
from app.core.notifier import notify_slack, notify_user, send_email, send_sms
from app.db.prisma_client import db

router = APIRouter(prefix="/alerts", tags=["alerts"])

# Alerts and Notifications Endpoints 
# Alert for high substitution parts
# This will check for parts that have been substituted more than 3 times
@router.get("/alerts/high-substitution-parts")
async def substitution_procurement_alert(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    subs = await db.jobpart.find_many(where={"substituted": True})
    await db.disconnect()

    count = Counter([p.originalSku for p in subs if p.originalSku])
    high_subs = [sku for sku, c in count.items() if c >= 3]

    if high_subs:
        await notify_user(
            email="procurement@repairshop.com",
            subject="🚨 High Substitution Alert",
            body="These SKUs had frequent substitutions:\n" + "\n".join(high_subs)
        )

    return {"alerted_skus": high_subs}

# Alert for overutilized bays
# This will check if any bay has more than 10 jobs in a single day
@router.get("/alerts/overutilized-bays")
async def bay_overload_alert(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    jobs = await db.job.find_many()
    await db.disconnect()


    usage = defaultdict(lambda: defaultdict(int))  # bay -> date -> count
    for j in jobs:
        if j.bayId:
            day = j.createdAt.strftime("%Y-%m-%d")
            usage[j.bayId][day] += 1

    alerts = []
    for bay, days in usage.items():
        for date, count in days.items():
            if count > settings.MAX_BAY_JOBS_PER_DAY:
                alerts.append({"bay": bay, "date": date, "job_count": count})

    if alerts:
        await notify_user(
            email="manager@repairshop.com",
            subject="📈 Bay Overutilization Alert",
            body="\n".join(f"{a['bay']} on {a['date']}: {a['job_count']} jobs" for a in alerts)
        )

    return {"alerts": alerts}

# Alert for technician job overlap
# This will check if a technician has multiple jobs assigned on the same day
@router.get("/alerts/tech-overlap")
async def alert_tech_job_overlap(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    jobs = await db.job.find_many()
    await db.disconnect()


    overlap_alerts = []
    tech_jobs = defaultdict(list)

    for j in jobs:
        if j.technicianId:
            day = j.createdAt.strftime("%Y-%m-%d")
            tech_jobs[(j.technicianId, day)].append(j.bayId)

    for (tech, day), bays in tech_jobs.items():
        if len(set(bays)) > 1:
            overlap_alerts.append({
                "technician_id": tech,
                "date": day,
                "bays": list(set(bays))
            })

    return {"overlap_alerts": overlap_alerts}


async def notify_sla_breaches():
    SLA_HOURS = 48
    now = datetime.utcnow()

    await db.connect()
    claims = await db.warrantyclaim.find_many(
        where={"status": "OPEN", "firstResponseAt": None},
        include={"assignedTo": True}
    )
    await db.disconnect()

    for c in claims:
        hours_open = (now - c.createdAt).total_seconds() / 3600
        if hours_open > SLA_HOURS and c.assignedTo and c.assignedTo.email:
            await send_email(
                to=c.assignedTo.email,
                subject=f"SLA Breach Alert: Claim #{c.id}",
                body=f"Claim #{c.id} has exceeded the 48-hour SLA response window."
            )


async def check_failed_login_spike(threshold=20):
    today = datetime.utcnow().date()
    await db.connect()
    failures = await db.warrantyaudit.find_many(
        where={
            "action": "LOGIN_FAILED",
            "timestamp": {"gte": today}
        }
    )
    await db.disconnect()

    if len(failures) >= threshold:
        await send_email(
            to="admin@repairshop.local",
            subject="⚠️ Login Failures Spike Alert",
            body=f"{len(failures)} failed login attempts detected today."
        )

# Triggers appointment reminders for the next day
@router.post("/notifications/appointment-reminders")
async def send_appointment_reminders():
    tomorrow = datetime.utcnow().date() + timedelta(days=1)

    await db.connect()
    appts = await db.appointment.find_many(
        where={"startTime": {"gte": datetime.combine(tomorrow, time.min), "lte": datetime.combine(tomorrow, time.max)}},
        include={"customer": True}
    )
    await db.disconnect()

    for appt in appts:
        await send_sms(appt.customer.phone, f"Reminder: Your appointment is tomorrow at {appt.startTime.strftime('%H:%M')}")

    return {"notified": len(appts)}

# Alert for overdue invoices
# This will check for invoices that are overdue and not paid
@router.post("/notifications/invoice-overdue")
async def alert_overdue_invoices():
    today = datetime.utcnow().date()

    await db.connect()
    invoices = await db.invoice.find_many(
        where={"dueDate": {"lt": today}, "status": {"not": "PAID"}},
        include={"customer": True}
    )
    await db.disconnect()

    for inv in invoices:
        await send_email(inv.customer.email, "Invoice Overdue", f"Invoice {inv.id} is overdue. Please make payment.")

    return {"alertsSent": len(invoices)}

async def alert_low_stock():
    await db.connect()
    low_parts = await db.part.find_many(where={"quantityOnHand": {"lte": "minThreshold"}})
    await db.disconnect()

    if low_parts:
        part_list = "\n".join([f"{p.sku}: {p.description} - {p.quantityOnHand}" for p in low_parts])
        await send_email(
            to_email="manager@shop.com",
            subject="Low Stock Alert",
            body=f"The following parts are below minimum:\n{part_list}",
        )
        await send_sms("+12223334444", "Parts stock low. Check email for details.")
        await notify_slack("#inventory", f"🚨 Low stock detected:\n{part_list}")



def send_report_email(to: str, subject: str, attachment_path: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["To"] = to
    msg["From"] = "reports@repairshop.com"

    msg.set_content("Attached is your financial report.")
    with open(attachment_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename="report.pdf")

    with smtplib.SMTP("localhost") as s:
        s.send_message(msg)

async def alert_on_low_inventory():
    await db.connect()
    low_parts = await db.part.find_many(where={
        "quantity": {"lte": {"path": "$.alertThreshold"}},
        "alertSent": False
    })
    for p in low_parts:
        await send_sms("+15551234567", f"Inventory Low: Part {p.sku} is below threshold")
        await db.part.update(where={"id": p.id}, data={"alertSent": True})
    await db.disconnect()

def send_tech_summary_email(tech_email: str, summary: dict):
    body = f"You have {summary['count']} job(s) scheduled today.\n\n"
    for job in summary["jobs"]:
        body += f"- {job['type']} at {job['scheduledAt']}\n"

    msg = EmailMessage()
    msg["To"] = tech_email
    msg["Subject"] = "Daily Work Summary"
    msg.set_content(body)
    with smtplib.SMTP("localhost") as s:
        s.send_message(msg)

async def send_followups():
    now = datetime.utcnow()
    upcoming = now + timedelta(days=1)

    await db.connect()
    estimates = await db.estimate.find_many(where={
        "expiresAt": {"lte": upcoming},
        "approvedAt": None,
        "followUpSent": False
    })

    for est in estimates:
        customer = await db.customer.find_unique(where={"id": est.customerId})
        await send_email(
            to_email=customer.email,
            subject="Estimate expiring soon",
            body=(
                f"Your estimate #{est.id} will expire on {est.expiresAt.date()}. "
                "Contact us with questions."
            ),
        )
        await db.estimate.update(where={"id": est.id}, data={"followUpSent": True})
    await db.disconnect()


class BannerIn(BaseModel):
    message: str
    level: str  # INFO / WARNING / CRITICAL
    expiresAt: Optional[datetime]

@router.post("/notices")
async def create_banner(data: BannerIn, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    banner = await db.notificationbanner.create(data=data.dict())
    await db.disconnect()
    return {"message": "Banner created", "banner": banner}

@router.get("/notices/active")
async def get_active_banners():
    now = datetime.utcnow()
    await db.connect()
    banners = await db.notificationbanner.find_many(
        where={
            "active": True,
            "OR": [
                {"expiresAt": None},
                {"expiresAt": {"gte": now}}
            ]
        },
        order={"createdAt": "desc"}
    )
    await db.disconnect()
    return banners

async def send_service_reminders():
    await db.connect()

    vehicles = await db.vehicle.find_many()
    reminders = []

    for v in vehicles:
        contracts = await db.vehiclecontract.find_many(
            where={
                "vehicleId": v.id,
                "endDate": {"gte": datetime.utcnow()},
                "visitsUsed": {"lt": 999}
            }
        )
        if contracts:
            mileage_due = v.mileage and v.mileage % 5000 < 300  # approx. every 5K
            if mileage_due:
                last_sent = v.lastReminderAt or datetime(2000, 1, 1)
                if (datetime.utcnow() - last_sent).days >= 30:
                    customer = await db.customer.find_unique(where={"id": v.customerId})
                    await send_email(
                        customer.email,
                        "Service Reminder",
                        f"Your vehicle {v.make} {v.model} is due for service.",
                    )
                    await send_sms(customer.phone, "Your car is due for service. Book now.")
                    reminders.append(v.id)

    for vid in reminders:
        await db.vehicle.update(where={"id": vid}, data={"lastReminderAt": datetime.utcnow()})

    await db.disconnect()
