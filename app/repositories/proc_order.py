"""采购订单仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proc_order import ProcOrder


async def get_order(session: AsyncSession, order_id: str) -> ProcOrder | None:
    result = await session.execute(select(ProcOrder).where(ProcOrder.id == order_id))
    return result.scalar_one_or_none()


async def get_order_by_no(session: AsyncSession, order_no: str) -> ProcOrder | None:
    result = await session.execute(select(ProcOrder).where(ProcOrder.order_no == order_no))
    return result.scalar_one_or_none()


async def list_orders(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, supplier_id: str | None = None,
) -> list[ProcOrder]:
    stmt = select(ProcOrder).order_by(ProcOrder.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(ProcOrder.status == status)
    if supplier_id:
        stmt = stmt.where(ProcOrder.supplier_id == supplier_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_orders(
    session: AsyncSession, status: str | None = None, supplier_id: str | None = None,
) -> int:
    stmt = select(func.count(ProcOrder.id))
    if status:
        stmt = stmt.where(ProcOrder.status == status)
    if supplier_id:
        stmt = stmt.where(ProcOrder.supplier_id == supplier_id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_order(session: AsyncSession, order: ProcOrder) -> ProcOrder:
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def update_order(session: AsyncSession, order: ProcOrder) -> ProcOrder:
    await session.commit()
    await session.refresh(order)
    return order


async def delete_order(session: AsyncSession, order: ProcOrder) -> None:
    await session.delete(order)
    await session.commit()
