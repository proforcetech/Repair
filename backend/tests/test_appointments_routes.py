from __future__ import annotations

import asyncio
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest


class _PrismaStub:
    def __init__(self, *args, **kwargs):
        pass


if "prisma" in sys.modules:
    sys.modules["prisma"].Prisma = _PrismaStub
else:
    sys.modules["prisma"] = types.SimpleNamespace(Prisma=_PrismaStub)

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.appointments import routes  # noqa: E402


class FakeAppointmentTable:
    def __init__(self) -> None:
        self.created: List[Dict[str, Any]] = []
        self.existing: List[Dict[str, Any]] = []

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = {"id": f"appt-{len(self.created)+1}", **data}
        self.created.append(record)
        return record

    async def find_first(self, where: Dict[str, Any]) -> Dict[str, Any] | None:
        technician = where.get("technicianId")
        bay = where.get("bayId")
        start_before = where.get("startTime", {}).get("lt")
        end_after = where.get("endTime", {}).get("gt")

        for record in self.existing:
            if technician and record.get("technicianId") != technician:
                continue
            if bay and record.get("bayId") != bay:
                continue
            if start_before and end_after:
                overlaps = not (
                    record["endTime"] <= end_after or record["startTime"] >= start_before
                )
                if overlaps:
                    return record
        return None

    async def find_many(self, **_: Any) -> List[Dict[str, Any]]:
        return list(self.existing)

    async def find_unique(self, where: Dict[str, Any]) -> Dict[str, Any] | None:
        lookup = where.get("id")
        for record in self.existing:
            if record.get("id") == lookup:
                return record
        return None

    async def update(self, where: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        lookup = where.get("id")
        for record in self.existing:
            if record.get("id") == lookup:
                record.update(data)
                return record
        updated = {"id": lookup, **data}
        self.existing.append(updated)
        return updated


class FakeTable:
    def __init__(self) -> None:
        self.records: List[Any] = []

    async def find_many(self, **_: Any) -> List[Any]:
        return list(self.records)

    async def update(self, **_: Any) -> Dict[str, Any]:
        return {}


class FakeAppointmentPhotoTable(FakeTable):
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data


class FakeMaintenanceContractTable(FakeTable):
    async def find_many(self, **_: Any) -> List[Any]:
        return []


class FakeDB:
    def __init__(self) -> None:
        self.appointment = FakeAppointmentTable()
        self.appointmentphoto = FakeAppointmentPhotoTable()
        self.user = FakeTable()
        self.bay = FakeTable()
        self.vehicle = FakeTable()
        self.maintenancecontract = FakeMaintenanceContractTable()
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False


@pytest.fixture()
def fake_environment(monkeypatch):
    fake_db = FakeDB()
    email_calls: List[Any] = []
    sms_calls: List[Any] = []

    async def fake_send_email(*args, **kwargs):
        email_calls.append((args, kwargs))

    async def fake_send_sms(*args, **kwargs):
        sms_calls.append((args, kwargs))

    monkeypatch.setattr(routes, "db", fake_db)
    monkeypatch.setattr(routes, "send_email", fake_send_email)
    monkeypatch.setattr(routes, "send_sms", fake_send_sms)

    return fake_db, email_calls, sms_calls


def test_public_booking_creates_appointment(fake_environment):
    fake_db, _, _ = fake_environment

    payload = routes.AppointmentBooking(
        title="Brake inspection",
        customerId="cust-1",
        vehicleId="veh-1",
        startTime=datetime.utcnow(),
        endTime=datetime.utcnow() + timedelta(hours=1),
        reason="Noise when braking",
    )

    appointment = asyncio.run(routes.book_appointment(payload))

    assert fake_db.appointment.created
    created = fake_db.appointment.created[0]
    assert created["customerId"] == "cust-1"
    assert created["status"] == "SCHEDULED"
    assert appointment["id"].startswith("appt-")


def test_auto_schedule_assigns_first_available_slot(fake_environment):
    fake_db, _, _ = fake_environment

    today = datetime.utcnow().date()
    fake_db.user.records = [SimpleNamespace(id="tech-1"), SimpleNamespace(id="tech-2")]
    fake_db.bay.records = [SimpleNamespace(id="bay-1")]
    fake_user = SimpleNamespace(id="user-123", role="CUSTOMER")

    response = asyncio.run(
        routes.auto_schedule_appointment(
            request=routes.AutoScheduleRequest(vehicleId="veh-42", durationMinutes=90),
            user=fake_user,
        )
    )

    created = fake_db.appointment.created[-1]
    expected_start = datetime.combine(today, datetime.min.time()).replace(hour=8)
    expected_end = expected_start + timedelta(minutes=90)
    assert response["message"] == "Scheduled"
    assert created["startTime"] == expected_start
    assert created["endTime"] == expected_end
    assert created["technicianId"] == "tech-1"
    assert created["bayId"] == "bay-1"
    assert created["customerId"] == "user-123"


def test_maintenance_reminders_only_notify_due(fake_environment):
    fake_db, email_calls, sms_calls = fake_environment

    overdue_vehicle = SimpleNamespace(
        make="Falcon",
        mileageReminderThreshold=5000,
        lastServiceMileage=6000,
        timeReminderMonths=6,
        lastServiceDate=datetime.utcnow() - timedelta(days=200),
        customer=SimpleNamespace(email="cust@example.com", phone="+15550001"),
    )
    fresh_vehicle = SimpleNamespace(
        make="Eagle",
        mileageReminderThreshold=5000,
        lastServiceMileage=3000,
        timeReminderMonths=6,
        lastServiceDate=datetime.utcnow() - timedelta(days=30),
        customer=SimpleNamespace(email="fresh@example.com", phone="+15550002"),
    )
    fake_db.vehicle.records = [overdue_vehicle, fresh_vehicle]

    result = asyncio.run(routes.run_maintenance_reminders())

    assert result["remindersSent"] == 1
    assert len(email_calls) == 1
    assert len(sms_calls) == 1
    assert email_calls[0][0][0] == "cust@example.com"
