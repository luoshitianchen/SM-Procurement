"""采购订单管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.proc_order import OrderCreate, OrderStatusUpdate, OrderUpdate
from app.services.proc_order import OrderService

router = APIRouter(prefix="/api/procurement/orders", tags=["procurement-orders"])


@router.get("")
async def list_orders(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OrderService.list_orders(
        session, limit=limit, offset=offset,
        status_filter=status_filter, supplier_id=supplier_id
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OrderService.create_order(session, payload, request)


@router.get("/{order_id}")
async def get_order(
    order_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OrderService.get_order(session, order_id)


@router.patch("/{order_id}")
async def update_order(
    order_id: str, payload: OrderUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OrderService.update_order(session, order_id, payload, request)


@router.patch("/{order_id}/status")
async def change_order_status(
    order_id: str, payload: OrderStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OrderService.change_status(session, order_id, payload.status, request)


@router.delete("/{order_id}")
async def delete_order(
    order_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OrderService.delete_order(session, order_id, request)
