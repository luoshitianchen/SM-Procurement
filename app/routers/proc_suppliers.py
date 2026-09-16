"""采购供应商管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.proc_supplier import SupplierCreate, SupplierStatusUpdate, SupplierUpdate
from app.services.proc_supplier import SupplierService

router = APIRouter(prefix="/api/procurement/suppliers", tags=["procurement-suppliers"])


@router.get("")
async def list_suppliers(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    level: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await SupplierService.list_suppliers(
        session, limit=limit, offset=offset, level=level,
        status_filter=status_filter, keyword=keyword
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await SupplierService.create_supplier(session, payload, request)


@router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await SupplierService.get_supplier(session, supplier_id)


@router.patch("/{supplier_id}")
async def update_supplier(
    supplier_id: str, payload: SupplierUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await SupplierService.update_supplier(session, supplier_id, payload, request)


@router.patch("/{supplier_id}/status")
async def update_supplier_status(
    supplier_id: str, payload: SupplierStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await SupplierService.update_status(session, supplier_id, payload.status, request)


@router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await SupplierService.delete_supplier(session, supplier_id, request)
