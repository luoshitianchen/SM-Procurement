"""采购订单 Pydantic 模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    order_no: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    supplier_id: str = Field(min_length=1, max_length=64)
    requisition_id: str = Field(default="", max_length=64)
    title: str = Field(min_length=1, max_length=256)
    amount: float = Field(gt=0)
    order_date: str = Field(default="", max_length=32)
    remark: str = Field(default="", max_length=2000)


class OrderUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    amount: float | None = Field(default=None, gt=0)
    order_date: str | None = Field(default=None, max_length=32)
    remark: str | None = Field(default=None, max_length=2000)


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "confirmed", "received", "closed", "cancelled"]
