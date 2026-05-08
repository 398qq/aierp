"""Finance schemas — Pydantic v2 models for payments, invoices, targets, contracts, notifications."""

from datetime import datetime
from pydantic import BaseModel, Field


# --- PaymentRecord ---

class PaymentRecordCreate(BaseModel):
    sales_order_id: int
    customer_id: int
    amount: float
    payment_date: str | None = None
    payment_method: str = "bank"
    status: str = "pending"
    notes: str | None = None


class PaymentRecordUpdate(BaseModel):
    sales_order_id: int | None = None
    customer_id: int | None = None
    amount: float | None = None
    payment_date: str | None = None
    payment_method: str | None = None
    status: str | None = None
    notes: str | None = None


# --- Invoice ---

class InvoiceCreate(BaseModel):
    invoice_no: str | None = None
    sales_order_id: int
    customer_id: int
    amount: float
    tax_amount: float = 0
    invoice_date: str | None = None
    invoice_type: str = "普通发票"
    status: str = "draft"
    notes: str | None = None


class InvoiceUpdate(BaseModel):
    invoice_no: str | None = None
    sales_order_id: int | None = None
    customer_id: int | None = None
    amount: float | None = None
    tax_amount: float | None = None
    invoice_date: str | None = None
    invoice_type: str | None = None
    status: str | None = None
    notes: str | None = None


# --- SalesTarget ---

class SalesTargetCreate(BaseModel):
    user_id: int
    target_amount: float = 0
    target_type: str = "monthly"
    period: str | None = None
    target_orders: int | None = None
    period_start: str | None = None
    period_end: str | None = None
    actual_amount: float = 0
    status: str = "active"


class SalesTargetUpdate(BaseModel):
    user_id: int | None = None
    target_amount: float | None = None
    target_type: str | None = None
    period: str | None = None
    target_orders: int | None = None
    period_start: str | None = None
    period_end: str | None = None
    actual_amount: float | None = None
    status: str | None = None


# --- Contract ---

class ContractCreate(BaseModel):
    contract_no: str | None = None
    customer_id: int
    sales_order_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    amount: float = 0
    signed_date: str | None = None
    expire_date: str | None = None
    status: str = "draft"
    file_url: str | None = None
    notes: str | None = None


class ContractUpdate(BaseModel):
    contract_no: str | None = None
    customer_id: int | None = None
    sales_order_id: int | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    amount: float | None = None
    signed_date: str | None = None
    expire_date: str | None = None
    status: str | None = None
    file_url: str | None = None
    notes: str | None = None


# --- Notification ---

class MarkReadRequest(BaseModel):
    ids: list[int] | None = None
    all: bool = False


# ============================================================
# Response Schemas
# ============================================================

class PaymentRecordResponse(BaseModel):
    id: int
    sales_order_id: int
    customer_id: int
    amount: float
    payment_date: str | None = None
    payment_method: str
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    id: int
    invoice_no: str | None = None
    sales_order_id: int
    customer_id: int
    amount: float
    tax_amount: float
    invoice_date: str | None = None
    invoice_type: str
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class SalesTargetResponse(BaseModel):
    id: int
    user_id: int
    target_amount: float
    target_type: str
    period: str | None = None
    target_orders: int | None = None
    period_start: str | None = None
    period_end: str | None = None
    actual_amount: float
    status: str
    created_at: datetime
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class ContractResponse(BaseModel):
    id: int
    contract_no: str | None = None
    customer_id: int
    sales_order_id: int | None = None
    title: str
    amount: float
    signed_date: str | None = None
    expire_date: str | None = None
    status: str
    file_url: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class PaymentStats(BaseModel):
    total_received: float = 0
    total_pending: float = 0
    total_overdue: float = 0
    by_method: dict[str, float] = {}
    monthly: list[dict] = []
