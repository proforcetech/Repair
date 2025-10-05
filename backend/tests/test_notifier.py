from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

if "dotenv" not in sys.modules:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None)

if "aiosmtplib" not in sys.modules:
    async def _fake_send(*args: Any, **kwargs: Any) -> None:
        return None

    sys.modules["aiosmtplib"] = types.SimpleNamespace(send=_fake_send)


sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core import notifier


def test_send_email_uses_aiosmtplib(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_send(*args: Any, **kwargs: Any) -> None:
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(notifier.aiosmtplib, "send", fake_send)
    monkeypatch.setattr(notifier.settings.smtp, "host", "smtp.example.com")
    monkeypatch.setattr(notifier.settings.smtp, "port", 2525)
    monkeypatch.setattr(notifier.settings.smtp, "username", "smtp-user")
    monkeypatch.setattr(notifier.settings.smtp, "password", "smtp-pass")
    monkeypatch.setattr(notifier.settings.smtp, "from_address", "alerts@example.com")

    async def _run() -> None:
        await notifier.send_email("user@example.com", "System Update", "Hello!")

    asyncio.run(_run())

    msg = captured["args"][0]
    assert msg["To"] == "user@example.com"
    assert msg["From"] == "alerts@example.com"
    assert msg["Subject"] == "System Update"
    assert msg.get_content().strip() == "Hello!"

    kwargs = captured["kwargs"]
    assert kwargs["hostname"] == "smtp.example.com"
    assert kwargs["port"] == 2525
    assert kwargs["username"] == "smtp-user"
    assert kwargs["password"] == "smtp-pass"
    assert kwargs["start_tls"] is True


def test_notify_user_reuses_send_email(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str]] = []

    async def fake_send_email(to_email: str, subject: str, body: str) -> None:
        calls.append((to_email, subject, body))

    monkeypatch.setattr(notifier, "send_email", fake_send_email)

    asyncio.run(notifier.notify_user("user@example.com", "Greetings", "Body text"))

    assert calls == [("user@example.com", "Greetings", "Body text")]


def test_send_sms_uses_registered_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyProvider:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        async def send(self, phone: str, body: str) -> None:
            self.calls.append((phone, body))

    provider = DummyProvider()

    monkeypatch.setattr(notifier, "_sms_provider", provider, raising=False)

    asyncio.run(notifier.send_sms("+15550000000", "Reminder"))

    assert provider.calls == [("+15550000000", "Reminder")]


def test_twilio_provider_runs_in_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    class DummyMessages:
        def create(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    dummy_client = SimpleNamespace(messages=DummyMessages())

    class DummyLoop:
        def __init__(self) -> None:
            self.executors: list[Any] = []

        def run_in_executor(self, executor: Any, func: Any):
            self.executors.append(executor)

            async def _runner() -> Any:
                return func()

            return _runner()

    loop = DummyLoop()
    monkeypatch.setattr(notifier.asyncio, "get_running_loop", lambda: loop)

    provider = notifier.TwilioSMSProvider("sid", "token", "+19995550000", client=dummy_client)

    async def _run() -> None:
        await provider.send("+12223334444", "Inventory low")

    asyncio.run(_run())

    assert calls == [
        {"to": "+12223334444", "from_": "+19995550000", "body": "Inventory low"}
    ]
    assert loop.executors == [None]


def test_send_sms_builds_default_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyProvider:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        async def send(self, phone: str, body: str) -> None:
            self.calls.append((phone, body))

    provider = DummyProvider()
    monkeypatch.setattr(notifier, "_sms_provider", None, raising=False)
    monkeypatch.setattr(notifier, "_build_default_sms_provider", lambda: provider)

    asyncio.run(notifier.send_sms("+14445556666", "Ping"))

    assert provider.calls == [("+14445556666", "Ping")]
