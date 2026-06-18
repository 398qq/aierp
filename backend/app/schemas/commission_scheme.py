"""Pydantic schemas for 013 commission scheme configuration."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ── Request Schemas ─────────────────────────────────────────────────────


class TierCreate(BaseModel):
    tier_no: int = Field(..., ge=1)
    metric_type: str = "monthly_sales"
    low_amount: Decimal = Field(default=Decimal("0"), ge=0)
    high_amount: Decimal | None = None
    rate: Decimal = Field(..., ge=0, le=Decimal("1"))
    cap_amount: Decimal = Field(default=Decimal("0"), ge=0)
    floor_amount: Decimal = Field(default=Decimal("0"), ge=0)
    product_category: str | None = None
    customer_level: str | None = None


class AssignmentCreate(BaseModel):
    assignee_type: str = Field(..., pattern=r"^(user|role)$")
    assignee_id: int = Field(..., gt=0)


class SchemeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool = False
    tiers: list[TierCreate] = Field(default_factory=list, max_length=10)
    assignments: list[AssignmentCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> "SchemeCreate":
        if (
            self.effective_to
            and self.effective_from
            and self.effective_to <= self.effective_from
        ):
            raise ValueError("effective_to must be after effective_from")
        return self

    @model_validator(mode="after")
    def validate_tiers(self) -> "SchemeCreate":
        """Validate no overlap / no gap in tiers."""
        if not self.tiers:
            return self
        sorted_tiers = sorted(self.tiers, key=lambda t: t.low_amount)
        for i in range(len(sorted_tiers) - 1):
            curr = sorted_tiers[i]
            nxt = sorted_tiers[i + 1]
            if curr.high_amount is None:
                raise ValueError(
                    f"Tier {curr.tier_no} has no upper bound but is not the last tier"
                )
            if curr.high_amount != nxt.low_amount:
                raise ValueError(
                    f"Gap between tier {curr.tier_no} (high={curr.high_amount}) "
                    f"and tier {nxt.tier_no} (low={nxt.low_amount})"
                )
        return self


class SchemeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool | None = None
    tiers: list[TierCreate] | None = None
    assignments: list[AssignmentCreate] | None = None


class SchemeActivate(BaseModel):
    """Activate a draft/pending scheme manually."""


class SchemeAssign(BaseModel):
    assignments: list[AssignmentCreate]


class SchemeSimulateRequest(BaseModel):
    scheme_id: int
    period_from: date
    period_to: date
    user_ids: list[int] | None = None  # None = all


# ── Response Schemas ────────────────────────────────────────────────────


class TierResponse(BaseModel):
    id: int
    scheme_id: int
    tier_no: int
    metric_type: str
    low_amount: Decimal
    high_amount: Decimal | None
    rate: Decimal
    cap_amount: Decimal
    floor_amount: Decimal
    product_category: str | None
    customer_level: str | None

    model_config = {"from_attributes": True}


class AssignmentResponse(BaseModel):
    id: int
    scheme_id: int
    assignee_type: str
    assignee_id: int

    model_config = {"from_attributes": True}


class SchemeResponse(BaseModel):
    id: int
    name: str
    description: str | None
    version_no: int
    status: str
    effective_from: date
    effective_to: date | None
    is_default: bool
    created_by: int | None
    created_at: datetime | None
    updated_at: datetime | None
    tiers: list[TierResponse] = []
    assignments: list[AssignmentResponse] = []

    model_config = {"from_attributes": True}


class SchemeVersionResponse(BaseModel):
    id: int
    scheme_id: int
    version_no: int
    snapshot: Any
    changed_by: int
    changed_at: datetime

    model_config = {"from_attributes": True}


class SimulateUserRow(BaseModel):
    user_id: int
    name: str
    old_amount: Decimal
    new_amount: Decimal
    diff_pct: Decimal
    flag: str = "normal"  # normal | red


class SimulateResponse(BaseModel):
    summary: dict
    by_user: list[SimulateUserRow]


class MySchemeResponse(BaseModel):
    """Current user's effective scheme (simplified)."""

    scheme_id: int
    scheme_name: str
    version_no: int
    effective_from: date
    effective_to: date | None
    tiers: list[TierResponse] = []
