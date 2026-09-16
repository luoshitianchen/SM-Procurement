"""采购订单服务层：供应商/申请校验与订单状态机。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.proc_order import ProcOrder
from app.repositories import proc_order as repo
from app.repositories import proc_requisition as req_repo
from app.repositories import proc_supplier as supplier_repo
from app.schemas.proc_order import OrderCreate, OrderUpdate
from app.services.audit import record_audit

# 订单状态机流转
ALLOWED_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"received", "cancelled"},
    "received": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


def _to_dict(o: ProcOrder) -> dict:
    return {
        "id": o.id, "order_no": o.order_no, "supplier_id": o.supplier_id,
        "requisition_id": o.requisition_id, "title": o.title, "amount": o.amount,
        "order_date": o.order_date, "status": o.status, "remark": o.remark,
        "created_at": o.created_at.isoformat() if o.created_at else "",
        "updated_at": o.updated_at.isoformat() if o.updated_at else "",
    }


class OrderService:
    @staticmethod
    async def list_orders(session: AsyncSession, limit: int, offset: int,
                          status_filter: str | None, supplier_id: str | None) -> dict:
        rows = await repo.list_orders(session, limit=limit, offset=offset,
                                      status=status_filter, supplier_id=supplier_id)
        total = await repo.count_orders(session, status=status_filter, supplier_id=supplier_id)
        return {"total": total, "items": [_to_dict(o) for o in rows]}

    @staticmethod
    async def get_order(session: AsyncSession, order_id: str) -> dict:
        o = await repo.get_order(session, order_id)
        if not o:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购订单不存在")
        return _to_dict(o)

    @staticmethod
    async def create_order(session: AsyncSession, payload: OrderCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if payload.amount <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "订单金额必须大于 0")
        if await repo.get_order_by_no(session, payload.order_no):
            raise HTTPException(status.HTTP_409_CONFLICT, "订单号已存在")
        supplier = await supplier_repo.get_supplier(session, payload.supplier_id)
        if not supplier:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "供应商不存在")
        if supplier.level == "blacklisted":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "黑名单供应商不可下单")
        if payload.requisition_id:
            req = await req_repo.get_requisition(session, payload.requisition_id)
            if not req:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "关联采购申请不存在")
            if req.status != "approved":
                raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                    f"仅已审批通过的申请可下单（当前 {req.status}）")
        order = ProcOrder(
            id=str(uuid.uuid4()), order_no=payload.order_no,
            supplier_id=payload.supplier_id, requisition_id=payload.requisition_id,
            title=payload.title, amount=payload.amount, order_date=payload.order_date,
            remark=payload.remark, status="pending",
        )
        order = await repo.create_order(session, order)
        await record_audit(session, "proc.order.created", "internal",
                           f"order_no={payload.order_no}", request)
        return _to_dict(order)

    @staticmethod
    async def update_order(session: AsyncSession, order_id: str,
                            payload: OrderUpdate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        o = await repo.get_order(session, order_id)
        if not o:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购订单不存在")
        if o.status in ("closed", "cancelled"):
            raise HTTPException(status.HTTP_409_CONFLICT, "终态订单不可修改")
        for field in ("title", "amount", "order_date", "remark"):
            value = getattr(payload, field)
            if value is not None:
                setattr(o, field, value)
        o = await repo.update_order(session, o)
        await record_audit(session, "proc.order.updated", "internal",
                           f"order_id={order_id}", request)
        return _to_dict(o)

    @staticmethod
    async def change_status(session: AsyncSession, order_id: str,
                            new_status: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        o = await repo.get_order(session, order_id)
        if not o:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购订单不存在")
        allowed = ALLOWED_TRANSITIONS.get(o.status, set())
        if new_status not in allowed:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"不允许从 {o.status} 变更为 {new_status}")
        o.status = new_status
        o = await repo.update_order(session, o)
        await record_audit(session, "proc.order.status_changed", "internal",
                           f"order_id={order_id} status={new_status}", request)
        return _to_dict(o)

    @staticmethod
    async def delete_order(session: AsyncSession, order_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        o = await repo.get_order(session, order_id)
        if not o:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购订单不存在")
        if o.status not in ("pending",):
            raise HTTPException(status.HTTP_409_CONFLICT, "仅待确认订单可删除")
        await repo.delete_order(session, o)
        await record_audit(session, "proc.order.deleted", "internal",
                           f"order_id={order_id}", request)
        return {"deleted": True, "id": order_id}
