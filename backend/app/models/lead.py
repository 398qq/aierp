"""Lead model — developer leads pool (new customer candidates).

跟 Customer 表完全隔离：用于"开发新客户"前期记录潜在买家线索。
一旦确认合作（status=converted）就写 converted_customer_id 关联到 customers，
但 customers 表本身不会被自动修改——由用户决定何时真正落库。
"""
import datetime

from sqlalchemy import (
    BigInteger, DateTime, Float, ForeignKey, Integer, Numeric,
    String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # ── 关联产品 ──
    product_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )

    # ── 公司基础信息 ──
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    annual_revenue: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    # ── 联系人 ──
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_wechat: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── 线索管理 ──
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual",
        comment="web_search | cross_reference | manual | referral | import",
    )
    source_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new",
        comment="new | researching | contacted | qualified | lost | converted",
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium",
        comment="high | medium | low",
    )
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_contacted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_action_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_action: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── 量化匹配度 ──
    fit_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="0-100, 产品-客户匹配度"
    )
    fit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_annual_volume: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="预估年用量(pcs)"
    )
    estimated_annual_value: Mapped[float | None] = mapped_column(
        Numeric(18, 2), nullable=True, comment="预估年金额"
    )

    # ── AI 写的个性化开场白 (销售员直接复制发) ──
    ai_outreach: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_outreach_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── 转化 ──
    converted_customer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    converted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 关系
    product = relationship("Product", lazy="joined", foreign_keys=[product_id])
    converted_customer = relationship("Customer", lazy="joined", foreign_keys=[converted_customer_id])
