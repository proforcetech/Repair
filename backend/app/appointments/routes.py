"""Appointment management routes.

This module exposes appointment-related endpoints including booking,
auto-scheduling, reminder dispatch, and asset assignment utilities.
The previous implementation contained duplicated route registrations and
undefined helper usages which caused FastAPI to raise assertion errors when
mounting the router.  The refactored module keeps a single handler per
endpoint path, centralises the request models, and relies on explicit imports
for notification helpers and Prisma queries.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
import os
import uuid
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, require_role
from app.core.notifier import send_email, send_sms
from app.db.prisma_client import db


router = APIRouter(prefix="/appointments", tags=["appointments"])


class AppointmentCreate(BaseModel):
    """Payload for creating an appointment for the authenticated customer."""

    title: str
    startTime: datetime
    endTime: datetime
    vehicleId: Optional[str] = None
    technicianId: Optional[str] = None
    reason: Optional[str] = None


class AppointmentBooking(BaseModel):
    """Payload used by public booking flows."""

    title: str
    customerId: str
    vehicleId: str
    startTime: datetime
    endTime: datetime
    reason: str


class AutoScheduleRequest(BaseModel):
    vehicleId: str
    durationMinutes: int


class ApptTimeUpdate(BaseModel):
    startTime: datetime
    endTime: datetime


class Assignment(BaseModel):
    technicianId: Optional[str] = None
    bayId: Optional[str] = None
    serviceTruck: Optional[str] = None


class AppointmentUpdate(BaseModel):
    notes: Optional[str] = None
    checklist: Optional[Dict] = None


@router.post("/")
async def create_appointment(
    data: AppointmentCreate, user=Depends(get_current_user)
):
    """Create an appointment for the authenticated customer."""

    payload = data.model_dump(exclude_unset=True)
    payload["customerId"] = user.id
    payload.setdefault("status", "SCHEDULED")

    await db.connect()
    appointment = await db.appointment.create(data=payload)
    await db.disconnect()
    return appointment


@router.get("/")
async def list_appointments(user=Depends(get_current_user)):
    """List appointments for the current user or all if privileged."""

    await db.connect()
    if user.role in {"ADMIN", "MANAGER"}:
        appointments = await db.appointment.find_many()
    else:
        appointments = await db.appointment.find_many(where={"customerId": user.id})
    await db.disconnect()
    return appointments


@router.post("/{appointment_id}/reminders")
async def send_reminder(appointment_id: str, user=Depends(get_current_user)):
    """Send an email reminder for an appointment."""

    require_role(["ADMIN", "FRONT_DESK"])(user)

    await db.connect()
    appointment = await db.appointment.find_unique(
        where={"id": appointment_id},
        include={"customer": True},
    )
    await db.disconnect()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    await send_email(
        to_email=appointment.customer.email,
        subject="Upcoming Appointment Reminder",
        body=(
            "Hello! Reminder for your appointment: "
            f"{appointment.title} at {appointment.startTime}"
        ),
    )
    return {"message": "Reminder sent"}


@router.get("/calendar")
async def calendar_view(
    technicianId: Optional[str] = None,
    day: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Return a list of appointments filtered by technician or day."""

    await db.connect()
    filters: Dict = {}
    if technicianId:
        filters["technicianId"] = technicianId
    if day:
        date = datetime.strptime(day, "%Y-%m-%d")
        filters["startTime"] = {"gte": date, "lt": date + timedelta(days=1)}

    appointments = await db.appointment.find_many(where=filters)
    await db.disconnect()
    return appointments


@router.post("/{appointment_id}/sync")
async def sync_to_calendar(appointment_id: str, user=Depends(get_current_user)):
    """Stub endpoint representing external calendar synchronisation."""

    require_role(["FRONT_DESK", "MANAGER", "ADMIN"])(user)

    await db.connect()
    appointment = await db.appointment.find_unique(where={"id": appointment_id})
    await db.disconnect()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {
        "message": "Calendar sync request accepted",
        "appointment": appointment,
        "calendarSync": "Google/Outlook API integration pending",
    }


@router.post("/book")
async def book_appointment(data: AppointmentBooking):
    """Book an appointment without authentication (public entry point)."""

    payload = {**data.model_dump(), "status": "SCHEDULED"}

    await db.connect()
    appointment = await db.appointment.create(data=payload)
    await db.disconnect()
    return appointment


@router.post("/auto-schedule")
async def auto_schedule_appointment(
    request: AutoScheduleRequest, user=Depends(get_current_user)
):
    """Automatically schedule the next available slot for a vehicle."""

    await db.connect()
    technicians = await db.user.find_many(where={"role": "TECHNICIAN"})
    bays = await db.bay.find_many()
    today = datetime.utcnow().date()

    for hour in range(8, 17):
        start_time = datetime.combine(today, time(hour=hour, minute=0))
        end_time = start_time + timedelta(minutes=request.durationMinutes)

        for technician in technicians:
            conflict = await db.appointment.find_first(
                where={
                    "technicianId": technician.id,
                    "startTime": {"lt": end_time},
                    "endTime": {"gt": start_time},
                    "status": "SCHEDULED",
                }
            )
            if conflict:
                continue

            for bay in bays:
                bay_conflict = await db.appointment.find_first(
                    where={
                        "bayId": getattr(bay, "id", None),
                        "startTime": {"lt": end_time},
                        "endTime": {"gt": start_time},
                        "status": "SCHEDULED",
                    }
                )
                if bay_conflict:
                    continue

                appointment = await db.appointment.create(
                    data={
                        "customerId": user.id,
                        "vehicleId": request.vehicleId,
                        "startTime": start_time,
                        "endTime": end_time,
                        "status": "SCHEDULED",
                        "technicianId": technician.id,
                        "bayId": getattr(bay, "id", None),
                        "title": "Auto-scheduled appointment",
                        "reason": "Auto-scheduled appointment",
                    }
                )
                await db.disconnect()
                return {"message": "Scheduled", "appointment": appointment}

    await db.disconnect()
    raise HTTPException(status_code=409, detail="No available technician + bay slots today")


@router.post("/dispatch/optimize-route")
async def optimize_route(addresses: List[str]):
    """Placeholder implementation returning addresses sorted lexicographically."""

    return {"optimizedRoute": sorted(addresses)}


@router.post("/reminders/maintenance")
async def run_maintenance_reminders():
    """Send maintenance reminders for vehicles due by mileage or time."""

    now = datetime.utcnow()
    await db.connect()
    vehicles = await db.vehicle.find_many(
        where={"isArchived": False},
        include={"customer": True},
    )
    await db.disconnect()

    reminders_sent = 0
    for vehicle in vehicles:
        mileage_threshold = getattr(vehicle, "mileageReminderThreshold", None)
        last_service_mileage = getattr(vehicle, "lastServiceMileage", None)
        mileage_due = (
            mileage_threshold is not None
            and last_service_mileage is not None
            and last_service_mileage >= mileage_threshold
        )

        time_threshold_months = getattr(vehicle, "timeReminderMonths", None)
        last_service_date = getattr(vehicle, "lastServiceDate", None)
        time_due = False
        if time_threshold_months and last_service_date:
            delta = timedelta(days=30 * time_threshold_months)
            time_due = last_service_date <= now - delta

        if mileage_due or time_due:
            reminders_sent += 1
            await send_email(
                vehicle.customer.email,
                "Maintenance Due",
                f"Your vehicle {vehicle.make} is due for service.",
            )
            await send_sms(
                vehicle.customer.phone,
                "Reminder: Your vehicle may need service.",
            )

    return {"remindersSent": reminders_sent}


@router.post("/maintenance/recurring")
async def check_recurring_services():
    """Create follow-up appointments for recurring maintenance contracts."""

    now = datetime.utcnow()

    await db.connect()
    due_contracts = await db.maintenancecontract.find_many(
        where={
            "recurrenceMonths": {"not": None},
            "nextServiceDue": {"lte": now},
            "isActive": True,
        },
        include={"vehicle": {"include": {"customer": True}}},
    )

    for contract in due_contracts:
        customer = contract.vehicle.customer
        next_due = now + timedelta(days=contract.recurrenceMonths * 30)
        await db.appointment.create(
            data={
                "customerId": customer.id,
                "vehicleId": contract.vehicleId,
                "startTime": now + timedelta(days=1),
                "endTime": now + timedelta(days=1, hours=1),
                "status": "SCHEDULED",
                "reason": "Recurring maintenance",
                "title": "Recurring maintenance",
            }
        )
        await db.maintenancecontract.update(
            where={"id": contract.id},
            data={"nextServiceDue": next_due},
        )
        await send_email(
            customer.email,
            "Service Scheduled",
            "Your next recurring maintenance has been scheduled.",
        )

    await db.disconnect()
    return {"scheduled": len(due_contracts)}


@router.put("/{appointment_id}/reschedule")
async def reschedule_appointment(
    appointment_id: str, update: ApptTimeUpdate, user=Depends(get_current_user)
):
    """Reschedule an appointment (front desk or manager only)."""

    require_role(["FRONT_DESK", "MANAGER"])(user)

    await db.connect()
    appointment = await db.appointment.update(
        where={"id": appointment_id},
        data={"startTime": update.startTime, "endTime": update.endTime},
    )
    await db.disconnect()
    return {"message": "Appointment rescheduled", "appointment": appointment}


@router.put("/{appointment_id}/assignment")
async def update_assignment(
    appointment_id: str, assignment: Assignment, user=Depends(get_current_user)
):
    """Assign resources (technician/bay/truck) to an appointment."""

    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()

    technician_id = assignment.technicianId
    if technician_id:
        appt = await db.appointment.find_unique(where={"id": appointment_id})
        if not appt:
            await db.disconnect()
            raise HTTPException(status_code=404, detail="Appointment not found")
        conflicts = await db.appointment.find_many(
            where={
                "technicianId": technician_id,
                "startTime": {"lt": appt.endTime},
                "endTime": {"gt": appt.startTime},
                "status": "SCHEDULED",
                "NOT": {"id": appointment_id},
            }
        )
        if conflicts:
            await db.disconnect()
            raise HTTPException(status_code=400, detail="Technician not available")

    updated = await db.appointment.update(
        where={"id": appointment_id},
        data=assignment.model_dump(exclude_unset=True),
    )
    await db.disconnect()
    return {"message": "Assigned", "appointment": updated}


@router.post("/reminders/pending")
async def send_reminders(user=Depends(get_current_user)):
    """Send reminders for appointments occurring in the next 24 hours."""

    require_role(["ADMIN", "MANAGER"])(user)

    window_start = datetime.utcnow() + timedelta(hours=1)
    window_end = datetime.utcnow() + timedelta(hours=25)

    await db.connect()
    upcoming = await db.appointment.find_many(
        where={
            "scheduledAt": {"gte": window_start, "lte": window_end},
            "reminderSentAt": None,
        },
        include={"customer": True},
    )

    for appointment in upcoming:
        message = (
            "Reminder: You have a "
            f"{appointment.type.lower()} appointment on "
            f"{appointment.scheduledAt.strftime('%A %b %d, %I:%M %p')}"
        )
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://sms-provider.example/send",
                json={"to": appointment.customer.phone, "body": message},
            )

        await db.appointment.update(
            where={"id": appointment.id},
            data={"reminderSentAt": datetime.utcnow()},
        )

    await db.disconnect()
    return {"sent": len(upcoming)}


@router.get("/work-in-progress")
async def work_in_progress(user=Depends(get_current_user)):
    """Return today's appointments in chronological order."""

    require_role(["MANAGER", "TECHNICIAN", "ADMIN"])(user)

    today = datetime.utcnow().date()
    start = datetime(today.year, today.month, today.day)
    end = datetime(today.year, today.month, today.day, 23, 59)

    await db.connect()
    appointments = await db.appointment.find_many(
        where={"scheduledAt": {"gte": start, "lte": end}},
        order={"scheduledAt": "asc"},
    )
    await db.disconnect()
    return appointments


PHOTO_DIR = "uploads/appointments"


@router.post("/{appointment_id}/photos")
async def upload_photo(
    appointment_id: str, file: UploadFile = File(...), user=Depends(get_current_user)
):
    """Store an uploaded appointment photo on disk."""

    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)

    os.makedirs(PHOTO_DIR, exist_ok=True)
    extension = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{extension}"
    path = os.path.join(PHOTO_DIR, filename)

    with open(path, "wb") as buffer:
        buffer.write(await file.read())

    await db.connect()
    await db.appointmentphoto.create(
        data={"appointmentId": appointment_id, "url": f"/{PHOTO_DIR}/{filename}"}
    )
    await db.disconnect()

    return {"message": "Uploaded", "url": f"/{PHOTO_DIR}/{filename}"}


@router.put("/{appointment_id}")
async def update_notes(
    appointment_id: str, data: AppointmentUpdate, user=Depends(get_current_user)
):
    """Update appointment notes or checklist details."""

    require_role(["TECHNICIAN", "MANAGER"])(user)

    await db.connect()
    updated = await db.appointment.update(
        where={"id": appointment_id},
        data=data.model_dump(exclude_unset=True),
    )
    await db.disconnect()
    return {"message": "Updated", "appointment": updated}


@router.get("/availability")
async def check_availability(date: datetime):
    """Return appointments scheduled within eight hours of the given date."""

    await db.connect()
    appointments = await db.appointment.find_many(
        where={"scheduledAt": {"gte": date, "lte": date + timedelta(hours=8)}}
    )
    await db.disconnect()
    return appointments


@router.get("/shop")
async def get_shop_appointments(user=Depends(get_current_user)):
    """List appointments for the authenticated user's shop."""

    require_role(["ADMIN", "MANAGER", "FRONT-DESK"])(user)

    await db.connect()
    appointments = await db.appointment.find_many(where={"shopId": user.shopId})
    await db.disconnect()
    return appointments
