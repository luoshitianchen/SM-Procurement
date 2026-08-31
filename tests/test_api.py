"""SM Procurement 领域测试：供应商、采购订单、审批、收货与统计。"""

import pytest
from fastapi.testclient import TestClient

from app import base
from app.main import VERSION, app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(base, "internal_api_key", lambda: "TEST")
    base.reset_state()
    from app.main import _init as init_db
    init_db()
    with TestClient(app) as c:
        c.headers["X-Internal-Token"] = "TEST"
        yield c


def _supplier(client, name="华信电子"):
    return client.post("/api/procurement/suppliers", json={"name": name, "contact": "陈经理", "category": "元器件"}).json()["id"]


def _order(client, supplier_id, po_number="PO-2026-001", qty=10, price=100):
    return client.post("/api/procurement/orders", json={"po_number": po_number, "supplier_id": supplier_id, "requested_by": "采购员小王", "line_items": [{"item": "芯片", "quantity": qty, "unit_price": price}]}).json()["id"]


def test_health_and_version(client):
    r = client.get("/health", headers={"X-Request-Id": "suite-test"})
    assert r.status_code == 200
    assert r.json()["version"] == VERSION


def test_supplier_and_order(client):
    supplier_id = _supplier(client)
    assert client.post("/api/procurement/suppliers", json={"name": "华信电子", "category": "xx"}).status_code == 409
    po_id = _order(client, supplier_id)
    assert client.post("/api/procurement/orders", json={"po_number": "PO-2026-001", "supplier_id": supplier_id, "requested_by": "r", "line_items": [{"item": "芯片", "quantity": 1, "unit_price": 1}]}).status_code == 409
    detail = client.get(f"/api/procurement/orders/{po_id}").json()
    assert detail["total_amount"] == 1000
    assert len(detail["line_items"]) == 1


def test_order_requires_supplier(client):
    assert client.post("/api/procurement/orders", json={"po_number": "PO-XXX", "supplier_id": "no-such-supplier", "requested_by": "r", "line_items": [{"item": "xx", "quantity": 1, "unit_price": 1}]}).status_code == 404


def test_approve_and_receive(client):
    supplier_id = _supplier(client)
    po_id = _order(client, supplier_id, qty=10)
    assert client.post(f"/api/procurement/orders/{po_id}/approve").json()["status"] == "approved"
    assert client.post(f"/api/procurement/orders/{po_id}/receive", json={"quantity_received": 10}).json()["order_status"] == "closed"
    # 已关闭不可再收货
    assert client.post(f"/api/procurement/orders/{po_id}/receive", json={"quantity_received": 1}).status_code == 409


def test_partial_receive(client):
    supplier_id = _supplier(client)
    po_id = _order(client, supplier_id, qty=10)
    client.post(f"/api/procurement/orders/{po_id}/approve")
    assert client.post(f"/api/procurement/orders/{po_id}/receive", json={"quantity_received": 4}).json()["order_status"] == "partial"


def test_stats(client):
    supplier_id = _supplier(client)
    _order(client, supplier_id)
    stats = client.get("/api/procurement/stats").json()
    assert stats["suppliers"] == 1
    assert stats["orders"] == 1
    assert stats["total_spend"] == 1000


def test_manifest_and_crypto(client):
    assert client.get("/api/integration/manifest").json()["version"] == VERSION
    enc = client.post("/api/crypto/encrypt", json={"value": "x"}).json()["ciphertext"]
    assert client.post("/api/crypto/decrypt", json={"value": enc}).json()["plaintext"] == "x"


def test_write_requires_auth(client):
    del client.headers["X-Internal-Token"]
    assert client.post("/api/procurement/suppliers", json={"name": "s", "category": "c"}).status_code == 401
