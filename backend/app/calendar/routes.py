## File: backend/app/bank/routes.py
## This file contains routes for managing bank transactions, including creating and uploading transactions.
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from datetime import datetime
from app.auth.dependencies import get_current_user, require_role, require_role, get_current_user
from app.db.prisma_client import db
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi import HTTPException
from fastapi.responses import Response
from ics import Calendar, Event
from pydantic import BaseModel
from typing import Optional
import csv
import os
import uuid

router = APIRouter(prefix="/bank", tags=["bank"])

# Vendor Bills Management Endpoints
@router.post("/vendor-bills")
async def record_vendor_bill(data: VendorBillCreate, user = Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)
    await db.connect()
    bill = await db.vendorbill.create(data.dict())
    await db.disconnect()
    return {"message": "Vendor bill recorded", "bill": bill}


# Calendar Webhook Endpoint
# This will handle incoming webhooks from calendar providers (Google, Outlook)
# It will update the appointment status based on the event ID and provider
# The payload structure is expected to be:
# {
#   "event_id": "abc123",
#   "status": "cancelled" | "updated",      # The status of the event
#   "provider": "GOOGLE" | "OUTLOOK"         # The calendar provider
# }
@router.post("/calendar/webhook")
async def calendar_webhook(request: Request):
    payload = await request.json()

    # Example structure:
    # {
    #   "event_id": "abc123",
    #   "status": "cancelled" | "updated",
    #   "provider": "GOOGLE" | "OUTLOOK"
    # }

    event_id = payload.get("event_id")
    provider = payload.get("provider")
    status = payload.get("status")

    if not event_id or not provider:
        raise HTTPException(status_code=400, detail="Invalid payload")

    await db.connect()
    appt = await db.appointment.find_first(where={
        "externalEventId": event_id,
        "calendarProvider": provider.upper()
    })

    if not appt:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Appointment not found")

    if status == "cancelled":
        await db.appointment.update(where={"id": appt.id}, data={"status": "CANCELLED"})
    elif status == "updated":
        # Future: pull new details from provider
        pass

    await db.disconnect()
    return {"message": "Webhook processed"}

# Calendar View Endpoint
# This will allow users to view appointments in a calendar format
# It will filter by technician and date if provided
@router.get("/calendar/full")
async def full_calendar_view(
    technicianId: Optional[str] = None,
    day: Optional[str] = None,
    user = Depends(get_current_user)
):
    await db.connect()

    filters = {}
    if technicianId:
        filters["technicianId"] = technicianId
    if day:
        date = datetime.strptime(day, "%Y-%m-%d")
        filters["startTime"] = {
            "gte": date,
            "lt": date + timedelta(days=1)
        }

    appointments = await db.appointment.find_many(where=filters, include={"technician": True})
    bays = await db.workbay.find_many(include={"assignedJob": True})

    await db.disconnect()
    return {
        "appointments": appointments,
        "bays": bays
    }

# Public Calendar ICS Endpoint
# This will generate an ICS file for public viewing of a technician's calendar
# It will mark jobs as acknowledged when accessed via the public token
@router.get("/calendar/public/{token}.ics")
async def public_tech_ics(token: str):
    await db.connect()
    tech = await db.user.find_first(where={"publicCalendarToken": token})
    if not tech:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Invalid token")

    jobs = await db.job.find_many(
        where={"technicianId": tech.id, "acknowledged": False}
    )

    for job in jobs:
        await db.job.update(
            where={"id": job.id},
            data={"acknowledged": True, "acknowledgedAt": datetime.utcnow()}
        )

    await db.disconnect()

    # Return calendar file as before...
# This will generate an ICS file for public viewing of a technician's calendar
@router.post("/calendar/sync")
async def sync_appointments_to_google(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    # This assumes access_token is stored or OAuth2 flow completed
    token = await get_user_google_token(user.id)
    events = await fetch_appointments_to_sync()

    for event in events:
        await push_to_google_calendar(token, event)

    return {"message": f"{len(events)} appointments synced"}

# Google OAuth Callback Endpoint
# This will handle the OAuth callback from Google after user authorizes access
@router.get("/calendar/oauth/callback")
async def google_oauth_callback(code: str, user=Depends(get_current_user)):
    # Exchange code for token
    token_data = await exchange_google_code_for_token(code)
    refresh_token = token_data["refresh_token"]
    email = token_data["email"]

    await db.connect()
    await db.user.update(
        where={"id": user.id},
        data={
            "googleRefreshToken": refresh_token,
            "googleEmail": email
        }
    )
    await db.disconnect()
    return {"message": "Google Calendar linked"}
