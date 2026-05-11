from sqlalchemy import Boolean, DECIMAL, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ApprovalRule(TimestampMixin, Base):
    __tablename__ = "approval_rules"

    doc_type: Mapped[str] = mapped_column(String(50))  # quotation, purchase_order
    min_amount: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    customer_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    flow_config: Mapped[dict] = mapped_column(JSON, default=list)  # [{level:1, approver_role:"sales_manager", approver_id:null}]
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ApprovalRequest(TimestampMixin, Base):
    __tablename__ = "approval_requests"

    doc_type: Mapped[str] = mapped_column(String(50))
    doc_id: Mapped[int] = mapped_column()
    submitter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, approved, rejected
    current_level: Mapped[int] = mapped_column(Integer, default=1)
    flow_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    submitter = relationship("User", foreign_keys=[submitter_id])
    actions = relationship("ApprovalAction", back_populates="request", lazy="selectin", order_by="ApprovalAction.level")


class ApprovalAction(TimestampMixin, Base):
    __tablename__ = "approval_actions"

    request_id: Mapped[int] = mapped_column(ForeignKey("approval_requests.id", ondelete="CASCADE"))
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(20))  # approve, reject
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)

    request = relationship("ApprovalRequest", back_populates="actions")
    approver = relationship("User", foreign_keys=[approver_id])
