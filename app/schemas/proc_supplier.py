"""采购供应商 Pydantic 模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=256)
    category: str = Field(default="", max_length=128)
    contact_person: str = Field(default="", max_length=128)
    phone: str = Field(default="", max_length=64)
    email: str = Field(default="", max_length=256)
    address: str = Field(default="", max_length=256)
    level: Literal["preferred", "approved", "blacklisted"] = "approved"
    remark: str = Field(default="", max_length=2000)


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=256)
    category: str | None = Field(default=None, max_length=128)
    contact_person: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=256)
    address: str | None = Field(default=None, max_length=256)
    level: Literal["preferred", "approved", "blacklisted"] | None = None
    remark: str | None = Field(default=None, max_length=2000)


class SupplierStatusUpdate(BaseModel):
    status: Literal["active", "inactive"]
