"""Sales schemas — Pydantic v2 models for opportunities, quotations, orders, delivery notes."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

OpportunityStatus = Literal["active", "won", "lost"]
QuotationStatus = Literal[
    "draft", "sent", "accepted", "rejected", "expired", "lost", "won"
]
SalesOrderStatus = Literal[
    "pending",
    "draft",
    "confirmed",
    "partially_shipped",
    "shipped",
    "delivered",
    "invoiced",
    "completed",
    "cancelled",
]
DeliveryStatus = Literal["pending", "shipped", "delivered", "cancelled"]


# ============================================================
# Opportunity
# ============================================================


class OpportunityCreate(BaseModel):
    customer_id: int
    product_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: Literal["active"] = "active"
    stage: str | None = None
    amount: float | None = None
    win_probability: int | None = None
    expected_close_date: datetime | None = None
    assigned_to: str | None = None
    source: str | None = None
    notes: str | None = None


class OpportunityUpdate(BaseModel):
    customer_id: int | None = None
    product_id: int | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: OpportunityStatus | None = None
    stage: str | None = None
    amount: float | None = None
    win_probability: int | None = None
    expected_close_date: datetime | None = None
    assigned_to: str | None = None
    source: str | None = None
    notes: str | None = None


class OpportunityResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    customer_id: int
    customer_name: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    title: str
    description: str | None = None
    status: str
    stage: str | None = None
    amount: float | None = None
    win_probability: int | None = None
    expected_close_date: datetime | None = None
    assigned_to: str | None = None
    source: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    ai: "OpportunityAI | None" = None
    model_config = {"from_attributes": True}


# ============================================================
# Quotation
# ============================================================


class QuotationItemCreate(BaseModel):
    product_id: int | None = None
    product_name: str | None = None
    customer_part_no: str | None = Field(None, max_length=150)
    customer_product_name: str | None = Field(None, max_length=255)
    quantity: int = 1
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    tax_rate: float | None = None
    discount_rate: float | None = None
    cost_price: float | None = None
    untaxed_cost: float | None = None
    taxed_cost: float | None = None
    sales_profit: float | None = None
    datecode: str | None = Field(None, max_length=100)
    lead_time: str | None = Field(None, max_length=100)
    notes: str | None = None


class QuotationItemUpdate(BaseModel):
    product_id: int | None = None
    product_name: str | None = None
    customer_part_no: str | None = Field(None, max_length=150)
    customer_product_name: str | None = Field(None, max_length=255)
    quantity: int | None = None
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    tax_rate: float | None = None
    discount_rate: float | None = None
    cost_price: float | None = None
    untaxed_cost: float | None = None
    taxed_cost: float | None = None
    sales_profit: float | None = None
    datecode: str | None = Field(None, max_length=100)
    lead_time: str | None = Field(None, max_length=100)
    notes: str | None = None


class QuotationItemResponse(BaseModel):
    id: int
    quotation_id: int
    product_id: int | None = None
    product_name: str | None = None
    customer_part_no: str | None = None
    customer_product_name: str | None = None
    quantity: int
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    tax_rate: float | None = None
    discount_rate: float | None = None
    cost_price: float | None = None
    untaxed_cost: float | None = None
    taxed_cost: float | None = None
    sales_profit: float | None = None
    datecode: str | None = None
    lead_time: str | None = None
    notes: str | None = None
    model_config = {"from_attributes": True}


class QuotationCreate(BaseModel):
    quotation_no: str | None = None
    customer_id: int
    opportunity_id: int | None = None
    title: str | None = None
    total_amount: float = 0
    status: QuotationStatus = "draft"
    currency: str = "CNY"
    incoterms: str | None = None
    payment_terms: str | None = None
    discount_rate: float | None = None
    discount_amount: float | None = None
    subtotal: float | None = None
    valid_until: datetime | None = None
    notes: str | None = None
    items: list[QuotationItemCreate] = []


class QuotationUpdate(BaseModel):
    quotation_no: str | None = None
    customer_id: int | None = None
    opportunity_id: int | None = None
    title: str | None = None
    total_amount: float | None = None
    status: QuotationStatus | None = None
    currency: str | None = None
    incoterms: str | None = None
    payment_terms: str | None = None
    discount_rate: float | None = None
    discount_amount: float | None = None
    subtotal: float | None = None
    valid_until: datetime | None = None
    notes: str | None = None
    items: list[QuotationItemCreate] | None = None


class QuotationStatusUpdate(BaseModel):
    status: QuotationStatus


class QuotationFromInquiryRequest(BaseModel):
    inquiry_id: int
    customer_id: int | None = None
    title: str | None = None
    valid_until: datetime | None = None
    notes: str | None = None
    items: list[dict] = []  # [{product_id, product_name, quantity, unit_price}]


class QuotationResponse(BaseModel):
    id: int
    quotation_no: str | None = None
    customer_id: int
    customer_name: str | None = None
    opportunity_id: int | None = None
    opportunity_title: str | None = None
    title: str | None = None
    total_amount: float
    status: str
    currency: str = "CNY"
    incoterms: str | None = None
    payment_terms: str | None = None
    discount_rate: float | None = None
    discount_amount: float | None = None
    subtotal: float | None = None
    valid_until: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    items: list[QuotationItemResponse] = []
    ai: "QuotationAI | None" = None
    model_config = {"from_attributes": True}


# ============================================================
# Sales Order
# ============================================================


class SalesOrderItemCreate(BaseModel):
    product_id: int | None = None
    product_name: str | None = None
    customer_part_no: str | None = Field(None, max_length=150)
    customer_product_name: str | None = Field(None, max_length=255)
    quantity: int = 1
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    tax_rate: float | None = None
    discount_rate: float | None = None
    notes: str | None = None


class SalesOrderItemUpdate(BaseModel):
    product_id: int | None = None
    product_name: str | None = None
    customer_part_no: str | None = Field(None, max_length=150)
    customer_product_name: str | None = Field(None, max_length=255)
    quantity: int | None = None
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    tax_rate: float | None = None
    discount_rate: float | None = None
    notes: str | None = None


class SalesOrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: int | None = None
    product_name: str | None = None
    customer_part_no: str | None = None
    customer_product_name: str | None = None
    quantity: int
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    tax_rate: float | None = None
    discount_rate: float | None = None
    notes: str | None = None
    model_config = {"from_attributes": True}


class SalesOrderCreate(BaseModel):
    order_no: str | None = None
    customer_id: int
    quotation_id: int | None = None
    total_amount: float = 0
    status: Literal["pending"] = "pending"
    currency: str = "CNY"
    incoterms: str | None = None
    payment_terms: str | None = None
    due_date: datetime | None = None
    customer_po_no: str | None = None
    shipping_address: str | None = None
    billing_address: str | None = None
    discount_rate: float | None = None
    discount_amount: float | None = None
    subtotal: float | None = None
    order_date: datetime | None = None
    delivery_date: datetime | None = None
    notes: str | None = None
    items: list[SalesOrderItemCreate] = []


class SalesOrderUpdate(BaseModel):
    order_no: str | None = None
    customer_id: int | None = None
    quotation_id: int | None = None
    total_amount: float | None = None
    status: SalesOrderStatus | None = None
    currency: str | None = None
    incoterms: str | None = None
    payment_terms: str | None = None
    due_date: datetime | None = None
    customer_po_no: str | None = None
    shipping_address: str | None = None
    billing_address: str | None = None
    discount_rate: float | None = None
    discount_amount: float | None = None
    subtotal: float | None = None
    order_date: datetime | None = None
    delivery_date: datetime | None = None
    notes: str | None = None
    items: list[SalesOrderItemCreate] | None = None


class SalesOrderResponse(BaseModel):
    id: int
    order_no: str | None = None
    customer_id: int
    customer_name: str | None = None
    quotation_id: int | None = None
    quotation_no: str | None = None
    total_amount: float
    status: str
    currency: str = "CNY"
    incoterms: str | None = None
    payment_terms: str | None = None
    due_date: datetime | None = None
    customer_po_no: str | None = None
    shipping_address: str | None = None
    billing_address: str | None = None
    discount_rate: float | None = None
    discount_amount: float | None = None
    subtotal: float | None = None
    order_date: datetime | None = None
    delivery_date: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    items: list[SalesOrderItemResponse] = []
    ai: "SalesOrderAI | None" = None
    model_config = {"from_attributes": True}


# ============================================================
# Delivery Note
# ============================================================


class DeliveryNoteItemCreate(BaseModel):
    product_id: int | None = None
    product_name: str | None = None
    customer_part_no: str | None = Field(None, max_length=150)
    customer_product_name: str | None = Field(None, max_length=255)
    quantity: int = 1
    unit: str | None = None
    notes: str | None = None


class DeliveryNoteItemUpdate(BaseModel):
    product_id: int | None = None
    product_name: str | None = None
    customer_part_no: str | None = Field(None, max_length=150)
    customer_product_name: str | None = Field(None, max_length=255)
    quantity: int | None = None
    unit: str | None = None
    notes: str | None = None


class DeliveryNoteItemResponse(BaseModel):
    id: int
    delivery_note_id: int
    product_id: int | None = None
    product_name: str | None = None
    customer_part_no: str | None = None
    customer_product_name: str | None = None
    quantity: int
    unit: str | None = None
    notes: str | None = None
    model_config = {"from_attributes": True}


class DeliveryNoteCreate(BaseModel):
    delivery_no: str | None = None
    sales_order_id: int
    customer_id: int
    status: Literal["pending"] = "pending"
    shipping_method: str | None = None
    tracking_number: str | None = None
    incoterms: str | None = None
    delivery_date: datetime | None = None
    received_date: datetime | None = None
    notes: str | None = None
    items: list[DeliveryNoteItemCreate] = []


class DeliveryNoteUpdate(BaseModel):
    delivery_no: str | None = None
    sales_order_id: int | None = None
    customer_id: int | None = None
    status: DeliveryStatus | None = None
    shipping_method: str | None = None
    tracking_number: str | None = None
    incoterms: str | None = None
    delivery_date: datetime | None = None
    received_date: datetime | None = None
    notes: str | None = None


class DeliveryNoteMarkPaidIn(BaseModel):
    amount: float | None = None
    payment_method: str = "bank"
    payment_date: datetime | None = None
    notes: str | None = None


class DeliveryNoteResponse(BaseModel):
    id: int
    delivery_no: str | None = None
    sales_order_id: int
    sales_order_no: str | None = None
    customer_id: int
    customer_name: str | None = None
    status: str
    shipping_method: str | None = None
    tracking_number: str | None = None
    incoterms: str | None = None
    delivery_date: datetime | None = None
    received_date: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    items: list[DeliveryNoteItemResponse] = []
    ai: "DeliveryNoteAI | None" = None
    model_config = {"from_attributes": True}


# ============================================================
# AI Insight Types (returned when include_ai=true)
# ============================================================


class OpportunityAI(BaseModel):
    risk_level: str = "low"  # low / medium / high
    win_probability: int = 50
    next_best_action: str | None = None
    key_concerns: list[str] = []


class QuotationAI(BaseModel):
    pricing_health: str = "fair"  # good / fair / poor
    win_probability: int = 50
    margin_assessment: str | None = None
    improvement_suggestions: list[str] = []


class SalesOrderAI(BaseModel):
    delivery_risk: str = "low"  # low / medium / high
    payment_risk: str = "low"
    health_score: int = 80
    flags: list[str] = []


class DeliveryNoteAI(BaseModel):
    completion_risk: str = "low"  # low / medium / high
    signing_delay_probability: int = 10
    issues: list[str] = []


# ============================================================
# List AI insight map {entity_id: insight}
# ============================================================


class ListAIInsights(BaseModel):
    opportunities: dict[int, OpportunityAI] = {}
    quotations: dict[int, QuotationAI] = {}
    sales_orders: dict[int, SalesOrderAI] = {}
    delivery_notes: dict[int, DeliveryNoteAI] = {}


# ============================================================
# Batch Operations
# ============================================================


class BatchDeleteRequest(BaseModel):
    ids: list[int]


class OpportunityBatchUpdate(BaseModel):
    ids: list[int]
    stage: str | None = None
    win_probability: int | None = None


# ============================================================
# Flow Conversion
# ============================================================


class ConversionValidation(BaseModel):
    risk_level: str = "low"
    warnings: list[str] = []
    recommendations: list[str] = []


class ConvertResponse(BaseModel):
    id: int
    document_no: str
    msg: str
    ai_validation: ConversionValidation | None = None


# ============================================================
# Sales Targets
# ============================================================


class TargetCreate(BaseModel):
    user_id: int
    period: str | None = None
    target_amount: float | None = None
    target_orders: int | None = None
    target_type: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    actual_amount: float | None = None
    status: str | None = None


class TargetUpdate(BaseModel):
    user_id: int | None = None
    period: str | None = None
    target_amount: float | None = None
    target_orders: int | None = None
    target_type: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    actual_amount: float | None = None
    status: str | None = None


# ============================================================
# Inquiry / Auto-Reply
# ============================================================


class InquiryAutoReplyRequest(BaseModel):
    """Request body for AI-powered inquiry auto-reply."""

    inquiry_text: str = Field(
        min_length=1,
        max_length=5000,
        description="客户询价原文，支持型号/品牌/数量描述",
    )
    customer_id: int | None = Field(None, description="客户ID（已知客户）")
    contact_name: str | None = Field(None, max_length=100)
    contact_info: str | None = Field(None, max_length=255, description="邮箱或电话")
    channel: str = Field(default="web", description="来源渠道: web/wechat/email/api")


class MatchedProductItem(BaseModel):
    id: int
    sku: str | None
    name: str
    brand_name: str | None
    stock_qty: int | None = 0
    stock_status: str  # in_stock / low_stock / out_of_stock
    suggested_price: float | None = None


class InquiryAutoReplyResponse(BaseModel):
    """Response from AI-powered inquiry auto-reply."""

    inquiry_id: int
    reply_text: str
    confidence: float | None
    matched_products: list[MatchedProductItem]
    created_opportunity_id: int | None = None  # auto-created if high confidence
    summary: str  # 1-line summary for CRM
