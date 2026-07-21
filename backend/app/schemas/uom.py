from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class UomDictResponse(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=50)
    uom_type: Literal["count", "package"]
    category: str | None = None
    description: str | None = None
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class UomDictCreate(BaseModel):
    code: str = Field(..., max_length=20, min_length=1)
    name: str = Field(..., max_length=50, min_length=1)
    uom_type: Literal["count", "package"]
    category: str | None = Field(None, max_length=30)
    description: str | None = None
    sort_order: int = 0


class UomDictUpdate(BaseModel):
    name: str | None = Field(None, max_length=50, min_length=1)
    uom_type: Literal["count", "package"] | None = None
    category: str | None = Field(None, max_length=30)
    description: str | None = None
    sort_order: int | None = None


class ProductPackLevelResponse(BaseModel):
    pack_level: int
    uom_code: str
    qty_per_parent: Decimal = Field(..., ge=0)

    class Config:
        from_attributes = True


class ProductPackLevelUpsert(BaseModel):
    pack_level: int = Field(..., ge=0, le=2)
    uom_code: str = Field(..., min_length=1, max_length=20)
    qty_per_parent: Decimal = Field(Decimal("1"), ge=0)
