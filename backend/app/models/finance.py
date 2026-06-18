import datetime

from sqlalchemy import (
    DECIMAL,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class PaymentRecord(TimestampMixin, Base):
    __tablename__ = "payment_records"

    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    delivery_note_id: Mapped[int | None] = mapped_column(
        ForeignKey("delivery_notes.id"), nullable=True
    )
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id"), nullable=True
    )
    amount: Mapped[float] = mapped_column(DECIMAL(20, 6))
    payment_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payment_method: Mapped[str] = mapped_column(String(30), default="bank")
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    transaction_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id])
    customer = relationship("Customer", foreign_keys=[customer_id])
    delivery_note = relationship("DeliveryNote", foreign_keys=[delivery_note_id])
    invoice = relationship("Invoice", foreign_keys=[invoice_id])


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"

    invoice_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    amount: Mapped[float] = mapped_column(DECIMAL(20, 6))
    tax_amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    invoice_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invoice_type: Mapped[str] = mapped_column(String(20), default="普通发票")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    due_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subtotal: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id])
    customer = relationship("Customer", foreign_keys=[customer_id])
    lines = relationship(
        "InvoiceLine",
        back_populates="invoice",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class SalesTarget(TimestampMixin, Base):
    __tablename__ = "sales_targets"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    target_type: Mapped[str] = mapped_column(String(20), default="monthly")
    period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_orders: Mapped[int | None] = mapped_column(nullable=True)
    commission_rate: Mapped[float] = mapped_column(
        DECIMAL(8, 4),
        default=0.05,
        server_default="0.05",
        comment="Per-user commission rate (e.g. 0.05 = 5%)",
    )
    period_start: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    period_end: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")

    user = relationship("User", foreign_keys=[user_id])


class Contract(TimestampMixin, Base):
    __tablename__ = "contracts"

    contract_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    sales_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    signed_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expire_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="draft")
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", foreign_keys=[customer_id])
    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id])


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(30), default="followup")
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_id: Mapped[int | None] = mapped_column(nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    channel: Mapped[str] = mapped_column(String(30), default="in_app")
    template_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class Commission(TimestampMixin, Base):
    """Sales commission record — payable to a sales rep on a sales order.

    Status machine:
        draft → pending_approval → approved → paid
                                  ↘ rejected → (terminal)
                                  ↘ cancelled → (terminal)

    Since 013 scheme engine: ``commission_scheme_id`` + ``scheme_snapshot``
    record which scheme was used and what the configuration was at calculation
    time, so future scheme changes don't retroactively alter paid commissions.
    """

    __tablename__ = "commissions"

    commission_no: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    sales_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )

    base_amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    rate: Mapped[float] = mapped_column(DECIMAL(8, 4), default=0)
    commission_amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    paid_amount: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)

    status: Mapped[str] = mapped_column(String(20), default="draft")
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 013 scheme integration
    commission_scheme_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("commission_schemes.id"), nullable=True, default=None
    )
    scheme_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=None
    )

    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id])
    sales_user = relationship("User", foreign_keys=[sales_user_id])
    customer = relationship("Customer", foreign_keys=[customer_id])
    approver = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'paid', 'rejected', 'cancelled')",
            name="ck_commission_status",
        ),
        CheckConstraint(
            "rate >= 0 AND rate <= 1",
            name="ck_commission_rate_range",
        ),
    )


class InvoiceLine(TimestampMixin, Base):
    """Single line in an invoice — mirrors a SalesOrderItem."""

    __tablename__ = "invoice_lines"

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unit_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    total_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    tax_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    tax_amount: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice = relationship("Invoice", back_populates="lines")
    product = relationship("Product", foreign_keys=[product_id])
