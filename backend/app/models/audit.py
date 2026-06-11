"""Audit log models — Stage 2 / Stage 7.

status_transition_log: tracks every state machine transition across
all sales aggregates (sales_order / invoice / payment_record /
delivery_note / quotation / opportunity). One row per transition.

field_change_log (Stage 7): tracks every generic field change
(customer / supplier / product / quotation / order / etc.) —
one row per changed field per update. Captures:
- table_name + record_id (which row)
- field_name (which column)
- old_value / new_value (snapshots)
- actor (who)
- changed_at (when)
- reason (optional)

Used for:
- "为什么这单状态变成 completed 了？"  (audit trail)
- 报表：平均停留时长（PENDING → CONFIRMED 平均几天？）
- 客户行为分析（哪些客户的订单经常被 cancel？）
- "谁改了客户 A 的邮箱？"  (field-level audit)
- 业务行为分析（销售多久会调一次价格？）
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class StatusTransitionLog(TimestampMixin, Base):
    """One row per state machine transition.

    Append-only: never updated, never deleted. The status_after / status_before
    snapshots let us reconstruct the full lifecycle of any aggregate.
    """

    __tablename__ = "status_transition_logs"

    # Which aggregate
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    aggregate_id: Mapped[int] = mapped_column(nullable=False, index=True)
    aggregate_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. order_no, invoice_no

    # State transition
    status_before: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status_after: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # confirm / ship / complete / cancel / pay / issue

    # Who / when / why
    actor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Optional context (links to other aggregates)
    customer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True
    )
    sales_order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_transition_logs_aggregate", "aggregate_type", "aggregate_id"),
        Index("ix_transition_logs_customer_time", "customer_id", "transitioned_at"),
        Index("ix_transition_logs_time", "transitioned_at"),
    )


class FieldChangeLog(TimestampMixin, Base):
    """One row per changed field per update (Stage 7).

    Generic field-level audit: any model with `__tablename__` can be tracked
    by passing `audit_fields=True` to BaseCRUDService.update().

    Example: customer.update({"email": "new@x.com"}, audit_actor="alice")
    → one FieldChangeLog row: table=customer, field=email, old=old@x.com, new=new@x.com, actor=alice
    """

    __tablename__ = "field_change_logs"

    # Which record
    table_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    record_id: Mapped[int] = mapped_column(nullable=False, index=True)

    # What changed
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Who / when / why
    actor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_field_change_logs_record", "table_name", "record_id"),
        Index("ix_field_change_logs_field_time", "table_name", "field_name", "changed_at"),
    )
