"""Commission scheme models — tier configuration, assignment, version audit.

013 提成方案配置的核心模型，与 012 佣金模型配合使用。
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class CommissionScheme(TimestampMixin, Base):
    """提成方案主表 — 全局配置 + 版本管理 + 生效范围。"""

    __tablename__ = "commission_schemes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, default=None)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), default=None
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending', 'active', 'expired', 'inactive')",
            name="ck_scheme_status",
        ),
    )

    # relationships
    tiers: Mapped[list["SchemeTier"]] = relationship(
        "SchemeTier", back_populates="scheme", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["SchemeAssignment"]] = relationship(
        "SchemeAssignment", back_populates="scheme", cascade="all, delete-orphan"
    )
    versions: Mapped[list["SchemeVersion"]] = relationship(
        "SchemeVersion", back_populates="scheme", cascade="all, delete-orphan"
    )


class SchemeTier(TimestampMixin, Base):
    """阶梯定义 — 一条记录代表一个金额区间 + 比例 + 可选的产品线/客户覆盖。"""

    __tablename__ = "scheme_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("commission_schemes.id", ondelete="CASCADE"), nullable=False
    )
    tier_no: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly_sales"
    )
    low_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    high_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), default=None)
    rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    cap_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    floor_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0
    )
    product_category: Mapped[str | None] = mapped_column(String(100), default=None)
    customer_level: Mapped[str | None] = mapped_column(String(20), default=None)

    __table_args__ = (
        CheckConstraint("rate >= 0 AND rate <= 1", name="ck_tier_rate"),
        CheckConstraint(
            "low_amount >= 0 AND (high_amount IS NULL OR high_amount > low_amount)",
            name="ck_tier_range",
        ),
        CheckConstraint(
            "floor_amount <= cap_amount OR cap_amount = 0",
            name="ck_tier_cap_floor",
        ),
    )

    # relationships
    scheme: Mapped["CommissionScheme"] = relationship(
        "CommissionScheme", back_populates="tiers"
    )


class SchemeAssignment(TimestampMixin, Base):
    """方案分配 — 用户或角色与方案的关联。"""

    __tablename__ = "scheme_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("commission_schemes.id", ondelete="CASCADE"), nullable=False
    )
    assignee_type: Mapped[str] = mapped_column(String(10), nullable=False)
    assignee_id: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "assignee_type IN ('user', 'role')",
            name="ck_assignee_type",
        ),
        UniqueConstraint(
            "assignee_type",
            "assignee_id",
            "deleted_at",
            name="uq_assignee_scheme",
        ),
    )

    # relationships
    scheme: Mapped["CommissionScheme"] = relationship(
        "CommissionScheme", back_populates="assignments"
    )


class SchemeVersion(TimestampMixin, Base):
    """方案版本审计 — 保存每次修改的 JSON 快照。"""

    __tablename__ = "scheme_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("commission_schemes.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(
        # JSONB — SQLite compat: Text in tests, JSONB in PG
        # Use String for portability; PG driver coerces.
        String,
        nullable=False,
    )
    changed_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # relationships
    scheme: Mapped["CommissionScheme"] = relationship(
        "CommissionScheme", back_populates="versions"
    )
