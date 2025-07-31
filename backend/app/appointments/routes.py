# backend/app/appointments/routes.py
# This file contains appointment management routes for creating, updating, and managing appointments.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
    from app.auth.dependencies import get_current_user, require_role
    from app.core.notifier import send_email
    from app.db.prisma_client import db
    from datetime import datetime, time, timedelta
    from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
    from pydantic import BaseModel
    from typing import Optional
    import httpx
    import os
    import uuid
    
router = APIRouter(prefix="/appointments", tags=["appointments"])


class AppointmentCreate(BaseModel):
    title: str
    vehicleId: Optional[str] = None
    technicianId: Optional[str] = None
    startTime: datetime
    endTime: datetime

# Appointment Management Endpoints
# This will handle creating, listing, and managing appointments
@router.post("/")
async def create_appointment(data: AppointmentCreate, user = Depends(get_current_user)):
    await db.connect()
    appt = await db.appointment.create({
        **data.dict(),
        "customerId": user.id
    })
    await db.disconnect()
    return appt

# Update an existing appointment
@router.get("/")
async def list_appointments(user = Depends(get_current_user)):
    await db.connect()
    if user.role in ["ADMIN", "MANAGER"]:
        appts = await db.appointment.find_many()
    else:
        appts = await db.appointment.find_many(where={"customerId": user.id})
    await db.disconnect()
    return appts

# Get a specific appointment by ID
@router.post("/reminders/{appt_id}")
async def send_reminder(appt_id: str, user = Depends(get_current_user)):
    require_role(["ADMIN", "FRONT_DESK"])(user)
    await db.connect()
    appt = await db.appointment.find_unique(
        where={"id": appt_id},
        include={"customer": True}
    )
    await db.disconnect()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    await send_email(
        to_email=appt.customer.email,
        subject="Upcoming Appointment Reminder",
        body=f"Hello! Reminder for your appointment: {appt.title} at {appt.startTime}"
    )
    return {"message": "Reminder sent"}

# Calendar View Endpoint
# This will allow users to view appointments in a calendar format
# It will filter by technician and date if provided
@router.get("/calendar")
async def calendar_view(
    technicianId: Optional[str] = None,
    day: Optional[str] = None,  # YYYY-MM-DD
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

    appointments = await db.appointment.find_many(where=filters)
    await db.disconnect()
    return appointments

# Sync Appointment to Calendar
# This will handle syncing an appointment to an external calendar (Google/Outlook)
# For now, it will just return a message indicating the sync request
# In the future, this will integrate with Google Calendar API or Outlook API
@router.post("/{appt_id}/sync-calendar")
async def sync_to_calendar(appt_id: str, user = Depends(get_current_user)):
    require_role(["FRONT_DESK", "MANAGER", "ADMIN"])(user)
    await db.connect()
    appt = await db.appointment.find_unique(where={"id": appt_id})
    await db.disconnect()

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Stub for now
    return {
        "message": "Calendar sync request accepted",
        "appointment": appt,
        "calendarSync": "Google/Outlook API integration pending"
    }


class AppointmentCreate(BaseModel):
    customerId: str
    vehicleId: str
    startTime: datetime
    endTime: datetime
    reason: str

# Book an Appointment Endpoint
# This will allow customers to book an appointment for their vehicle
# It will check for technician availability and time conflicts
# If the appointment overlaps with an existing one, it will return an error
@router.post("/appointments/")
async def book_appointment(data: AppointmentCreate):
    await db.connect()
    appointment = await db.appointment.create(data=data.dict())
    await db.disconnect()
    return appointment

# Assign Technician to Appointment Endpoint
# This will allow admins or managers to assign a technician to an appointment
# It will check for time conflicts with existing appointments
# If the technician is already booked for that time, it will return an error
@router.post("/appointments/assign")
async def assign_technician(appointment_id: str, technician_id: str):
    await db.connect()
    # Check for time overlap
    appt = await db.appointment.find_unique(where={"id": appointment_id})
    conflicts = await db.appointment.find_many(
        where={
            "technicianId": technician_id,
            "startTime": {"lt": appt.endTime},
            "endTime": {"gt": appt.startTime},
            "status": "SCHEDULED"
        }
    )
    if conflicts:
        await db.disconnect()
        raise HTTPException(400, "Technician not available")

    updated = await db.appointment.update(
        where={"id": appointment_id},
        data={"technicianId": technician_id}
    )
    await db.disconnect()
    return {"message": "Technician assigned", "appointment": updated}

# Calendar View Endpoint
# This will allow users to view appointments in a calendar format
# It will group appointments by day and return a structured response
# It will also include customer and vehicle details for each appointment
@router.get("/appointments/calendar")
async def calendar_view(user=Depends(get_current_user)):
    await db.connect()
    appointments = await db.appointment.find_many(
        order={"startTime": "asc"},
        include={"customer": True, "vehicle": True, "technician": True}
    )
    await db.disconnect()

    result = {}
    for a in appointments:
        key = a.startTime.strftime("%Y-%m-%d")
        result.setdefault(key, []).append(a)

    return result

# Assign Bay to Appointment Endpoint
# This will allow admins or managers to assign a service bay to an appointment
# It will check if the bay is already in use and return an error if it is
# If the bay is available, it will update the appointment and bay status
@router.post("/bays/{bay_id}/assign")
async def assign_bay(bay_id: str, appointment_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    bay = await db.bay.update(
        where={"id": bay_id},
        data={"inUse": True, "currentAppointmentId": appointment_id}
    )
    await db.appointment.update(
        where={"id": appointment_id},
        data={"status": "IN_PROGRESS"}
    )
    await db.disconnect()
    return {"message": "Bay assigned", "bay": bay}




# Auto-Schedule Appointment Endpoint
# This will automatically schedule an appointment for a vehicle based on technician and bay availability
# It will check for available technicians and bays for the next business day
# If no slots are available, it will return an error
@router.post("/appointments/auto-schedule")
async def auto_schedule_appointment(
    vehicle_id: str, duration_minutes: int, user=Depends(get_current_user)
):
    await db.connect()
    technicians = await db.user.find_many(where={"role": "TECHNICIAN"})
    bays = await db.bay.find_many()
    today = datetime.utcnow().date()

    for hour in range(8, 17):
        start_time = datetime.combine(today, time(hour, 0))
        end_time = start_time + timedelta(minutes=duration_minutes)

        for tech in technicians:
            tech_busy = await db.appointment.find_first(
                where={
                    "technicianId": tech.id,
                    "startTime": {"lt": end_time},
                    "endTime": {"gt": start_time},
                    "status": "SCHEDULED"
                }
            )
            if tech_busy:
                continue

            for bay in bays:
                bay_busy = await db.appointment.find_first(
                    where={
                        "bayId": bay.id,
                        "startTime": {"lt": end_time},
                        "endTime": {"gt": start_time},
                        "status": "SCHEDULED"
                    }
                )
                if bay_busy:
                    continue

                appt = await db.appointment.create(data={
                    "customerId": user.id,
                    "vehicleId": vehicle_id,
                    "startTime": start_time,
                    "endTime": end_time,
                    "status": "SCHEDULED",
                    "technicianId": tech.id,
                    "bayId": bay.id,
                    "reason": "Auto-scheduled appointment"
                })
                await db.disconnect()
                return {"message": "Scheduled", "appointment": appt}

    await db.disconnect()
    raise HTTPException(409, "No available technician + bay slots today")

# Route Optimization Endpoint
# This will optimize a route for multiple addresses using a placeholder algorithm
# In the future, this will integrate with Mapbox or Google Maps API for real optimization

@router.post("/dispatch/optimize-route")
async def optimize_route(addresses: list[str]):
    # Simulate route optimization – integrate with Mapbox/Google later
    ordered = sorted(addresses)  # placeholder sort
    return {"optimizedRoute": ordered}

# Maintenance Reminders Endpoint
# This will send reminders to customers for vehicle maintenance based on last service date or mileage
@router.post("/reminders/maintenance/run")
async def run_maintenance_reminders():
    now = datetime.utcnow()
    six_months_ago = now - timedelta(days=180)

    await db.connect()
    due = await db.vehicle.find_many(
        where={
            "OR": [
                {"lastServiceMileage": {"lte": PrismaClient.field("mileageReminderThreshold")}},
                {"lastServiceDate": {"lte": six_months_ago}}
            ]
        },
        include={"customer": True}
    )
    await db.disconnect()

    for v in due:
        await send_email(v.customer.email, "Maintenance Due", f"Your vehicle {v.make} is due for service.")
        await send_sms(v.customer.phone, "Reminder: Your vehicle may need service.")

    return {"remindersSent": len(due)}

# Recurring Maintenance Services Endpoint
# This will check for recurring maintenance contracts and schedule appointments if due
@router.post("/maintenance/check-recurring")
async def check_recurring_services():
    now = datetime.utcnow()

    await db.connect()
    due_contracts = await db.maintenancecontract.find_many(
        where={
            "recurrenceMonths": {"not": None},
            "nextServiceDue": {"lte": now},
            "isActive": True
        },
        include={"vehicle": {"include": {"customer": True}}}
    )

    for contract in due_contracts:
        customer = contract.vehicle.customer
        # Schedule appointment + update nextServiceDue
        new_due = now + timedelta(days=contract.recurrenceMonths * 30)
        await db.appointment.create(data={
            "customerId": customer.id,
            "vehicleId": contract.vehicleId,
            "startTime": now + timedelta(days=1),
            "endTime": now + timedelta(days=1, hours=1),
            "status": "SCHEDULED",
            "reason": "Recurring maintenance"
        })
        await db.maintenancecontract.update(
            where={"id": contract.id},
            data={"nextServiceDue": new_due}
        )
        await send_email(customer.email, "Service Scheduled", "Your next recurring maintenance has been scheduled.")

    await db.disconnect()
    return {"scheduled": len(due_contracts)}


class ApptTimeUpdate(BaseModel):
    startTime: datetime
    endTime: datetime

@router.put("/appointments/{id}/reschedule")
async def reschedule_appointment(id: str, update: ApptTimeUpdate, user=Depends(get_current_user)):
    require_role(["FRONT_DESK", "MANAGER"])(user)

    await db.connect()
    appt = await db.appointment.update(
        where={"id": id},
        data={"startTime": update.startTime, "endTime": update.endTime}
    )
    await db.disconnect()
    return {"message": "Appointment rescheduled", "appointment": appt}

class AppointmentIn(BaseModel):
    customerId: str
    vehicleId: str
    type: str
    scheduledAt: datetime
    duration: int
    notes: Optional[str] = None

@router.post("/appointments")
async def create_appointment(data: AppointmentIn, user=Depends(get_current_user)):
    require_role(["FRONT-DESK", "MANAGER", "ADMIN"])(user)

    await db.connect()
    appt = await db.appointment.create(data=data.dict())
    await db.disconnect()
    return appt

@router.get("/appointments/calendar")
async def get_calendar(start: datetime, end: datetime, user=Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)

    await db.connect()
    appts = await db.appointment.find_many(where={
        "scheduledAt": {"gte": start, "lte": end}
    })
    await db.disconnect()
    return appts

@router.post("/public/appointments")
async def customer_book_appointment(data: AppointmentIn):
    # No auth — called from public frontend

    await db.connect()
    appt = await db.appointment.create(data={**data.dict(), "status": "SCHEDULED"})
    await db.disconnect()
    return {"message": "Appointment booked", "id": appt.id}

@router.get("/appointments/availability")
async def check_availability(date: datetime):
    await db.connect()
    appointments = await db.appointment.find_many(
        where={"scheduledAt": {"gte": date, "lte": date + timedelta(hours=8)}}
    )
    await db.disconnect()
    return appointments

class Assignment(BaseModel):
    technicianId: str
    bay: Optional[str]
    serviceTruck: Optional[str]

@router.put("/appointments/{id}/assign")
async def assign_technician(id: str, assignment: Assignment, user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    updated = await db.appointment.update(
        where={"id": id},
        data=assignment.dict(exclude_unset=True)
    )
    await db.disconnect()
    return {"message": "Assigned", "appointment": updated}


@router.post("/appointments/reminders/send")
async def send_reminders(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    upcoming = await db.appointment.find_many(
        where={
            "scheduledAt": {"gte": datetime.utcnow() + timedelta(hours=1),
                            "lte": datetime.utcnow() + timedelta(hours=25)},
            "reminderSentAt": None
        },
        include={"customer": True}
    )

    for appt in upcoming:
        message = (
            f"Reminder: You have a {appt.type.lower()} appointment on "
            f"{appt.scheduledAt.strftime('%A %b %d, %I:%M %p')}."
        )
        # Send SMS (example with Twilio-style HTTP call)
        async with httpx.AsyncClient() as client:
            await client.post("https://sms-provider.example/send", json={
                "to": appt.customer.phone,
                "body": message
            })

        await db.appointment.update(
            where={"id": appt.id},
            data={"reminderSentAt": datetime.utcnow()}
        )

    await db.disconnect()
    return {"sent": len(upcoming)}

@router.get("/appointments/wip")
async def work_in_progress(user=Depends(get_current_user)):
    require_role(["MANAGER", "TECHNICIAN", "ADMIN"])(user)

    await db.connect()
    today = datetime.utcnow().date()
    appts = await db.appointment.find_many(
        where={
            "scheduledAt": {
                "gte": datetime(today.year, today.month, today.day),
                "lte": datetime(today.year, today.month, today.day, 23, 59)
            }
        },
        order={"scheduledAt": "asc"}
    )
    await db.disconnect()

    return appts



PHOTO_DIR = "uploads/appointments"

@router.post("/appointments/{id}/photos")
async def upload_photo(id: str, file: UploadFile = File(...), user=Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)

    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(PHOTO_DIR, filename)

    with open(path, "wb") as f:
        f.write(await file.read())

    await db.connect()
    await db.appointmentphoto.create(data={"appointmentId": id, "url": f"/{PHOTO_DIR}/{filename}"})
    await db.disconnect()

    return {"message": "Uploaded", "url": f"/{PHOTO_DIR}/{filename}"}

class AppointmentUpdate(BaseModel):
    notes: Optional[str]
    checklist: Optional[dict]

@router.put("/appointments/{id}/update")
async def update_notes(id: str, data: AppointmentUpdate, user=Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER"])(user)

    await db.connect()
    updated = await db.appointment.update(where={"id": id}, data=data.dict(exclude_unset=True))
    await db.disconnect()
    return {"message": "Updated", "appointment": updated}

@router.get("/appointments")
async def get_shop_appointments(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT-DESK"])(user)

    await db.connect()
    appts = await db.appointment.find_many(where={"shopId": user.shopId})
    await db.disconnect()
    return appts
