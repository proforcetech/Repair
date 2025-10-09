from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.invoice import routes


@dataclass
class FakeRecord:
    data: Dict[str, Any]

    def copy(self) -> Dict[str, Any]:
        return dict(self.data)


class FakeCustomerTable:
    def __init__(self) -> None:
        self.records: Dict[str, Dict[str, Any]] = {}

    def add(self, customer: Dict[str, Any]) -> None:
        self.records[customer["id"]] = dict(customer)

    def get(self, customer_id: str | None) -> Dict[str, Any] | None:
        if not customer_id:
            return None
        record = self.records.get(customer_id)
        return dict(record) if record else None


class FakePaymentTable:
    def __init__(self, db: "FakeDB") -> None:
        self._db = db
        self.records: List[Dict[str, Any]] = []

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = {"id": f"pay-{len(self.records) + 1}", **data}
        self.records.append(record)
        return dict(record)

    async def find_many(self, where: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        if not where:
            return [dict(record) for record in self.records]
        invoice_id = where.get("invoiceId")
        return [dict(record) for record in self.records if record.get("invoiceId") == invoice_id]


class FakeInvoiceTable:
    def __init__(self, db: "FakeDB") -> None:
        self._db = db
        self.records: Dict[str, Dict[str, Any]] = {}
        self.updated: List[Dict[str, Any]] = []

    async def find_many(self, where: Dict[str, Any] | None = None, include: Dict[str, Any] | None = None, order_by: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:  # noqa: ANN001
        invoices = list(self.records.values())
        if where:
            for key, value in where.items():
                invoices = [record for record in invoices if record.get(key) == value]
        if order_by and "createdAt" in order_by:
            invoices.sort(key=lambda record: record.get("createdAt"), reverse=order_by["createdAt"] == "desc")
        if order_by and "finalizedAt" in order_by:
            invoices.sort(key=lambda record: record.get("finalizedAt"), reverse=order_by["finalizedAt"] == "desc")
        return [self._apply_include(record, include) for record in invoices]

    async def find_unique(self, where: Dict[str, Any], include: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
        record = self.records.get(where.get("id"))
        if not record:
            return None
        return self._apply_include(record, include)

    async def update(self, where: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        record = self.records.get(where.get("id"))
        if not record:
            raise KeyError("Invoice not found")
        record.update(data)
        self.updated.append({"where": where, "data": data})
        return self._apply_include(record, None)

    def _apply_include(self, record: Dict[str, Any], include: Dict[str, Any] | None) -> Dict[str, Any]:
        result = dict(record)
        if include and include.get("payments"):
            result["payments"] = [
                dict(payment) for payment in self._db.payment.records if payment.get("invoiceId") == record.get("id")
            ]
        if include and include.get("items"):
            result["items"] = [dict(item) for item in record.get("items", [])]
        if include and include.get("customer"):
            customer = self._db.customer.get(record.get("customerId"))
            if customer:
                result["customer"] = customer
        return result


class FakeDB:
    def __init__(self) -> None:
        self.connected = False
        self.invoice = FakeInvoiceTable(self)
        self.payment = FakePaymentTable(self)
        self.customer = FakeCustomerTable()

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    fake_db = FakeDB()
    monkeypatch.setattr(routes, "db", fake_db)

    api = FastAPI()
    api.include_router(routes.router)
    return api


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    test_client = TestClient(app)
    test_client.app.dependency_overrides[routes.get_current_user] = lambda: SimpleNamespace(id="manager-1", role="MANAGER")
    return test_client


def seed_invoice(fake_db: FakeDB, invoice_id: str = "inv-1", *, total: float = 200.0, late_fee: float = 0.0) -> None:
    fake_db.customer.add({"id": "cust-1", "name": "Jamie Customer", "email": "jamie@example.com"})
    fake_db.invoice.records[invoice_id] = {
        "id": invoice_id,
        "number": invoice_id,
        "customerId": "cust-1",
        "status": "DRAFT",
        "total": total,
        "lateFee": late_fee,
        "createdAt": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "dueDate": datetime(2024, 1, 15, tzinfo=timezone.utc).isoformat(),
        "issuedDate": datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
        "items": [
            {"id": "item-1", "description": "Brake pads", "quantity": 1, "unitPrice": total / 2, "cost": total / 4},
            {"id": "item-2", "description": "Labor", "quantity": 1, "unitPrice": total / 2, "cost": total / 3},
        ],
        "customer": {"id": "cust-1", "name": "Jamie Customer", "email": "jamie@example.com"},
        "finalizedAt": datetime(2024, 1, 2, tzinfo=timezone.utc),
    }


def get_fake_db() -> FakeDB:
    assert isinstance(routes.db, FakeDB)
    return routes.db


def test_manual_payment_transitions_invoice_status(client: TestClient) -> None:
    fake_db = get_fake_db()
    seed_invoice(fake_db)

    response = client.post("/invoice/inv-1/pay", json={"amount": 100, "method": "CASH"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PARTIALLY_PAID"
    assert body["payments"][-1]["runningBalance"] == 100

    response = client.post("/invoice/inv-1/pay", json={"amount": 100, "method": "CARD"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PAID"
    assert body["balanceDue"] == 0


def test_finalize_invoice_marks_finalized(client: TestClient) -> None:
    fake_db = get_fake_db()
    seed_invoice(fake_db)

    response = client.post("/invoice/inv-1/finalize")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FINALIZED"
    assert fake_db.invoice.records["inv-1"]["status"] == "FINALIZED"


def test_margin_endpoint_uses_line_items(client: TestClient) -> None:
    fake_db = get_fake_db()
    seed_invoice(fake_db, total=300.0)

    response = client.get("/invoice/inv-1/margin")
    assert response.status_code == 200
    body = response.json()
    assert pytest.approx(body["total_price"], rel=1e-3) == 300.0
    assert body["gross_margin_percent"] > 0


def test_margin_analytics_aggregates_finalized_invoices(client: TestClient) -> None:
    fake_db = get_fake_db()
    seed_invoice(fake_db, invoice_id="inv-1", total=300.0)
    fake_db.invoice.records["inv-1"]["status"] = "FINALIZED"
    seed_invoice(fake_db, invoice_id="inv-2", total=150.0)
    fake_db.invoice.records["inv-2"]["status"] = "FINALIZED"

    response = client.get("/invoice/analytics/margin")
    assert response.status_code == 200
    analytics = response.json()
    assert analytics["lowMarginInvoices"] >= 0
    assert len(analytics["series"]) == 2


def test_stripe_checkout_mocked(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    fake_db = get_fake_db()
    seed_invoice(fake_db, total=120.0)

    captured: Dict[str, Any] = {}

    class FakeSession:
        url = "https://stripe.test/session"

    def fake_create(**kwargs: Any) -> FakeSession:
        captured.update(kwargs)
        return FakeSession()

    monkeypatch.setattr(routes.stripe.checkout.Session, "create", fake_create)  # type: ignore[attr-defined]
    client.app.dependency_overrides[routes.get_current_user] = lambda: SimpleNamespace(id="cust-1", role="CUSTOMER")

    response = client.post("/invoice/inv-1/pay/online")
    assert response.status_code == 200
    assert response.json()["checkout_url"] == "https://stripe.test/session"
    assert captured["metadata"]["invoice_id"] == "inv-1"
    assert captured["line_items"][0]["price_data"]["unit_amount"] == 12000
