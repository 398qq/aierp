import datetime

from sqlalchemy import DECIMAL, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    amount: Mapped[float | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    win_probability: Mapped[int | None] = mapped_column(nullable=True)
    expected_close_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product = relationship("Product", foreign_keys=[product_id])
    quotations = relationship("Quotation", back_populates="opportunity", lazy="selectin")


class Quotation(TimestampMixin, Base):
    __tablename__ = "quotations"

    quotation_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    valid_until: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    opportunity = relationship("Opportunity", back_populates="quotations")
    items = relationship("QuotationItem", back_populates="quotation", lazy="selectin", cascade="all, delete-orphan")


class QuotationItem(TimestampMixin, Base):
    __tablename__ = "quotation_items"

    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    total_price: Mapped[float | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    quotation = relationship("Quotation", back_populates="items")
    product = relationship("Product", foreign_keys=[product_id])


class SalesOrder(TimestampMixin, Base):
    __tablename__ = "sales_orders"

    order_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"), nullable=True)
    total_amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    order_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items = relationship("SalesOrderItem", back_populates="order", lazy="selectin", cascade="all, delete-orphan")


class SalesOrderItem(TimestampMixin, Base):
    __tablename__ = "sales_order_items"

    order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    total_price: Mapped[float | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product", foreign_keys=[product_id])


class DeliveryNote(TimestampMixin, Base):
    __tablename__ = "delivery_notes"

    delivery_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    delivery_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items = relationship("DeliveryNoteItem", back_populates="delivery_note", lazy="selectin", cascade="all, delete-orphan")


class DeliveryNoteItem(TimestampMixin, Base):
    __tablename__ = "delivery_note_items"

    delivery_note_id: Mapped[int] = mapped_column(ForeignKey("delivery_notes.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    delivery_note = relationship("DeliveryNote", back_populates="items")
    product = relationship("Product", foreign_keys=[product_id])


