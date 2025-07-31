# backend/app/notifications/routes.py
# This file contains notification routes for sending appointment reminders and other notifications.
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from app.core.notifier import send_sms, send_email

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.post("/reminders/run")
async def send_appointment_reminders():
    now = datetime.utcnow()
    soon = now + timedelta(hours=24)

    await db.connect()
    upcoming = await db.appointment.find_many(
        where={
            "startTime": {"gte": now, "lt": soon},
            "status": "SCHEDULED"
        },
        include={"customer": True}
    )
    await db.disconnect()

    for appt in upcoming:
        await send_sms(appt.customer.phone, f"Reminder: Appointment at {appt.startTime}")
        await send_email(appt.customer.email, "Appointment Reminder", f"You're scheduled for service at {appt.startTime}")
    
    return {"count": len(upcoming)}
