from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db

from . import services


router = APIRouter(prefix="/calendar", tags=["calendar"])


def _dict_or_attr(record: Any, key: str, default: Any | None = None) -> Any:
    """Return ``record[key]`` for dicts or ``getattr(record, key)`` for objects."""

    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


@router.get("/full")
async def full_calendar_view(
    technicianId: Optional[str] = None,
    day: Optional[str] = None,
    user: Any = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return appointments and bay information for the requested filters."""

    await db.connect()
    try:
        filters: Dict[str, Any] = {}

        if technicianId:
            filters["technicianId"] = technicianId
        if day:
            try:
                date = datetime.strptime(day, "%Y-%m-%d")
            except ValueError as exc:  # pragma: no cover - FastAPI handles validation
                raise HTTPException(status_code=400, detail="Invalid day format") from exc
            filters["startTime"] = {
                "gte": date,
                "lt": date + timedelta(days=1),
            }

        appointments = await db.appointment.find_many(
            where=filters, include={"technician": True}
        )
        bays = await db.workbay.find_many(include={"assignedJob": True})
    finally:
        await db.disconnect()

    return {"appointments": appointments, "bays": bays}


@router.get("/public/{token}.ics")
async def public_technician_calendar(token: str) -> Response:
    """Generate an ICS feed for a technician's public calendar."""

    await db.connect()
    try:
        technician = await db.user.find_first(where={"publicCalendarToken": token})
        if not technician:
            raise HTTPException(status_code=404, detail="Invalid token")

        jobs = await db.job.find_many(
            where={"technicianId": _dict_or_attr(technician, "id"), "acknowledged": False}
        )

        now = datetime.now(timezone.utc)
        for job in jobs:
            job_id = _dict_or_attr(job, "id")
            await db.job.update(
                where={"id": job_id},
                data={"acknowledged": True, "acknowledgedAt": now},
            )
    finally:
        await db.disconnect()

    calendar_body = services.generate_public_calendar_ics(technician, jobs)
    return Response(content=calendar_body, media_type="text/calendar")


@router.post("/webhook")
async def calendar_webhook(request: Request) -> Dict[str, str]:
    payload = await request.json()

    try:
        await services.process_webhook_payload(payload)
    except services.InvalidWebhookPayload as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except services.AppointmentNotFound as exc:
        raise HTTPException(status_code=404, detail="Appointment not found") from exc

    return {"message": "Webhook processed"}


@router.post("/sync")
async def sync_appointments_to_google(user: Any = Depends(get_current_user)) -> Dict[str, str]:
    require_role(["ADMIN", "MANAGER"])(user)

    token = await services.get_user_google_token(_dict_or_attr(user, "id"))
    events = await services.fetch_appointments_to_sync()

    for event in events:
        await services.push_to_google_calendar(token, event)

    return {"message": f"{len(events)} appointments synced"}


@router.get("/oauth/callback")
async def google_oauth_callback(
    code: str,
    user: Any = Depends(get_current_user),
) -> Dict[str, str]:
    token_data = await services.exchange_google_code_for_token(code)
    await services.store_google_credentials(_dict_or_attr(user, "id"), token_data)
    return {"message": "Google Calendar linked"}

