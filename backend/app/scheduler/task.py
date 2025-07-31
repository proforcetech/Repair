# File: backend/app/scheduler/task.py
# This file contains scheduled tasks for the application, such as sending weekly technician schedules.
from app.db.prisma_client import db
from fastapi import APIRouter
from app.core.notifications import notify_user
from datetime import datetime, timedelta

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

async def send_weekly_tech_schedules():
    await db.connect()
    techs = await db.user.find_many(where={"role": "TECHNICIAN"})
    end = datetime.utcnow() + timedelta(days=7)

    for tech in techs:
        jobs = await db.job.find_many(
            where={
                "technicianId": tech.id,
                "startTime": {"gte": datetime.utcnow(), "lte": end}
            },
            order={"startTime": "asc"}
        )
        if jobs:
            body = "\n".join(
                f"{j.startTime} → {j.endTime} | {j.type} @ Bay(s): {j.bayIds or j.bayId}"
                for j in jobs
            )
            await notify_user(
                email=tech.email,
                subject="🗓️ Your Weekly Job Schedule",
                body=f"Hi {tech.email},\n\nHere’s your schedule for the upcoming week:\n\n{body}"
            )
    await db.disconnect()
