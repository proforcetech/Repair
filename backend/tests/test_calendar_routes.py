from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _PrismaStub:
    def __init__(self, *args, **kwargs):
        pass


if "prisma" in sys.modules:
    sys.modules["prisma"].Prisma = _PrismaStub
else:
    sys.modules["prisma"] = types.SimpleNamespace(Prisma=_PrismaStub)


sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.calendar import routes, services  # noqa: E402


class FakeUserTable:
    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    async def find_first(self, where: Dict[str, Any]) -> Dict[str, Any] | None:
        token = where.get("publicCalendarToken")
        for record in self.records:
            if record.get("publicCalendarToken") == token:
                return dict(record)
        return None

    async def find_unique(self, where: Dict[str, Any]) -> Dict[str, Any] | None:
        lookup = where.get("id")
        for record in self.records:
            if record.get("id") == lookup:
                return dict(record)
        return None

    async def update(self, where: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        lookup = where.get("id")
        for record in self.records:
            if record.get("id") == lookup:
                record.update(data)
                return dict(record)
        updated = {"id": lookup, **data}
        self.records.append(updated)
        return updated


class FakeJobTable:
    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []
        self.updated: List[Dict[str, Any]] = []

    async def find_many(self, where: Dict[str, Any]) -> List[Dict[str, Any]]:
        technician = where.get("technicianId")
        acknowledged = where.get("acknowledged")
        results = []
        for record in self.records:
            if technician and record.get("technicianId") != technician:
                continue
            if acknowledged is not None and record.get("acknowledged") != acknowledged:
                continue
            results.append(dict(record))
        return results

    async def update(self, where: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        lookup = where.get("id")
        for record in self.records:
            if record.get("id") == lookup:
                record.update(data)
                self.updated.append({"where": where, "data": data})
                return dict(record)
        raise KeyError("Job not found")


class FakeAppointmentTable:
    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []
        self.updated: List[Dict[str, Any]] = []

    async def find_first(self, where: Dict[str, Any]) -> Dict[str, Any] | None:
        external_id = where.get("externalEventId")
        provider = where.get("calendarProvider")
        for record in self.records:
            if record.get("externalEventId") == external_id and record.get("calendarProvider") == provider:
                return dict(record)
        return None

    async def find_many(self, where: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        status = (where or {}).get("status") if where else None
        if status:
            return [dict(rec) for rec in self.records if rec.get("status") == status]
        return [dict(rec) for rec in self.records]

    async def update(self, where: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        lookup = where.get("id")
        for record in self.records:
            if record.get("id") == lookup:
                record.update(data)
                self.updated.append({"where": where, "data": data})
                return dict(record)
        raise KeyError("Appointment not found")


class FakeWorkbayTable:
    async def find_many(self, **_: Any) -> List[Dict[str, Any]]:
        return []


class FakeDB:
    def __init__(self) -> None:
        self.connected = False
        self.user = FakeUserTable()
        self.job = FakeJobTable()
        self.appointment = FakeAppointmentTable()
        self.workbay = FakeWorkbayTable()

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    fake_db = FakeDB()
    monkeypatch.setattr(routes, "db", fake_db)
    monkeypatch.setattr(services, "db", fake_db)

    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def test_public_ics_marks_jobs_acknowledged(client: TestClient):
    fake_db = routes.db  # type: ignore[assignment]

    fake_db.user.records.append(
        {
            "id": "tech-1",
            "name": "Alex Technician",
            "publicCalendarToken": "token-123",
        }
    )

    start = datetime.utcnow().replace(microsecond=0)
    end = start + timedelta(hours=2)
    fake_db.job.records.append(
        {
            "id": "job-1",
            "technicianId": "tech-1",
            "acknowledged": False,
            "title": "Oil Change",
            "description": "Routine maintenance",
            "startTime": start,
            "endTime": end,
        }
    )

    response = client.get("/calendar/public/token-123.ics")

    assert response.status_code == 200
    body = response.text
    assert "BEGIN:VCALENDAR" in body
    assert "SUMMARY:Oil Change" in body
    assert fake_db.job.records[0]["acknowledged"] is True
    assert fake_db.job.updated, "Job acknowledgement should be recorded"


def test_webhook_updates_appointment_status(client: TestClient):
    fake_db = routes.db  # type: ignore[assignment]

    fake_db.appointment.records.append(
        {
            "id": "appt-1",
            "externalEventId": "evt-123",
            "calendarProvider": "GOOGLE",
            "status": "SCHEDULED",
        }
    )

    response = client.post(
        "/calendar/webhook",
        json={"event_id": "evt-123", "provider": "GOOGLE", "status": "cancelled"},
    )

    assert response.status_code == 200
    assert fake_db.appointment.updated
    assert fake_db.appointment.records[0]["status"] == "CANCELLED"


def test_webhook_missing_event_returns_404(client: TestClient):
    response = client.post(
        "/calendar/webhook",
        json={"event_id": "missing", "provider": "GOOGLE", "status": "cancelled"},
    )

    assert response.status_code == 404
