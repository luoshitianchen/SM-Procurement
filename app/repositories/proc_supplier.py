"""采购供应商仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proc_supplier import ProcSupplier


async def get_supplier(session: AsyncSession, supplier_id: str) -> ProcSupplier | None:
    result = await session.execute(select(ProcSupplier).where(ProcSupplier.id == supplier_id))
    return result.scalar_one_or_none()


async def get_supplier_by_code(session: AsyncSession, code: str) -> ProcSupplier | None:
    result = await session.execute(select(ProcSupplier).where(ProcSupplier.code == code))
    return result.scalar_one_or_none()


async def list_suppliers(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    level: str | None = None, status: str | None = None, keyword: str | None = None,
) -> list[ProcSupplier]:
    stmt = select(ProcSupplier).order_by(ProcSupplier.created_at.desc()).limit(limit).offset(offset)
    if level:
        stmt = stmt.where(ProcSupplier.level == level)
    if status:
        stmt = stmt.where(ProcSupplier.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(ProcSupplier.name.like(like), ProcSupplier.code.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_suppliers(
    session: AsyncSession, level: str | None = None,
    status: str | None = None, keyword: str | None = None,
) -> int:
    stmt = select(func.count(ProcSupplier.id))
    if level:
        stmt = stmt.where(ProcSupplier.level == level)
    if status:
        stmt = stmt.where(ProcSupplier.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(ProcSupplier.name.like(like), ProcSupplier.code.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_supplier(session: AsyncSession, supplier: ProcSupplier) -> ProcSupplier:
    session.add(supplier)
    await session.commit()
    await session.refresh(supplier)
    return supplier


async def update_supplier(session: AsyncSession, supplier: ProcSupplier) -> ProcSupplier:
    await session.commit()
    await session.refresh(supplier)
    return supplier


async def delete_supplier(session: AsyncSession, supplier: ProcSupplier) -> None:
    await session.delete(supplier)
    await session.commit()
