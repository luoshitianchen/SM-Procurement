"""采购申请仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proc_requisition import ProcRequisition


async def get_requisition(session: AsyncSession, req_id: str) -> ProcRequisition | None:
    result = await session.execute(select(ProcRequisition).where(ProcRequisition.id == req_id))
    return result.scalar_one_or_none()


async def get_requisition_by_no(session: AsyncSession, req_no: str) -> ProcRequisition | None:
    result = await session.execute(select(ProcRequisition).where(ProcRequisition.req_no == req_no))
    return result.scalar_one_or_none()


async def list_requisitions(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None,
) -> list[ProcRequisition]:
    stmt = select(ProcRequisition).order_by(ProcRequisition.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(ProcRequisition.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_requisitions(session: AsyncSession, status: str | None = None) -> int:
    stmt = select(func.count(ProcRequisition.id))
    if status:
        stmt = stmt.where(ProcRequisition.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_requisition(session: AsyncSession, req: ProcRequisition) -> ProcRequisition:
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req


async def update_requisition(session: AsyncSession, req: ProcRequisition) -> ProcRequisition:
    await session.commit()
    await session.refresh(req)
    return req


async def delete_requisition(session: AsyncSession, req: ProcRequisition) -> None:
    await session.delete(req)
    await session.commit()
