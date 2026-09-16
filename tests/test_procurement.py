"""采购业务深化测试：供应商/申请/订单全生命周期与业务规则。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

INTERNAL_TOKEN = "test-internal-key-12345"
AUTH_HEADERS = {"X-Internal-Token": INTERNAL_TOKEN}

_counter = {"n": 0}


def uniq(prefix: str) -> str:
    _counter["n"] += 1
    return f"{prefix}-{_counter['n']}"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════
# 供应商
# ═══════════════════════════════════════════════════════════

class TestSupplierManagement:
    def test_create_supplier_success(self, client):
        resp = client.post("/api/procurement/suppliers", json={
            "code": "SUP-001", "name": "华星原材料厂", "category": "原材料",
            "contact_person": "王经理",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["code"] == "SUP-001"
        assert resp.json()["status"] == "active"

    def test_create_supplier_require_token(self, client):
        resp = client.post("/api/procurement/suppliers", json={
            "code": "SUP-NOAUTH", "name": "无令牌供应商",
        })
        assert resp.status_code in (401, 403)

    def test_create_supplier_duplicate_code(self, client):
        resp = client.post("/api/procurement/suppliers", json={
            "code": "SUP-001", "name": "重复编码",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_list_suppliers(self, client):
        resp = client.get("/api/procurement/suppliers", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_suppliers_keyword(self, client):
        resp = client.get("/api/procurement/suppliers?keyword=华星", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert any("华星" in i["name"] for i in resp.json()["items"])

    def test_get_supplier(self, client):
        create = client.post("/api/procurement/suppliers", json={
            "code": uniq("SUP"), "name": "查询供应商",
        }, headers=AUTH_HEADERS).json()
        resp = client.get(f"/api/procurement/suppliers/{create['id']}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["id"] == create["id"]

    def test_get_supplier_not_found(self, client):
        resp = client.get("/api/procurement/suppliers/nonexistent", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_update_supplier(self, client):
        create = client.post("/api/procurement/suppliers", json={
            "code": uniq("SUP"), "name": "待更新",
        }, headers=AUTH_HEADERS).json()
        resp = client.patch(f"/api/procurement/suppliers/{create['id']}", json={
            "contact_person": "新联系人", "level": "preferred",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["contact_person"] == "新联系人"
        assert resp.json()["level"] == "preferred"


# ═══════════════════════════════════════════════════════════
# 采购申请
# ═══════════════════════════════════════════════════════════

class TestRequisitionManagement:
    def test_create_requisition_success(self, client):
        resp = client.post("/api/procurement/requisitions", json={
            "req_no": uniq("REQ"), "title": "办公电脑采购",
            "requester": "张三", "department": "IT部", "total_amount": 60000,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["status"] == "draft"

    def test_create_requisition_require_token(self, client):
        resp = client.post("/api/procurement/requisitions", json={
            "req_no": "REQ-NOAUTH", "title": "无令牌申请",
        })
        assert resp.status_code in (401, 403)

    def test_create_requisition_duplicate_no(self, client):
        no = uniq("REQ")
        client.post("/api/procurement/requisitions", json={
            "req_no": no, "title": "首次",
        }, headers=AUTH_HEADERS)
        resp = client.post("/api/procurement/requisitions", json={
            "req_no": no, "title": "重复",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_approve_flow(self, client):
        create = client.post("/api/procurement/requisitions", json={
            "req_no": uniq("REQ"), "title": "审批流申请",
        }, headers=AUTH_HEADERS).json()
        # draft -> submitted
        sub = client.post(f"/api/procurement/requisitions/{create['id']}/submit", headers=AUTH_HEADERS)
        assert sub.status_code == 200
        assert sub.json()["status"] == "submitted"
        # submitted -> approved
        appr = client.post(f"/api/procurement/requisitions/{create['id']}/approve", headers=AUTH_HEADERS)
        assert appr.status_code == 200
        assert appr.json()["status"] == "approved"

    def test_reject_flow(self, client):
        create = client.post("/api/procurement/requisitions", json={
            "req_no": uniq("REQ"), "title": "驳回申请",
        }, headers=AUTH_HEADERS).json()
        client.post(f"/api/procurement/requisitions/{create['id']}/submit", headers=AUTH_HEADERS)
        resp = client.post(f"/api/procurement/requisitions/{create['id']}/reject", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_submit_non_draft_rejected(self, client):
        create = client.post("/api/procurement/requisitions", json={
            "req_no": uniq("REQ"), "title": "二次提交",
        }, headers=AUTH_HEADERS).json()
        client.post(f"/api/procurement/requisitions/{create['id']}/submit", headers=AUTH_HEADERS)
        resp = client.post(f"/api/procurement/requisitions/{create['id']}/submit", headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_update_non_draft_rejected(self, client):
        create = client.post("/api/procurement/requisitions", json={
            "req_no": uniq("REQ"), "title": "已提交申请",
        }, headers=AUTH_HEADERS).json()
        client.post(f"/api/procurement/requisitions/{create['id']}/submit", headers=AUTH_HEADERS)
        resp = client.patch(f"/api/procurement/requisitions/{create['id']}", json={
            "title": "试图修改",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_list_requisitions_filter_status(self, client):
        resp = client.get("/api/procurement/requisitions?status=approved", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert all(i["status"] == "approved" for i in resp.json()["items"])

    def test_delete_draft_requisition(self, client):
        create = client.post("/api/procurement/requisitions", json={
            "req_no": uniq("REQ"), "title": "待删草稿",
        }, headers=AUTH_HEADERS).json()
        resp = client.delete(f"/api/procurement/requisitions/{create['id']}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════════════════
# 采购订单
# ═══════════════════════════════════════════════════════════

class TestOrderManagement:
    def _supplier_id(self, client, level: str = "approved") -> str:
        return client.post("/api/procurement/suppliers", json={
            "code": uniq("SUP"), "name": "订单供应商", "level": level,
        }, headers=AUTH_HEADERS).json()["id"]

    def _approved_requisition_id(self, client) -> str:
        req = client.post("/api/procurement/requisitions", json={
            "req_no": uniq("REQ"), "title": "订单关联申请",
        }, headers=AUTH_HEADERS).json()
        client.post(f"/api/procurement/requisitions/{req['id']}/submit", headers=AUTH_HEADERS)
        client.post(f"/api/procurement/requisitions/{req['id']}/approve", headers=AUTH_HEADERS)
        return req["id"]

    def test_create_order_success(self, client):
        sid = self._supplier_id(client)
        resp = client.post("/api/procurement/orders", json={
            "order_no": uniq("PO"), "supplier_id": sid,
            "title": "显示器采购", "amount": 30000,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"

    def test_create_order_require_token(self, client):
        sid = self._supplier_id(client)
        resp = client.post("/api/procurement/orders", json={
            "order_no": "PO-NOAUTH", "supplier_id": sid, "title": "无令牌订单", "amount": 1,
        })
        assert resp.status_code in (401, 403)

    def test_create_order_duplicate_no(self, client):
        sid = self._supplier_id(client)
        no = uniq("PO")
        client.post("/api/procurement/orders", json={
            "order_no": no, "supplier_id": sid, "title": "首次", "amount": 100,
        }, headers=AUTH_HEADERS)
        resp = client.post("/api/procurement/orders", json={
            "order_no": no, "supplier_id": sid, "title": "重复", "amount": 100,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_create_order_supplier_not_exist(self, client):
        resp = client.post("/api/procurement/orders", json={
            "order_no": uniq("PO"), "supplier_id": "ghost", "title": "幽灵供应商", "amount": 100,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 400

    def test_create_order_blacklisted_supplier_rejected(self, client):
        sid = self._supplier_id(client, level="blacklisted")
        resp = client.post("/api/procurement/orders", json={
            "order_no": uniq("PO"), "supplier_id": sid, "title": "黑名单下单", "amount": 100,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 400

    def test_create_order_with_unapproved_requisition_rejected(self, client):
        sid = self._supplier_id(client)
        draft_req = client.post("/api/procurement/requisitions", json={
            "req_no": uniq("REQ"), "title": "未审批申请",
        }, headers=AUTH_HEADERS).json()
        resp = client.post("/api/procurement/orders", json={
            "order_no": uniq("PO"), "supplier_id": sid,
            "requisition_id": draft_req["id"], "title": "挂未审批申请", "amount": 100,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 400

    def test_create_order_with_approved_requisition(self, client):
        sid = self._supplier_id(client)
        rid = self._approved_requisition_id(client)
        resp = client.post("/api/procurement/orders", json={
            "order_no": uniq("PO"), "supplier_id": sid, "requisition_id": rid,
            "title": "挂已审批申请", "amount": 100,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["requisition_id"] == rid

    def test_order_status_flow(self, client):
        sid = self._supplier_id(client)
        order = client.post("/api/procurement/orders", json={
            "order_no": uniq("PO"), "supplier_id": sid, "title": "状态流转", "amount": 100,
        }, headers=AUTH_HEADERS).json()
        confirmed = client.patch(f"/api/procurement/orders/{order['id']}/status", json={
            "status": "confirmed",
        }, headers=AUTH_HEADERS)
        assert confirmed.status_code == 200
        received = client.patch(f"/api/procurement/orders/{order['id']}/status", json={
            "status": "received",
        }, headers=AUTH_HEADERS)
        assert received.json()["status"] == "received"

    def test_order_invalid_transition_rejected(self, client):
        sid = self._supplier_id(client)
        order = client.post("/api/procurement/orders", json={
            "order_no": uniq("PO"), "supplier_id": sid, "title": "非法流转", "amount": 100,
        }, headers=AUTH_HEADERS).json()
        # pending 不可直接 closed
        resp = client.patch(f"/api/procurement/orders/{order['id']}/status", json={
            "status": "closed",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_list_orders(self, client):
        resp = client.get("/api/procurement/orders", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_get_order_not_found(self, client):
        resp = client.get("/api/procurement/orders/nonexistent", headers=AUTH_HEADERS)
        assert resp.status_code == 404
