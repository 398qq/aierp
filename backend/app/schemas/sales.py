"""Sales schemas — Pydantic v2 models for opportunities, quotations, orders, delivery notes."""

from datetime import datetime

from pydantic import BaseModel, Field


# --- Opportunity ---

class OpportunityCreate(BaseModel):
    customer_id: int
    name: str = Field(min_length=1, max_length=255)
    amount: float = 0
    stage: str = "lead"
    probability: int = 10
    expected_close_date: str | None = None
    actual_close_date: str | None = None
    notes: str | None = None


class OpportunityUpdate(BaseModel):
    customer_id: int | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    amount: float | None = None
    stage: str | None = None
    probability: int | None = None
    expected_close_date: str | None = None
    actual_close_date: str | None = None
    notes: str | None = None


class OpportunityResponse(BaseModel):
    id: int
    customer_id: int
    name: str
    amount: float
    stage: str
    probability: int
    expected_close_date: str | None
    actual_close_date: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime | None
    model_config = {"from_attributes": True}


# --- Quotation ---

class QuotationCreate(BaseModel):
    quotation_no: str | None = None
    customer_id: int
    status: str = "draft"
    total_amount: float = 0
    valid_until: str | None = None
    notes: str | None = None


class QuotationUpdate(BaseModel):
    quotation_no: str | None = None
    customer_id: int | None = None
    status: str | None = None
    total_amount: float | None = None
    valid_until: str | None = None
    notes: str | None = None


class QuotationResponse(BaseModel):
    id: int
    quotation_no: str | None
    customer_id: int
    status: str
    total_amount: float
    valid_until: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime | None
    items: list["QuotationItemResponse"] = []
    model_config = {"from_attributes": True}


class QuotationItemCreate(BaseModel):
    product_id: int
    quantity: int = 1
    unit_price: float = 0
    amount: float = 0


class QuotationItemUpdate(BaseModel):
    product_id: int | None = None
    quantity: int | None = None
    unit_price: float | None = None
    amount: float | None = None


class QuotationItemResponse(BaseModel):
    id: int
    quotation_id: int
    product_id: int
    quantity: int
    unit_price: float
    amount: float
    model_config = {"from_attributes": True}


# --- Sales Order ---

class SalesOrderCreate(BaseModel):
    order_no: str | None = None
    customer_id: int
    status: str = "pending"
    total_amount: float = 0
    delivery_date: str | None = None
    notes: str | None = None


class SalesOrderUpdate(BaseModel):
    order_no: str | None = None
    customer_id: int | None = None
    status: str | None = None
    total_amount: float | None = None
    delivery_date: str | None = None
    notes: str | None = None


class SalesOrderResponse(BaseModel):
    id: int
    order_no: str | None
    customer_id: int
    status: str
    total_amount: float
    delivery_date: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime | None
    items: list["SalesOrderItemResponse"] = []
    model_config = {"from_attributes": True}


class SalesOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = 1
    unit_price: float = 0
    amount: float = 0


class SalesOrderItemUpdate(BaseModel):
    product_id: int | None = None
    quantity: int | None = None
    unit_price: float | None = None
    amount: float | None = None


class SalesOrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: int
    quantity: int
    unit_price: float
    amount: float
    model_config = {"from_attributes": True}


# --- Delivery Note ---

class DeliveryNoteCreate(BaseModel):
    note_no: str | None = None
    sales_order_id: int
    customer_id: int
    status: str = "pending"
    delivery_date: str | None = None
    signed_at: str | None = None
    notes: str | None = None


class DeliveryNoteUpdate(BaseModel):
    note_no: str | None = None
    sales_order_id: int | None = None
    customer_id: int | None = None
    status: str | None = None
    delivery_date: str | None = None
    signed_at: str | None = None
    notes: str | None = None


class DeliveryNoteResponse(BaseModel):
    id: int
    note_no: str | None
    sales_order_id: int
    customer_id: int
    status: str
    delivery_date: str | None
    signed_at: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime | None
    items: list["DeliveryNoteItemResponse"] = []
    model_config = {"from_attributes": True}


class DeliveryNoteItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class DeliveryNoteItemUpdate(BaseModel):
    product_id: int | None = None
    quantity: int | None = None


class DeliveryNoteItemResponse(BaseModel):
    id: int
    delivery_note_id: int
    product_id: int
    quantity: int
    model_config = {"from_attributes": True}


# --- Sales Funnel ---

class FunnelStage(BaseModel):
    stage: str
    count: int
    amount: float


# --- Sales Stats ---

class SalesSummary(BaseModel):
    total_orders: int
    total_amount: float
    avg_amount: float
    active_opportunities: int


class TrendPoint(BaseModel):
    period: str
    order_count: int
    total_amount: float


class StageDistribution(BaseModel):
    stage: str
    count: int
    percentage: float


# --- Batch Operations ---

class BatchDeleteRequest(BaseModel):
    ids: list[int]


class OpportunityBatchUpdate(BaseModel):
    ids: list[int]
    stage: str | None = None
    probability: int | None = None


# --- Flow Conversion ---

class ConvertResponse(BaseModel):
    id: int
    document_no: str
    msg: str


# --- Document Numbering ---

class DocumentNumberResponse(BaseModel):
    document_no: str
