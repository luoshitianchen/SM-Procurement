"""采购申请服务层：审批状态机。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.proc_requisition import ProcRequisition
from app.repositories import proc_requisition as repo
from app.schemas.proc_requisition import RequisitionCreate, RequisitionUpdate
from app.services.audit import record_audit

# 状态机：draft→submitted→approved / rejected
SUBMITTABLE = {"draft"}
APPROVABLE = {"submitted"}


def _to_dict(r: ProcRequisition) -> dict:
    return {
        "id": r.id, "req_no": r.req_no, "title": r.title,
        "requester": r.requester, "department": r.department,
        "expected_date": r.expected_date, "total_amount": r.total_amount,
        "status": r.status, "remark": r.remark,
        "created_at": r.created_at.isoformat() if r.created_at else "",
        "updated_at": r.updated_at.isoformat() if r.updated_at else "",
    }


class RequisitionService:
    @staticmethod
    async def list_requisitions(session: AsyncSession, limit: int, offset: int,
                                 status_filter: str | None) -> dict:
        rows = await repo.list_requisitions(session, limit=limit, offset=offset,
                                            status=status_filter)
        total = await repo.count_requisitions(session, status=status_filter)
        return {"total": total, "items": [_to_dict(r) for r in rows]}

    @staticmethod
    async def get_requisition(session: AsyncSession, req_id: str) -> dict:
        r = await repo.get_requisition(session, req_id)
        if not r:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购申请不存在")
        return _to_dict(r)

    @staticmethod
    async def create_requisition(session: AsyncSession, payload: RequisitionCreate,
                                 request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if payload.total_amount < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "申请金额不能为负")
        if await repo.get_requisition_by_no(session, payload.req_no):
            raise HTTPException(status.HTTP_409_CONFLICT, "申请单号已存在")
        req = ProcRequisition(
            id=str(uuid.uuid4()), req_no=payload.req_no, title=payload.title,
            requester=payload.requester, department=payload.department,
            expected_date=payload.expected_date, total_amount=payload.total_amount,
            remark=payload.remark, status="draft",
        )
        req = await repo.create_requisition(session, req)
        await record_audit(session, "proc.requisition.created", "internal",
                           f"req_no={payload.req_no}", request)
        return _to_dict(req)

    @staticmethod
    async def update_requisition(session: AsyncSession, req_id: str,
                                  payload: RequisitionUpdate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        r = await repo.get_requisition(session, req_id)
        if not r:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购申请不存在")
        if r.status != "draft":
            raise HTTPException(status.HTTP_409_CONFLICT, "仅草稿状态可修改")
        for field in ("title", "requester", "department", "expected_date",
                      "total_amount", "remark"):
            value = getattr(payload, field)
            if value is not None:
                setattr(r, field, value)
        r = await repo.update_requisition(session, r)
        await record_audit(session, "proc.requisition.updated", "internal",
                           f"requisition_id={req_id}", request)
        return _to_dict(r)

    @staticmethod
    async def submit_requisition(session: AsyncSession, req_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        r = await repo.get_requisition(session, req_id)
        if not r:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购申请不存在")
        if r.status not in SUBMITTABLE:
            raise HTTPException(status.HTTP_409_CONFLICT, f"当前状态 {r.status} 不可提交")
        r.status = "submitted"
        r = await repo.update_requisition(session, r)
        await record_audit(session, "proc.requisition.submitted", "internal",
                           f"requisition_id={req_id}", request)
        return _to_dict(r)

    @staticmethod
    async def approve_requisition(session: AsyncSession, req_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        r = await repo.get_requisition(session, req_id)
        if not r:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购申请不存在")
        if r.status not in APPROVABLE:
            raise HTTPException(status.HTTP_409_CONFLICT, f"当前状态 {r.status} 不可审批")
        r.status = "approved"
        r = await repo.update_requisition(session, r)
        await record_audit(session, "proc.requisition.approved", "internal",
                           f"requisition_id={req_id}", request)
        return _to_dict(r)

    @staticmethod
    async def reject_requisition(session: AsyncSession, req_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        r = await repo.get_requisition(session, req_id)
        if not r:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购申请不存在")
        if r.status not in APPROVABLE:
            raise HTTPException(status.HTTP_409_CONFLICT, f"当前状态 {r.status} 不可驳回")
        r.status = "rejected"
        r = await repo.update_requisition(session, r)
        await record_audit(session, "proc.requisition.rejected", "internal",
                           f"requisition_id={req_id}", request)
        return _to_dict(r)

    @staticmethod
    async def delete_requisition(session: AsyncSession, req_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        r = await repo.get_requisition(session, req_id)
        if not r:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "采购申请不存在")
        if r.status not in SUBMITTABLE:
            raise HTTPException(status.HTTP_409_CONFLICT, "仅草稿状态可删除")
        await repo.delete_requisition(session, r)
        await record_audit(session, "proc.requisition.deleted", "internal",
                           f"requisition_id={req_id}", request)
        return {"deleted": True, "id": req_id}
