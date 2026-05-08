import datetime

from sqlalchemy import DECIMAL, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class PaymentRecord(TimestampMixin, Base):
    __tablename__ = "payment_records"

    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    amount: Mapped[float] = mapped_column(DECIMAL(15, 2))
    payment_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(30), default="bank")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"

    invoice_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    amount: Mapped[float] = mapped_column(DECIMAL(15, 2))
    tax_amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    invoice_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invoice_type: Mapped[str] = mapped_column(String(20), default="普通发票")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SalesTarget(TimestampMixin, Base):
    __tablename__ = "sales_targets"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    target_type: Mapped[str] = mapped_column(String(20), default="monthly")
    period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_orders: Mapped[int | None] = mapped_column(nullable=True)
    period_start: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")


class Contract(TimestampMixin, Base):
    __tablename__ = "contracts"

    contract_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    signed_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expire_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(30), default="followup")
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_id: Mapped[int | None] = mapped_column(nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
