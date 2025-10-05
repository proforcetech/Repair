"""Tests for websocket broadcast helper utilities."""

import asyncio
import json

import pytest

from app.core import broadcast


class DummyWebSocket:
    """Minimal async websocket stub for exercising broadcast helpers."""

    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail
        self.messages: list[str] = []
        self.client_state = "CONNECTED"
        self.application_state = "CONNECTED"
        self._send_attempts = 0

    async def send_text(self, data: str) -> None:  # pragma: no cover - exercised via tests
        self._send_attempts += 1
        if self.should_fail:
            self.client_state = "DISCONNECTED"
            self.application_state = "DISCONNECTED"
            raise RuntimeError("connection closed")
        self.messages.append(data)


def test_broadcast_job_update_prunes_closed_connections(caplog):
    async def runner() -> None:
        ws_success_one = DummyWebSocket()
        ws_failing = DummyWebSocket(should_fail=True)
        ws_success_two = DummyWebSocket()

        broadcast.register_job_connection(ws_success_one)
        broadcast.register_job_connection(ws_failing)
        broadcast.register_job_connection(ws_success_two)

        with caplog.at_level("WARNING"):
            await broadcast.broadcast_job_update({"job": 123})

        # Messages delivered to healthy sockets.
        payload = json.dumps({"job": 123})
        assert ws_success_one.messages == [payload]
        assert ws_success_two.messages == [payload]

        # Failing socket removed from the registry and logged.
        assert ws_failing not in broadcast.iter_job_connections()
        assert any("Failed to send message" in rec.message for rec in caplog.records)

        # Subsequent broadcasts continue reaching remaining clients.
        await broadcast.broadcast_job_update({"job": 456})
        second_payload = json.dumps({"job": 456})
        assert ws_success_one.messages[-1] == second_payload
        assert ws_success_two.messages[-1] == second_payload

        broadcast.unregister_job_connection(ws_success_one)
        broadcast.unregister_job_connection(ws_success_two)

    asyncio.run(runner())


def test_notify_technician_removes_failed_connection():
    async def runner() -> None:
        ws_ok = DummyWebSocket()
        ws_fail = DummyWebSocket(should_fail=True)

        broadcast.register_technician_connection("ok", ws_ok)
        broadcast.register_technician_connection("fail", ws_fail)

        await broadcast.notify_technician("fail", {"note": "update"})

        # Connection removed after the failed send attempt.
        assert "fail" not in broadcast.iter_connected_technicians()

        await broadcast.notify_technician("ok", {"note": "status"})
        assert ws_ok.messages == [json.dumps({"note": "status"})]

        broadcast.unregister_technician_connection("ok")

    asyncio.run(runner())
