"""采购供应商服务层。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.proc_supplier import ProcSupplier
from app.repositories import proc_supplier as repo
from app.schemas.proc_supplier import SupplierCreate, SupplierUpdate
from app.services.audit import record_audit


def _to_dict(s: ProcSupplier) -> dict:
    return {
        "id": s.id, "code": s.code, "name": s.name, "category": s.category,
        "contact_person": s.contact_person, "phone": s.phone,
        "email": s.email or "", "address": s.address, "level": s.level,
        "status": s.status, "remark": s.remark,
        "created_at": s.created_at.isoformat() if s.created_at else "",
        "updated_at": s.updated_at.isoformat() if s.updated_at else "",
    }


class SupplierService:
    @staticmethod
    async def list_suppliers(session: AsyncSession, limit: int, offset: int,
                             level: str | None, status_filter: str | None,
                             keyword: str | None) -> dict:
        rows = await repo.list_suppliers(session, limit=limit, offset=offset,
                                         level=level, status=status_filter, keyword=keyword)
        total = await repo.count_suppliers(session, level=level, status=status_filter, keyword=keyword)
        return {"total": total, "items": [_to_dict(s) for s in rows]}

    @staticmethod
    async def get_supplier(session: AsyncSession, supplier_id: str) -> dict:
        s = await repo.get_supplier(session, supplier_id)
        if not s:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "供应商不存在")
        return _to_dict(s)

    @staticmethod
    async def create_supplier(session: AsyncSession, payload: SupplierCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if await repo.get_supplier_by_code(session, payload.code):
            raise HTTPException(status.HTTP_409_CONFLICT, "供应商编码已存在")
        supplier = ProcSupplier(
            id=str(uuid.uuid4()), code=payload.code, name=payload.name,
            category=payload.category, contact_person=payload.contact_person,
            phone=payload.phone, email=payload.email, address=payload.address,
            level=payload.level, remark=payload.remark, status="active",
        )
        supplier = await repo.create_supplier(session, supplier)
        await record_audit(session, "proc.supplier.created", "internal",
                           f"code={payload.code}", request)
        return _to_dict(supplier)

    @staticmethod
    async def update_supplier(session: AsyncSession, supplier_id: str,
                              payload: SupplierUpdate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        s = await repo.get_supplier(session, supplier_id)
        if not s:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "供应商不存在")
        for field in ("name", "category", "contact_person", "phone", "email",
                      "address", "level", "remark"):
            value = getattr(payload, field)
            if value is not None:
                setattr(s, field, value)
        s = await repo.update_supplier(session, s)
        await record_audit(session, "proc.supplier.updated", "internal",
                           f"supplier_id={supplier_id}", request)
        return _to_dict(s)

    @staticmethod
    async def update_status(session: AsyncSession, supplier_id: str,
                            new_status: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        s = await repo.get_supplier(session, supplier_id)
        if not s:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "供应商不存在")
        s.status = new_status
        s = await repo.update_supplier(session, s)
        await record_audit(session, "proc.supplier.status_changed", "internal",
                           f"supplier_id={supplier_id} status={new_status}", request)
        return _to_dict(s)

    @staticmethod
    async def delete_supplier(session: AsyncSession, supplier_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        s = await repo.get_supplier(session, supplier_id)
        if not s:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "供应商不存在")
        await repo.delete_supplier(session, s)
        await record_audit(session, "proc.supplier.deleted", "internal",
                           f"supplier_id={supplier_id}", request)
        return {"deleted": True, "id": supplier_id}
