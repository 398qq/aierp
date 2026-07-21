"""Finance schemas — Pydantic v2 models for payments, invoices, targets, contracts, notifications."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PaymentStatus = Literal["pending", "partial", "completed", "overdue", "reversed"]
InvoiceStatus = Literal["draft", "issued", "overdue", "paid", "cancelled"]


# --- PaymentRecord ---


class PaymentRecordCreate(BaseModel):
    sales_order_id: int | None = None
    customer_id: int
    delivery_note_id: int | None = None
    invoice_id: int | None = None
    amount: float
    payment_date: str | None = None
    payment_method: str = "bank"
    status: Literal["pending"] = "pending"
    currency: str = "CNY"
    transaction_ref: str | None = None
    bank_account: str | None = None
    notes: str | None = None


class PaymentRecordUpdate(BaseModel):
    sales_order_id: int | None = None
    customer_id: int | None = None
    delivery_note_id: int | None = None
    invoice_id: int | None = None
    amount: float | None = None
    payment_date: str | None = None
    payment_method: str | None = None
    status: PaymentStatus | None = None
    currency: str | None = None
    transaction_ref: str | None = None
    bank_account: str | None = None
    notes: str | None = None


class PaymentAllocationItem(BaseModel):
    invoice_id: int
    amount: float = Field(gt=0)


class PaymentAllocationRequest(BaseModel):
    allocations: list[PaymentAllocationItem] = Field(min_length=1)


# --- Invoice ---


class InvoiceCreate(BaseModel):
    invoice_no: str | None = None
    sales_order_id: int
    delivery_note_id: int | None = None
    customer_id: int
    amount: float
    tax_amount: float | None = None
    invoice_date: str | None = None
    invoice_type: str = "普通发票"
    status: Literal["draft"] = "draft"
    currency: str = "CNY"
    due_date: str | None = None
    subtotal: float | None = None
    notes: str | None = None


class InvoiceUpdate(BaseModel):
    invoice_no: str | None = None
    sales_order_id: int | None = None
    delivery_note_id: int | None = None
    customer_id: int | None = None
    amount: float | None = None
    tax_amount: float | None = None
    invoice_date: str | None = None
    invoice_type: str | None = None
    status: InvoiceStatus | None = None
    currency: str | None = None
    due_date: str | None = None
    subtotal: float | None = None
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
    amount: float = Field(default=0, ge=0)
    currency: str = Field(default="CNY", min_length=3, max_length=3)
    signed_date: str | None = None
    expire_date: str | None = None
    status: Literal["draft", "signed"] = "draft"
    file_url: str | None = None
    delivery_address: str | None = None
    delivery_terms: str | None = None
    payment_terms: str | None = None
    acceptance_terms: str | None = None
    warranty_terms: str | None = None
    dispute_terms: str | None = None
    invoice_type: str | None = None
    notes: str | None = None


class ContractUpdate(BaseModel):
    contract_no: str | None = None
    customer_id: int | None = None
    sales_order_id: int | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    signed_date: str | None = None
    expire_date: str | None = None
    status: (
        Literal["draft", "signed", "active", "expired", "terminated", "cancelled"]
        | None
    ) = None
    file_url: str | None = None
    delivery_address: str | None = None
    delivery_terms: str | None = None
    payment_terms: str | None = None
    acceptance_terms: str | None = None
    warranty_terms: str | None = None
    dispute_terms: str | None = None
    invoice_type: str | None = None
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
    sales_order_id: int | None = None
    sales_order_no: str | None = None
    customer_id: int
    delivery_note_id: int | None = None
    delivery_note_no: str | None = None
    invoice_id: int | None = None
    invoice_no: str | None = None
    amount: float
    payment_date: str | None = None
    payment_method: str
    status: str
    currency: str = "CNY"
    transaction_ref: str | None = None
    bank_account: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    id: int
    invoice_no: str | None = None
    sales_order_id: int
    delivery_note_id: int | None = None
    sales_order_no: str | None = None
    customer_id: int
    customer_name: str | None = None
    amount: float
    tax_amount: float
    currency: str = "CNY"
    due_date: str | None = None
    subtotal: float | None = None
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
    currency: str = "CNY"
    signed_date: str | None = None
    expire_date: str | None = None
    status: str
    file_url: str | None = None
    delivery_address: str | None = None
    delivery_terms: str | None = None
    payment_terms: str | None = None
    acceptance_terms: str | None = None
    warranty_terms: str | None = None
    dispute_terms: str | None = None
    invoice_type: str | None = None
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


# --- Commission ---


class CommissionCreate(BaseModel):
    sales_order_id: int
    sales_user_id: int
    base_amount: float = Field(default=0, ge=0)
    rate: float = Field(default=0, ge=0, le=1)
    period: str | None = None
    notes: str | None = None


class CommissionUpdate(BaseModel):
    base_amount: float | None = Field(default=None, ge=0)
    rate: float | None = Field(default=None, ge=0, le=1)
    period: str | None = None
    notes: str | None = None
    status: str | None = None


class CommissionRead(BaseModel):
    id: int
    commission_no: str | None
    sales_order_id: int
    sales_user_id: int
    customer_id: int | None
    base_amount: float
    rate: float
    commission_amount: float
    paid_amount: float
    status: str
    approved_by: int | None
    approved_at: datetime | None
    paid_at: datetime | None
    period: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
