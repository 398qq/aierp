"""Audit log models — Stage 2.

status_transition_log: tracks every state machine transition across
all sales aggregates (sales_order / invoice / payment_record /
delivery_note / quotation / opportunity). One row per transition.

Used for:
- "为什么这单状态变成 completed 了？"  (audit trail)
- 报表：平均停留时长（PENDING → CONFIRMED 平均几天？）
- 客户行为分析（哪些客户的订单经常被 cancel？）
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
