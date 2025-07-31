# backend/app/core/scheduler.py
## This file handles scheduled tasks such as sending appointment reminders and monthly vendor scorecards.
# It uses APScheduler to run tasks at specified intervals.
# It connects to the Prisma database to fetch appointments and vendors, and sends emails using the notifier module.
# Make sure to set the SMTP configuration in your environment variables.
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from app.core.notifier import send_email
from app.db.prisma_client import db

scheduler = AsyncIOScheduler()

async def send_appointment_reminders():
    await db.connect()
    now = datetime.utcnow()
    soon = now + timedelta(hours=24)

    appointments = await db.appointment.find_many(
        where={
            "startTime": {
                "gte": now,
                "lte": soon
            },
            "status": "SCHEDULED"
        },
        include={"customer": True}
    )

    for appt in appointments:
        await send_email(
            to_email=appt.customer.email,
            subject="Reminder: Upcoming Appointment",
            body=f"Reminder for your appointment '{appt.title}' on {appt.startTime.strftime('%Y-%m-%d %H:%M')}"
        )
    await db.disconnect()

def start():
    scheduler.add_job(send_appointment_reminders, IntervalTrigger(minutes=60))
    scheduler.start()

async def send_monthly_vendor_scorecards():
    await db.connect()
    vendors = await db.vendor.find_many()
    await db.disconnect()

    for vendor in vendors:
        # Reuse previous logic
        response = await export_vendor_scorecard_pdf(vendor.name, system_user)
        pdf = await response.body()

        await send_email(
            to=f"{vendor.name.lower()}@vendor.com",
            subject="📊 Monthly Vendor Scorecard",
            body="Attached is your performance report for the last 90 days.",
            attachments=[("scorecard.pdf", pdf)]
        )
scheduler.add_job(send_monthly_vendor_scorecards, 'cron', day=1, hour=6)
