import datetime

from sqlalchemy import DECIMAL, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class PurchaseOrder(TimestampMixin, Base):
    __tablename__ = "purchase_orders"

    order_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    total_amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    expected_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    supplier = relationship("Supplier", foreign_keys=[supplier_id])
    items = relationship("PurchaseOrderItem", back_populates="order", lazy="selectin")


class PurchaseOrderItem(TimestampMixin, Base):
    __tablename__ = "purchase_order_items"

    order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float] = mapped_column(DECIMAL(12, 4), default=0)
    amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)

    order = relationship("PurchaseOrder", back_populates="items", foreign_keys=[order_id])
    product = relationship("Product", foreign_keys=[product_id])


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    payment_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(20), default="receipt")
    amount: Mapped[float] = mapped_column(DECIMAL(15, 2))
    method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    paid_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", foreign_keys=[customer_id])
    supplier = relationship("Supplier", foreign_keys=[supplier_id])


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"

    ticket_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", back_populates="tickets")

class Visit(TimestampMixin, Base):
    __tablename__ = "visits"

    visit_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("customer_contacts.id"), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visit_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    main_product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    key_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    followup_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", back_populates="visits")
    contact = relationship("CustomerContact", foreign_keys=[contact_id])


class Sample(TimestampMixin, Base):
    __tablename__ = "samples"

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    apply_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ship_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    receive_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="requested")
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", back_populates="samples")
    product = relationship("Product", foreign_keys=[product_id])
