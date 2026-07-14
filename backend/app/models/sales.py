import datetime

from sqlalchemy import DECIMAL, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    amount: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    win_probability: Mapped[int | None] = mapped_column(nullable=True)
    expected_close_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- AI 分析结果（由背景 AI 自动填充） ---
    ai_risk_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # low/medium/high
    ai_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_key_concerns: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON list
    ai_scored_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer = relationship("Customer", back_populates="opportunities")
    product = relationship("Product", foreign_keys=[product_id])
    quotations = relationship(
        "Quotation", back_populates="opportunity", lazy="selectin"
    )


class Quotation(TimestampMixin, Base):
    __tablename__ = "quotations"

    quotation_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunities.id"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    status: Mapped[str] = mapped_column(String(20), default="draft")

    # ── 商务条款 ──
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    incoterms: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # FOB / CIF / EXW
    payment_terms: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Net 30 / T/T in advance

    # ── 折扣 ──
    discount_rate: Mapped[float | None] = mapped_column(
        DECIMAL(5, 2), nullable=True
    )  # 折扣率 %
    discount_amount: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    subtotal: Mapped[float | None] = mapped_column(
        DECIMAL(20, 6), nullable=True
    )  # 税前折前合计

    valid_until: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", back_populates="quotations")
    opportunity = relationship("Opportunity", back_populates="quotations")
    items = relationship(
        "QuotationItem",
        primaryjoin="and_(Quotation.id == QuotationItem.quotation_id, QuotationItem.deleted_at.is_(None))",
        back_populates="quotation",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class QuotationItem(TimestampMixin, Base):
    __tablename__ = "quotation_items"

    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"))
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    total_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tax_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    discount_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    cost_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    untaxed_cost: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    taxed_cost: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    sales_profit: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    datecode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lead_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    quotation = relationship("Quotation", back_populates="items")
    product = relationship("Product", back_populates="quotation_items")


class SalesOrder(TimestampMixin, Base):
    __tablename__ = "sales_orders"

    order_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    quotation_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotations.id"), nullable=True
    )
    total_amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # ── 商务条款 ──
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    incoterms: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    customer_po_no: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── 地址 ──
    shipping_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    billing_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 折扣 ──
    discount_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    discount_amount: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    subtotal: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)

    order_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivery_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", back_populates="sales_orders")
    quotation = relationship("Quotation", foreign_keys=[quotation_id])
    items = relationship(
        "SalesOrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class SalesOrderItem(TimestampMixin, Base):
    __tablename__ = "sales_order_items"

    order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tax_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    discount_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    unit_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    total_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    # COGS — actual cost consumed from inventory batches at delivery time
    cost_amount: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product", back_populates="sales_order_items")


class DeliveryNote(TimestampMixin, Base):
    __tablename__ = "delivery_notes"

    delivery_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # ── 物流 ──
    shipping_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    incoterms: Mapped[str | None] = mapped_column(String(20), nullable=True)

    delivery_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", back_populates="delivery_notes")
    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id])
    items = relationship(
        "DeliveryNoteItem",
        back_populates="delivery_note",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class DeliveryNoteItem(TimestampMixin, Base):
    __tablename__ = "delivery_note_items"

    delivery_note_id: Mapped[int] = mapped_column(ForeignKey("delivery_notes.id"))
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    delivery_note = relationship("DeliveryNote", back_populates="items")
    product = relationship("Product", back_populates="delivery_note_items")


class ReturnNote(TimestampMixin, Base):
    """Sales return — refund flow from a delivered DeliveryNote.

    Lifecycle: pending → approved → completed | rejected.
    On completion: inventory restock + optional credit note.
    """

    __tablename__ = "return_notes"

    return_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_note_id: Mapped[int] = mapped_column(ForeignKey("delivery_notes.id"))
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    total_amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    delivery_note = relationship("DeliveryNote", foreign_keys=[delivery_note_id])
    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id])
    customer = relationship("Customer", foreign_keys=[customer_id])
    items = relationship(
        "ReturnNoteItem",
        back_populates="return_note",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ReturnNoteItem(TimestampMixin, Base):
    """Single line in a return note."""

    __tablename__ = "return_note_items"

    return_note_id: Mapped[int] = mapped_column(ForeignKey("return_notes.id"))
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    total_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    return_note = relationship("ReturnNote", back_populates="items")
    product = relationship("Product", foreign_keys=[product_id])


class Inquiry(TimestampMixin, Base):
    """Incoming customer inquiry — underived leads that may convert to opportunities."""

    __tablename__ = "inquiries"

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
    channel: Mapped[str] = mapped_column(
        String(20), default="web"
    )  # web, wechat, email, api
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_info: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # email/phone
    inquiry_text: Mapped[str] = mapped_column(Text)
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, replied, converted
    matched_products: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON list of {id, name, brand}
    ai_confidence: Mapped[float | None] = mapped_column(nullable=True)  # 0.0-1.0

    customer = relationship("Customer", backref="inquiries")
