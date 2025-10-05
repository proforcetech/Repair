from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from app.db.prisma_client import db


class InvalidWebhookPayload(Exception):
    """Raised when a webhook payload is missing required fields."""


class AppointmentNotFound(Exception):
    """Raised when a webhook references an appointment that cannot be located."""


def _extract(record: Any, key: str, default: Any | None = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def _format_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def generate_public_calendar_ics(technician: Any, jobs: Iterable[Any]) -> str:
    """Create a minimal ICS calendar feed for the provided technician jobs."""

    tech_name = _extract(technician, "name", "Technician")
    calendar_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//RepairCRM//Calendar//EN",
        f"X-WR-CALNAME:{_escape(str(tech_name))}",
    ]

    generated = datetime.now(timezone.utc)

    for job in jobs:
        start = _extract(job, "startTime")
        end = _extract(job, "endTime")
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            continue

        summary = _extract(job, "title") or _extract(job, "summary") or "Service Appointment"
        description = _extract(job, "description") or ""
        uid = _extract(job, "id") or f"job-{_format_dt(start)}"
        location = _extract(job, "location", "")

        calendar_lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{_escape(str(uid))}@repaircrm",
                f"DTSTAMP:{_format_dt(generated)}",
                f"DTSTART:{_format_dt(start)}",
                f"DTEND:{_format_dt(end)}",
                f"SUMMARY:{_escape(str(summary))}",
            ]
        )

        if description:
            calendar_lines.append(f"DESCRIPTION:{_escape(str(description))}")
        if location:
            calendar_lines.append(f"LOCATION:{_escape(str(location))}")

        calendar_lines.append("END:VEVENT")

    calendar_lines.append("END:VCALENDAR")
    return "\r\n".join(calendar_lines) + "\r\n"


async def process_webhook_payload(payload: Dict[str, Any]) -> None:
    event_id = payload.get("event_id")
    provider = payload.get("provider")
    status = payload.get("status", "").lower()

    if not event_id or not provider:
        raise InvalidWebhookPayload("event_id and provider are required")

    await db.connect()
    try:
        appointment = await db.appointment.find_first(
            where={
                "externalEventId": event_id,
                "calendarProvider": provider.upper(),
            }
        )

        if not appointment:
            raise AppointmentNotFound(event_id)

        appointment_id = _extract(appointment, "id")
        if not appointment_id:
            raise AppointmentNotFound(event_id)

        update_data: Dict[str, Any] = {}

        if status == "cancelled":
            update_data["status"] = "CANCELLED"
        elif status == "updated":
            start = payload.get("start")
            end = payload.get("end")
            if isinstance(start, str):
                update_data["startTime"] = datetime.fromisoformat(start)
            if isinstance(end, str):
                update_data["endTime"] = datetime.fromisoformat(end)

        if update_data:
            await db.appointment.update(where={"id": appointment_id}, data=update_data)
    finally:
        await db.disconnect()


async def get_user_google_token(user_id: str) -> str:
    await db.connect()
    try:
        user = await db.user.find_unique(where={"id": user_id})
    finally:
        await db.disconnect()

    token = _extract(user, "googleRefreshToken") if user else None
    if not token:
        raise ValueError("Google Calendar is not linked for this user")
    return str(token)


async def fetch_appointments_to_sync() -> List[Any]:
    await db.connect()
    try:
        appointments = await db.appointment.find_many(where={"status": "SCHEDULED"})
    finally:
        await db.disconnect()
    return list(appointments)


async def push_to_google_calendar(token: str, event: Any) -> None:
    if not token:
        raise ValueError("Missing Google token")
    if event is None:
        raise ValueError("Missing event data")
    # In a production system this would call Google APIs. Here we simply succeed.


async def exchange_google_code_for_token(code: str) -> Dict[str, str]:
    if not code:
        raise ValueError("Authorization code is required")

    # Placeholder for OAuth exchange logic.
    return {
        "refresh_token": f"refresh-{code}",
        "email": f"user-{code}@example.com",
    }


async def store_google_credentials(user_id: str, token_data: Dict[str, Any]) -> None:
    await db.connect()
    try:
        await db.user.update(
            where={"id": user_id},
            data={
                "googleRefreshToken": token_data.get("refresh_token"),
                "googleEmail": token_data.get("email"),
            },
        )
    finally:
        await db.disconnect()

