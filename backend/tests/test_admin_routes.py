from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterable

import pytest

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.admin import routes  # noqa: E402


async def _noop(*_: Any, **__: Any) -> None:
    return None


class _AsyncIterator:
    def __init__(self, results: Iterable[Any]) -> None:
        self._iterator = iter(results)

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D401 - helper
        return next(self._iterator)


def _constant(result: Any):
    async def _inner(*args: Any, **kwargs: Any) -> Any:
        return result

    return _inner


@pytest.mark.asyncio
async def test_financial_dashboard_shapes_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes.db, "connect", _noop)
    monkeypatch.setattr(routes.db, "disconnect", _noop)

    invoice_results = _AsyncIterator([
        SimpleNamespace(
            _sum=SimpleNamespace(total=1200.0),
            _count=SimpleNamespace(_all=8),
        ),
        SimpleNamespace(_count=SimpleNamespace(_all=3)),
    ])
    monkeypatch.setattr(routes.db, "invoice", SimpleNamespace(aggregate=invoice_results))

    monkeypatch.setattr(
        routes.db,
        "payment",
        SimpleNamespace(aggregate=_constant(SimpleNamespace(_sum=SimpleNamespace(amount=950.0)))),
    )

    user_results = _AsyncIterator([
        SimpleNamespace(_count=SimpleNamespace(_all=15)),
        SimpleNamespace(_count=SimpleNamespace(_all=6)),
    ])
    monkeypatch.setattr(routes.db, "user", SimpleNamespace(aggregate=user_results))

    monkeypatch.setattr(
        routes.db,
        "vehicle",
        SimpleNamespace(aggregate=_constant(SimpleNamespace(_count=SimpleNamespace(_all=42)))),
    )
    monkeypatch.setattr(
        routes.db,
        "customer",
        SimpleNamespace(aggregate=_constant(SimpleNamespace(_count=SimpleNamespace(_all=27)))),
    )

    job_results = _AsyncIterator([
        SimpleNamespace(_count=SimpleNamespace(_all=18)),
        SimpleNamespace(_count=SimpleNamespace(_all=11)),
    ])
    monkeypatch.setattr(routes.db, "job", SimpleNamespace(aggregate=job_results))

    warranty_results = _AsyncIterator([
        SimpleNamespace(_count=SimpleNamespace(_all=5)),
        SimpleNamespace(_count=SimpleNamespace(_all=2)),
    ])
    monkeypatch.setattr(routes.db, "warrantyclaim", SimpleNamespace(aggregate=warranty_results))

    result = await routes.financial_dashboard(SimpleNamespace(role="ADMIN"))

    assert result["financial"]["total_revenue"] == 1200.0
    assert result["financial"]["total_collected"] == 950.0
    assert result["counts"]["users"] == 15
    assert result["counts"]["technicians"] == 6
    assert result["counts"]["vehicles"] == 42
    assert result["counts"]["jobs"]["total"] == 18
    assert result["counts"]["jobs"]["completed"] == 11
    assert result["counts"]["invoices"]["total"] == 8
    assert result["counts"]["invoices"]["outstanding"] == 3
    assert result["counts"]["warranty_claims"]["total"] == 5
    assert result["counts"]["warranty_claims"]["open"] == 2


class _AuditAccessor:
    def __init__(self) -> None:
        self.find_calls: list[dict[str, Any]] = []

    async def aggregate(self, *_args: Any, **_kwargs: Any) -> Any:
        return SimpleNamespace(_count=SimpleNamespace(_all=10))

    async def find_many(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.find_calls.append(kwargs)
        return [{"id": "1", "action": "LOGIN"}]

    async def delete_many(self, **_kwargs: Any) -> Any:
        return SimpleNamespace(count=4)


@pytest.mark.asyncio
async def test_list_audit_logs_returns_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    accessor = _AuditAccessor()
    monkeypatch.setattr(routes.db, "connect", _noop)
    monkeypatch.setattr(routes.db, "disconnect", _noop)
    monkeypatch.setattr(routes.db, "auditlog", accessor)

    response = await routes.list_audit_logs(page=2, page_size=25, user=SimpleNamespace(role="ADMIN"))

    assert response["pagination"] == {"page": 2, "page_size": 25, "total": 10}
    assert response["items"] == [{"id": "1", "action": "LOGIN"}]
    assert accessor.find_calls == [
        {"order": {"timestamp": "desc"}, "skip": 25, "take": 25}
    ]


@pytest.mark.asyncio
async def test_purge_audit_logs_reports_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    accessor = _AuditAccessor()
    monkeypatch.setattr(routes.db, "connect", _noop)
    monkeypatch.setattr(routes.db, "disconnect", _noop)
    monkeypatch.setattr(routes.db, "auditlog", accessor)

    payload = routes.AuditLogPurgeRequest(older_than_days=30)
    result = await routes.purge_audit_logs(payload, user=SimpleNamespace(role="ADMIN"))

    assert result["deleted"] == 4
    assert "cutoff" in result
