# File: backend/app/technicians/routes.py
# This file contains routes for managing technicians, including job clocking, time-off requests, and
# technician availability. It also includes functionality for generating reports and managing technician schedules.
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user, require_role
from pydantic import BaseModel, EmailStr
from datetime import datetime
import csv
from fastapi.responses import StreamingResponse
from io import StringIO
from datetime import timedelta
from typing import Optional
from app.db.prisma_client import db

router = APIRouter(prefix="/technicians", tags=["technicians"])


@router.get("/reports/time-log.csv")
async def export_time_log_csv(
    technician_id: str,
    start_date: str,
    end_date: str,
    user = Depends(get_current_user)
):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()

    logs = await db.jobtimelog.find_many(
        where={
            "techId": technician_id,
            "startedAt": {"gte": start_date},
            "endedAt": {"lte": end_date}
        },
        include={"job": True}
    )

    await db.disconnect()

    # Prepare CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Job", "Started", "Ended", "Hours"])

    for log in logs:
        duration = (
            (log.endedAt - log.startedAt).total_seconds() / 3600
            if log.endedAt else 0
        )
        writer.writerow([
            log.startedAt.date(),
            log.job.title if log.job else "-",
            log.startedAt.isoformat(),
            log.endedAt.isoformat() if log.endedAt else "-",
            round(duration, 2)
        ])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=time_log.csv"
    })



@router.post("/jobs/{job_id}/clock-in")
async def clock_in(job_id: str, user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()
    log = await db.jobtimelog.create({
        "jobId": job_id,
        "techId": user.id,
        "startedAt": datetime.utcnow()
    })
    await db.disconnect()
    return {"message": "Clocked in", "log": log}

@router.post("/jobs/{job_id}/clock-out")
async def clock_out(job_id: str, user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()
    logs = await db.jobtimelog.find_many(
        where={"jobId": job_id, "techId": user.id, "endedAt": None},
        order={"startedAt": "desc"},
        take=1
    )
    if not logs:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="No open log found")
    
    log = logs[0]
    updated = await db.jobtimelog.update(
        where={"id": log.id},
        data={"endedAt": datetime.utcnow()}
    )
    await db.disconnect()
    return {"message": "Clocked out", "log": updated}
    await db.appointment.update(
        where={"id": appointmentId},
        data={"status": "COMPLETED"}
    )



@router.get("/dashboard")
async def technician_dashboard(user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    # Future: job queue, hours logged, assigned bays, etc.
    return {
        "message": "Technician dashboard base",
        "tech_id": user.id,
        "name": user.email,
        "next_jobs": [],  # placeholder
    }

@router.get("/jobs")
async def get_assigned_jobs(user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()
    jobs = await db.job.find_many(where={"technicianId": user.id})
    await db.disconnect()
    return jobs

class JobStatusUpdate(BaseModel):
    status: str  # Expected: QUEUED, IN_PROGRESS, ON_HOLD, COMPLETED

@router.put("/jobs/{job_id}/status")
async def update_job_status(job_id: str, data: JobStatusUpdate, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)

    await db.connect()
    job = await db.job.find_unique(where={"id": job_id})
    if not job or (user.role == "TECHNICIAN" and job.technicianId != user.id):
        raise HTTPException(status_code=403, detail="Unauthorized")

    updated = await db.job.update(
        where={"id": job_id},
        data={"status": data.status.upper()}
    )
    await db.disconnect()

    return {"message": "Job status updated", "job": updated}


class TimeLogUpdate(BaseModel):
    startedAt: Optional[datetime] = None
    endedAt: Optional[datetime] = None

@router.put("/time-log/{log_id}")
async def adjust_time_log(log_id: str, data: TimeLogUpdate, user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()

    log = await db.jobtimelog.find_unique(where={"id": log_id})
    if not log:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Log not found")

    updated = await db.jobtimelog.update(
        where={"id": log_id},
        data={k: v for k, v in data.dict().items() if v is not None}
    )
    await db.disconnect()
    return {"message": "Time log updated", "log": updated}

import secrets

@router.post("/tech/{tech_id}/enable-calendar")
async def enable_tech_calendar(tech_id: str, user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    token = secrets.token_hex(16)
    await db.connect()
    await db.user.update(
        where={"id": tech_id},
        data={"publicCalendarToken": token}
    )
    await db.disconnect()
    return {"calendar_url": f"https://yourdomain.com/api/calendar/public/{token}.ics"}

from app.core.notifier import notify_user

@router.post("/notify-tech-job")
async def notify_tech_of_job(job_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "FRONT-DESK"])(user)
    await db.connect()
    job = await db.job.find_unique(where={"id": job_id})
    tech = await db.user.find_unique(where={"id": job.technicianId})
    await db.disconnect()

    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    await notify_user(
        email=tech.email,
        subject="📅 New Job Assigned",
        body=f"You have a new job:\n\nType: {job.type}\nVehicle: {job.vehicleId}\nStart: {job.startTime}\nBay(s): {job.bayIds or job.bayId}"
    )

    return {"message": "Technician notified"}

@router.get("/technicians/{tech_id}/availability")
async def tech_availability(tech_id: str, day: date):
    start_of_day = datetime.combine(day, time(8, 0))
    end_of_day = datetime.combine(day, time(18, 0))

    await db.connect()
    appointments = await db.appointment.find_many(
        where={
            "technicianId": tech_id,
            "startTime": {"gte": start_of_day, "lt": end_of_day}
        }
    )
    await db.disconnect()

    busy_blocks = [(a.startTime, a.endTime) for a in appointments]
    return {"busy": busy_blocks}


@router.get("/technicians/{tech_id}/dispatch")
async def mobile_dispatch(tech_id: str):
    await db.connect()
    tech = await db.user.find_unique(where={"id": tech_id}, include={"zone": True})
    if not tech.zone:
        raise HTTPException(400, "No zone assigned")
    
    zone_codes = tech.zone.postalCodes
    appts = await db.appointment.find_many(
        where={"postalCode": {"in": zone_codes}, "status": "SCHEDULED"}
    )
    await db.disconnect()
    return appts

@router.get("/technicians/{tech_id}/scorecard")
async def technician_scorecard(tech_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    start = datetime.utcnow() - timedelta(days=30)

    await db.connect()
    jobs = await db.jobitem.find_many(where={
        "technicianId": tech_id,
        "createdAt": {"gte": start}
    })
    returns = await db.warrantyclaim.find_many(where={
        "jobItem": {"technicianId": tech_id},
        "createdAt": {"gte": start}
    })
    await db.disconnect()

    total_hours = sum(j.hoursBilled for j in jobs)
    total_cost = sum(j.laborCost for j in jobs)
    return_rate = len(returns) / max(len(jobs), 1)

    return {
        "jobsCompleted": len(jobs),
        "hoursBilled": round(total_hours, 2),
        "laborCost": round(total_cost, 2),
        "returnRate": f"{return_rate*100:.1f}%"
    }


class TimeOffCreate(BaseModel):
    startDate: datetime
    endDate: datetime
    reason: Optional[str]

@router.post("/timeoff")
async def request_time_off(data: TimeOffCreate, user=Depends(get_current_user)):
    await db.connect()
    req = await db.timeoffrequest.create(data={**data.dict(), "userId": user.id})
    await db.disconnect()
    return {"message": "Time-off request submitted", "request": req}

class TimeOffApproval(BaseModel):
    approved: bool

@router.put("/timeoff/{id}/decision")
async def approve_time_off(id: str, decision: TimeOffApproval, user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    result = await db.timeoffrequest.update(where={"id": id}, data={"approved": decision.approved})
    await db.disconnect()
    return {"message": "Request updated", "request": result}

@router.get("/availability")
async def list_technician_availability(user=Depends(get_current_user)):
    require_role(["MANAGER", "DISPATCH"])(user)
    await db.connect()
    offs = await db.timeoffrequest.find_many(where={"approved": True})
    await db.disconnect()
    return offs

@router.get("/technicians/workload")
async def technician_workload(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    today = datetime.utcnow().date()
    await db.connect()
    appts = await db.appointment.find_many(
        where={
            "scheduledAt": {
                "gte": datetime(today.year, today.month, today.day),
                "lte": datetime(today.year, today.month, today.day, 23, 59)
            }
        }
    )
    await db.disconnect()

    totals = {}
    for appt in appts:
        if not appt.technicianId:
            continue
        totals.setdefault(appt.technicianId, 0)
        totals[appt.technicianId] += appt.duration

    return [{"technicianId": k, "totalMinutes": v} for k, v in totals.items()]

from datetime import datetime

@router.post("/technicians/clock-in")
async def clock_in(appointmentId: str, user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)

    await db.connect()
    existing = await db.jobclock.find_first(
        where={"appointmentId": appointmentId, "technicianId": user.id, "clockOut": None}
    )
    if existing:
        raise HTTPException(400, detail="Already clocked in")

    record = await db.jobclock.create(data={
        "appointmentId": appointmentId,
        "technicianId": user.id,
        "clockIn": datetime.utcnow()
    })
    await db.disconnect()
    return {"message": "Clocked in", "record": record}

@router.post("/technicians/clock-out")
async def clock_out(appointmentId: str, user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)

    await db.connect()
    clock = await db.jobclock.find_first(
        where={"appointmentId": appointmentId, "technicianId": user.id, "clockOut": None}
    )
    if not clock:
        raise HTTPException(404, detail="No open clock-in found")

    record = await db.jobclock.update(
        where={"id": clock.id},
        data={"clockOut": datetime.utcnow()}
    )
    await db.disconnect()
    return {"message": "Clocked out", "record": record}

@router.get("/technicians/my-appointments")
async def my_appointments(user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    
    today = datetime.utcnow().date()
    await db.connect()
    appts = await db.appointment.find_many(
        where={
            "technicianId": user.id,
            "scheduledAt": {
                "gte": datetime(today.year, today.month, today.day),
                "lte": datetime(today.year, today.month, today.day, 23, 59)
            }
        },
        order={"scheduledAt": "asc"}
    )
    await db.disconnect()
    return appts

import httpx

@router.post("/dispatch/route-optimize")
async def optimize_route(truck_id: str, user=Depends(get_current_user)):
    require_role(["DISPATCH", "MANAGER", "ADMIN"])(user)

    await db.connect()
    truck = await db.servicetruck.find_unique(where={"id": truck_id})
    jobs = await db.appointment.find_many(
        where={"serviceTruck": truck_id, "status": "SCHEDULED"},
        order={"scheduledAt": "asc"}
    )
    await db.disconnect()

    coords = f"{truck.gpsLon},{truck.gpsLat};" + ";".join(
        f"{j.customerLon},{j.customerLat}" for j in jobs if j.customerLat and j.customerLon
    )

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.mapbox.com/optimized-trips/v1/mapbox/driving/{coords}",
            params={"access_token": "MAPBOX_API_TOKEN", "geometries": "geojson"}
        )
        return res.json()

@router.get("/technicians/{id}/shift-report")
async def shift_report(id: str, day: Optional[date] = None):
    d = day or date.today()
    start = datetime(d.year, d.month, d.day)
    end = start + timedelta(days=1)

    await db.connect()
    clocks = await db.jobclock.find_many(where={
        "technicianId": id,
        "clockIn": {"gte": start, "lte": end}
    })
    pings = await db.truckgps.find_many(where={
        "truckId": id, "timestamp": {"gte": start, "lte": end}
    })
    await db.disconnect()

    return {"jobs": clocks, "gpsTrack": pings}

@router.get("/technicians/{id}/daily-summary")
async def tech_summary(id: str, user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    today = datetime.utcnow().date()
    await db.connect()
    jobs = await db.appointment.find_many(where={
        "technicianId": id,
        "scheduledAt": {
            "gte": datetime(today.year, today.month, today.day),
            "lt": datetime(today.year, today.month, today.day + 1),
        }
    })
    await db.disconnect()

    return {
        "technicianId": id,
        "jobs": jobs,
        "count": len(jobs)
    }

@router.get("/technicians/{id}/route")
async def technician_route(id: str, user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN", "TECHNICIAN"])(user)

    today = datetime.utcnow().date()
    await db.connect()
    jobs = await db.appointment.find_many(where={
        "technicianId": id,
        "scheduledAt": {
            "gte": datetime(today.year, today.month, today.day),
            "lt": datetime(today.year, today.month, today.day + 1),
        },
        "latitude": {"not": None},
        "longitude": {"not": None},
    })
    await db.disconnect()

    return {
        "stops": [
            {"lat": j.latitude, "lng": j.longitude, "time": j.scheduledAt, "type": j.type}
            for j in jobs
        ]
    }

@router.post("/technicians/jobs/{appointment_id}/start")
async def start_job_timer(appointment_id: str, user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)

    await db.connect()
    active = await db.jobtimer.find_first(where={
        "technicianId": user.id,
        "endedAt": None
    })
    if active:
        raise HTTPException(400, detail="Finish current job before starting another.")

    timer = await db.jobtimer.create(data={
        "technicianId": user.id,
        "appointmentId": appointment_id,
        "startedAt": datetime.utcnow()
    })
    await db.disconnect()
    return {"message": "Timer started", "timer": timer}

@router.post("/technicians/jobs/{appointment_id}/stop")
async def stop_job_timer(appointment_id: str, user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)

    await db.connect()
    active = await db.jobtimer.find_first(where={
        "technicianId": user.id,
        "appointmentId": appointment_id,
        "endedAt": None
    })
    if not active:
        raise HTTPException(404, detail="No active timer found.")

    updated = await db.jobtimer.update(where={"id": active.id}, data={"endedAt": datetime.utcnow()})
    await db.disconnect()
    return {"message": "Timer stopped", "duration": (updated.endedAt - updated.startedAt).seconds}

@router.post("/technicians/clock-in")
async def clock_in(user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)

    await db.connect()
    active = await db.timeclock.find_first(where={"technicianId": user.id, "clockOut": None})
    if active:
        raise HTTPException(400, detail="Already clocked in")

    clock = await db.timeclock.create(data={
        "technicianId": user.id,
        "clockIn": datetime.utcnow()
    })
    await db.disconnect()
    return {"message": "Clocked in", "entry": clock}

@router.post("/technicians/clock-out")
async def clock_out(user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)

    await db.connect()
    clock = await db.timeclock.find_first(where={"technicianId": user.id, "clockOut": None})
    if not clock:
        raise HTTPException(404, detail="No active clock-in session")

    finished = await db.timeclock.update(where={"id": clock.id}, data={"clockOut": datetime.utcnow()})
    await db.disconnect()
    return {
        "message": "Clocked out",
        "duration_hours": round((finished.clockOut - finished.clockIn).total_seconds() / 3600, 2)
    }

@router.get("/technicians/{tech_id}/queue")
async def get_work_queue(tech_id: str, user=Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)

    await db.connect()
    appointments = await db.appointment.find_many(
        where={
            "technicianId": tech_id,
            "status": {"in": ["SCHEDULED", "IN_PROGRESS"]}
        },
        order={"scheduledAt": "asc"}
    )
    await db.disconnect()
    return appointments

@router.get("/dashboard/kpi/technicians")
async def tech_kpis(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    timers = await db.jobtimer.find_many(include={"technician": True})
    await db.disconnect()

    report = {}
    for t in timers:
        tech_id = t.technicianId
        duration = (t.endedAt - t.startedAt).total_seconds() / 3600
        report.setdefault(tech_id, {"name": t.technician.email, "hours": 0, "jobs": 0})
        report[tech_id]["hours"] += duration
        report[tech_id]["jobs"] += 1

    for r in report.values():
        r["efficiency"] = round(r["jobs"] / r["hours"], 2) if r["hours"] > 0 else 0

    return list(report.values())

class AvailabilityIn(BaseModel):
    date: datetime
    isAvailable: bool
    reason: Optional[str] = None

@router.post("/technicians/{id}/availability")
async def set_availability(id: str, data: AvailabilityIn, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    entry = await db.technicianavailability.upsert(
        where={"technicianId_date": {"technicianId": id, "date": data.date}},
        create={**data.dict(), "technicianId": id},
        update=data.dict()
    )
    await db.disconnect()
    return entry
