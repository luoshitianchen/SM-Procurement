"""采购申请管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.proc_requisition import RequisitionCreate, RequisitionUpdate
from app.services.proc_requisition import RequisitionService

router = APIRouter(prefix="/api/procurement/requisitions", tags=["procurement-requisitions"])


@router.get("")
async def list_requisitions(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RequisitionService.list_requisitions(
        session, limit=limit, offset=offset, status_filter=status_filter
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_requisition(
    payload: RequisitionCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RequisitionService.create_requisition(session, payload, request)


@router.get("/{req_id}")
async def get_requisition(
    req_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RequisitionService.get_requisition(session, req_id)


@router.patch("/{req_id}")
async def update_requisition(
    req_id: str, payload: RequisitionUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RequisitionService.update_requisition(session, req_id, payload, request)


@router.post("/{req_id}/submit")
async def submit_requisition(
    req_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RequisitionService.submit_requisition(session, req_id, request)


@router.post("/{req_id}/approve")
async def approve_requisition(
    req_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RequisitionService.approve_requisition(session, req_id, request)


@router.post("/{req_id}/reject")
async def reject_requisition(
    req_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RequisitionService.reject_requisition(session, req_id, request)


@router.delete("/{req_id}")
async def delete_requisition(
    req_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RequisitionService.delete_requisition(session, req_id, request)
