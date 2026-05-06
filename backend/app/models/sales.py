import datetime

from sqlalchemy import DECIMAL, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    name: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    stage: Mapped[str] = mapped_column(String(30), default="lead")
    probability: Mapped[int] = mapped_column(default=10)
    expected_close_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_close_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Quotation(TimestampMixin, Base):
    __tablename__ = "quotations"

    quotation_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    total_amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    valid_until: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class QuotationItem(TimestampMixin, Base):
    __tablename__ = "quotation_items"

    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float] = mapped_column(DECIMAL(12, 4), default=0)
    amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)


class SalesOrder(TimestampMixin, Base):
    __tablename__ = "sales_orders"

    order_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total_amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    delivery_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SalesOrderItem(TimestampMixin, Base):
    __tablename__ = "sales_order_items"

    order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float] = mapped_column(DECIMAL(12, 4), default=0)
    amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)


class DeliveryNote(TimestampMixin, Base):
    __tablename__ = "delivery_notes"

    note_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    delivery_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DeliveryNoteItem(TimestampMixin, Base):
    __tablename__ = "delivery_note_items"

    delivery_note_id: Mapped[int] = mapped_column(ForeignKey("delivery_notes.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(default=1)
