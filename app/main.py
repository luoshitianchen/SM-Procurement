"""SM Procurement —— 采购管理系统：供应商、采购订单、明细行与收货。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from app import base

SERVICE = "sm-procurement"
VERSION = "2.0.0"
NAME = "SM Procurement"
DESCRIPTION = "采购管理系统：供应商、采购订单、明细行与收货"
PORT = 8530


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _init() -> None:
    with base.db_ctx() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, contact TEXT,
                category TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id TEXT PRIMARY KEY, po_number TEXT NOT NULL UNIQUE, supplier_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft', total_amount REAL NOT NULL DEFAULT 0,
                requested_by TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS po_line_items (
                id TEXT PRIMARY KEY, po_id TEXT NOT NULL, item TEXT NOT NULL,
                quantity REAL NOT NULL, unit_price REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS receipts (
                id TEXT PRIMARY KEY, po_id TEXT NOT NULL, received_at TEXT NOT NULL,
                quantity_received REAL NOT NULL, status TEXT NOT NULL DEFAULT 'partial'
            );
            """
        )


app = base.create_app(
    service=SERVICE, name=NAME, description=DESCRIPTION, version=VERSION, port=PORT,
    dependencies=["sm-iam", "sm-workflow-approval", "sm-audit-log-center"],
    events=["po.created", "po.approved", "goods.received"],
    overview_fn=lambda _r: {
        "summary": {
            "suppliers": base.get_db().execute("SELECT COUNT(*) FROM suppliers").fetchone()[0],
            "open_pos": base.get_db().execute("SELECT COUNT(*) FROM purchase_orders WHERE status NOT IN ('closed','cancelled')").fetchone()[0],
        }
    },
)
_init()


class SupplierIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    contact: str = Field(default="", max_length=80)
    category: str = Field(min_length=2, max_length=60)


class LineItemIn(BaseModel):
    item: str = Field(min_length=2, max_length=120)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class PurchaseOrderIn(BaseModel):
    po_number: str = Field(min_length=4, max_length=30)
    supplier_id: str = Field(min_length=8)
    requested_by: str = Field(min_length=1, max_length=80)
    line_items: list[LineItemIn] = Field(min_length=1)


class ReceiveIn(BaseModel):
    quantity_received: float = Field(gt=0)


@app.post("/api/procurement/suppliers", status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    supplier_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        try:
            conn.execute("INSERT INTO suppliers VALUES (?,?,?,?,?,?)", (supplier_id, payload.name, payload.contact, payload.category, "active", _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "供应商已存在") from exc
    return {"id": supplier_id, "name": payload.name}


@app.get("/api/procurement/suppliers")
def list_suppliers(category: str | None = None) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if category:
            rows = conn.execute("SELECT * FROM suppliers WHERE category=? ORDER BY created_at DESC", (category,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM suppliers ORDER BY created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/procurement/orders", status_code=status.HTTP_201_CREATED)
def create_purchase_order(payload: PurchaseOrderIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    po_id = str(uuid.uuid4())
    total = round(sum(item.quantity * item.unit_price for item in payload.line_items), 2)
    with base.db_ctx() as conn:
        if not conn.execute("SELECT 1 FROM suppliers WHERE id=?", (payload.supplier_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "供应商不存在")
        try:
            conn.execute("INSERT INTO purchase_orders (id, po_number, supplier_id, status, total_amount, requested_by, created_at) VALUES (?,?,?,?,?,?,?)", (po_id, payload.po_number, payload.supplier_id, "draft", total, payload.requested_by, _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "采购订单号已存在") from exc
        for line in payload.line_items:
            conn.execute("INSERT INTO po_line_items VALUES (?,?,?,?,?)", (str(uuid.uuid4()), po_id, line.item, line.quantity, line.unit_price))
        base.record_audit("po.created", payload.requested_by, f"po={po_id} amount={total}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": po_id, "po_number": payload.po_number, "total_amount": total, "status": "draft"}


@app.get("/api/procurement/orders")
def list_orders(status_: str | None = None) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if status_:
            rows = conn.execute("SELECT * FROM purchase_orders WHERE status=? ORDER BY created_at DESC", (status_,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM purchase_orders ORDER BY created_at DESC LIMIT 200").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.get("/api/procurement/orders/{po_id}")
def get_order(po_id: str) -> dict[str, Any]:
    with base.db_ctx() as conn:
        po = conn.execute("SELECT * FROM purchase_orders WHERE id=?", (po_id,)).fetchone()
        if not po:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购订单不存在")
        lines = conn.execute("SELECT * FROM po_line_items WHERE po_id=?", (po_id,)).fetchall()
        receipts = conn.execute("SELECT * FROM receipts WHERE po_id=?", (po_id,)).fetchall()
    return {**dict(po), "line_items": [dict(r) for r in lines], "receipts": [dict(r) for r in receipts]}


@app.post("/api/procurement/orders/{po_id}/approve")
def approve_order(po_id: str, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    with base.db_ctx() as conn:
        if conn.execute("UPDATE purchase_orders SET status='approved' WHERE id=? AND status='draft'", (po_id,)).rowcount == 0:
            raise HTTPException(status.HTTP_409_CONFLICT, "订单不存在或不可审批")
        base.record_audit("po.approved", "internal", f"po={po_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": po_id, "status": "approved"}


@app.post("/api/procurement/orders/{po_id}/receive")
def receive_goods(po_id: str, payload: ReceiveIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    receipt_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        po = conn.execute("SELECT * FROM purchase_orders WHERE id=? AND status='approved'", (po_id,)).fetchone()
        if not po:
            raise HTTPException(status.HTTP_409_CONFLICT, "订单不存在或未审批")
        received_total = conn.execute("SELECT COALESCE(SUM(quantity_received),0) FROM receipts WHERE po_id=?", (po_id,)).fetchone()[0]
        order_qty = conn.execute("SELECT COALESCE(SUM(quantity),0) FROM po_line_items WHERE po_id=?", (po_id,)).fetchone()[0]
        new_total = received_total + payload.quantity_received
        status_ = "closed" if new_total >= order_qty else "partial"
        conn.execute("INSERT INTO receipts (id, po_id, received_at, quantity_received, status) VALUES (?,?,?,?,?)", (receipt_id, po_id, _now(), payload.quantity_received, "complete" if status_ == "closed" else "partial"))
        conn.execute("UPDATE purchase_orders SET status=? WHERE id=?", (status_, po_id))
        base.record_audit("goods.received", "internal", f"po={po_id} qty={payload.quantity_received}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": receipt_id, "po_id": po_id, "quantity_received": payload.quantity_received, "order_status": status_}


@app.get("/api/procurement/stats")
def stats() -> dict[str, Any]:
    with base.db_ctx() as conn:
        def _count(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]
        row = conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM purchase_orders").fetchone()
        return {
            "suppliers": _count("SELECT COUNT(*) FROM suppliers"),
            "orders": _count("SELECT COUNT(*) FROM purchase_orders"),
            "approved_orders": _count("SELECT COUNT(*) FROM purchase_orders WHERE status='approved'"),
            "closed_orders": _count("SELECT COUNT(*) FROM purchase_orders WHERE status='closed'"),
            "total_spend": row[0],
        }
