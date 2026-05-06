import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

# Many-to-many: customer <-> tag
customer_tag_table = Table(
    "customer_tag_links",
    Base.metadata,
    Column("customer_id", Integer, ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("customer_tags.id", ondelete="CASCADE"), primary_key=True),
)


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    credit_limit: Mapped[float | None] = mapped_column(nullable=True)
    credit_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_contacted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)

    contacts = relationship("CustomerContact", back_populates="customer", lazy="selectin")
    follow_ups = relationship("CustomerFollowUp", back_populates="customer", lazy="selectin")
    tags = relationship("CustomerTag", secondary=customer_tag_table, lazy="selectin")


class CustomerContact(TimestampMixin, Base):
    __tablename__ = "customer_contacts"

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    name: Mapped[str] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wechat: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_primary: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", back_populates="contacts")


class CustomerFollowUp(TimestampMixin, Base):
    __tablename__ = "customer_follow_ups"

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)

    customer = relationship("Customer", back_populates="follow_ups")


class CustomerTag(TimestampMixin, Base):
    __tablename__ = "customer_tags"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)


class CustomerAttachment(TimestampMixin, Base):
    __tablename__ = "customer_attachments"

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    original_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(default=0)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)


class CustomerLog(TimestampMixin, Base):
    __tablename__ = "customer_logs"

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(30))  # create, update, delete, merge, tag, import
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
