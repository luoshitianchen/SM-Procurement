"""采购申请 Pydantic 模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RequisitionCreate(BaseModel):
    req_no: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=256)
    requester: str = Field(default="", max_length=128)
    department: str = Field(default="", max_length=128)
    expected_date: str = Field(default="", max_length=32)
    total_amount: float = Field(default=0.0, ge=0)
    remark: str = Field(default="", max_length=2000)


class RequisitionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    requester: str | None = Field(default=None, max_length=128)
    department: str | None = Field(default=None, max_length=128)
    expected_date: str | None = Field(default=None, max_length=32)
    total_amount: float | None = Field(default=None, ge=0)
    remark: str | None = Field(default=None, max_length=2000)
