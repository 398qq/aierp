import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

# Many-to-many: customer <-> tag
customer_tag_table = Table(
    "customer_tag_links",
    Base.metadata,
    Column(
        "customer_id",
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("customer_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    # ── 基础标识 ──
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── 联系信息 ──
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 税务与法务 ──
    tax_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 纳税人识别号
    registration_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 统一社会信用代码
    invoice_title: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # 发票抬头
    invoice_address: Mapped[str | None] = mapped_column(Text, nullable=True)  # 发票地址

    # ── 银行信息 ──
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 开户行
    bank_account: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 银行账号

    # ── 分类与分级 ──
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    level: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # A / B / C / D
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    customer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price_tier: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # 价格等级
    annual_revenue: Mapped[float | None] = mapped_column(nullable=True)  # 年营业额
    employee_count: Mapped[int | None] = mapped_column(nullable=True)  # 员工数

    # ── 信用与付款 ──
    credit_limit: Mapped[float | None] = mapped_column(nullable=True)
    credit_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Net 30 / 月结30天
    payment_method: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # T/T / L/C
    currency: Mapped[str] = mapped_column(String(3), default="CNY")

    # ── 物流默认 ──
    delivery_address: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # 收货地址
    default_incoterm: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # FOB / CIF / EXW

    # ── CRM ──
    last_contacted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="new_lead"
    )  # new_lead/active/converted/vip/inactive/churned
    lifecycle: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # deprecated — superseded by status
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 组织层级 ──
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )

    # ── AI ──
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    ai_insights: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    contacts = relationship(
        "CustomerContact", back_populates="customer", lazy="selectin"
    )
    follow_ups = relationship(
        "CustomerFollowUp", back_populates="customer", lazy="selectin"
    )
    tags = relationship("CustomerTag", secondary=customer_tag_table, lazy="selectin")
    children = relationship(
        "Customer", back_populates="parent", lazy="selectin", remote_side="Customer.id"
    )
    parent = relationship(
        "Customer",
        back_populates="children",
        remote_side="Customer.parent_id",
        lazy="selectin",
    )
    opportunities = relationship(
        "Opportunity", back_populates="customer", lazy="selectin"
    )
    quotations = relationship("Quotation", back_populates="customer", lazy="selectin")
    sales_orders = relationship(
        "SalesOrder", back_populates="customer", lazy="selectin"
    )
    delivery_notes = relationship(
        "DeliveryNote", back_populates="customer", lazy="selectin"
    )
    tickets = relationship("Ticket", back_populates="customer", lazy="selectin")
    visits = relationship("Visit", back_populates="customer", lazy="selectin")
    samples = relationship("Sample", back_populates="customer", lazy="selectin")


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
    planned_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)

    customer = relationship("Customer", back_populates="follow_ups")


class CustomerTag(TimestampMixin, Base):
    __tablename__ = "customer_tags"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)


class CustomerAttachment(TimestampMixin, Base):
    __tablename__ = "customer_attachments"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(String(255))
    original_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(default=0)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)


class CustomerLog(TimestampMixin, Base):
    __tablename__ = "customer_logs"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE")
    )
    action: Mapped[str] = mapped_column(
        String(30)
    )  # create, update, delete, merge, tag, import
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)


class AlertRule(TimestampMixin, Base):
    __tablename__ = "alert_rules"

    name: Mapped[str] = mapped_column(String(100))
    rule_type: Mapped[str] = mapped_column(
        String(50)
    )  # no_order, credit_over, order_drop, ar_overdue
    threshold_days: Mapped[int | None] = mapped_column(
        nullable=True
    )  # for no_order: days without order
    threshold_pct: Mapped[float | None] = mapped_column(
        nullable=True
    )  # for credit_over/order_drop: percentage
    threshold_amount: Mapped[float | None] = mapped_column(
        nullable=True
    )  # for ar_overdue: amount
    enabled: Mapped[bool] = mapped_column(default=True)
    severity: Mapped[str] = mapped_column(
        String(20), default="warning"
    )  # info, warning, critical


class AlertEvent(TimestampMixin, Base):
    __tablename__ = "alert_events"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE")
    )
    rule_type: Mapped[str] = mapped_column(String(50))
    rule_name: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(default=False)
    read_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LevelRule(TimestampMixin, Base):
    __tablename__ = "level_rules"

    name: Mapped[str] = mapped_column(String(100))
    target_level: Mapped[str] = mapped_column(String(20))  # A, B, C, D
    condition_type: Mapped[str] = mapped_column(
        String(50)
    )  # revenue, order_count, days
    operator: Mapped[str] = mapped_column(String(10))  # >, <, >=, <=
    threshold_value: Mapped[float] = mapped_column()
    period_days: Mapped[int | None] = mapped_column(
        nullable=True
    )  # evaluation period in days
    enabled: Mapped[bool] = mapped_column(default=True)
    priority: Mapped[int] = mapped_column(default=0)


# ---------------------------------------------------------------------------
# Customer AI tables — defined to match the existing PostgreSQL schema.
# These tables are populated by the AI orchestration layer
# (app/services/orchestration/*) and the work-queue endpoints in
# app/api/v1/ai/customer_ai.py. Models were missing on the ORM side
# even though the tables existed; added in v6.4 to unblock the
# /ai/customer/work-queue endpoint (HTTP 500 ImportError).
# ---------------------------------------------------------------------------


class CustomerAIRecommendation(TimestampMixin, Base):
    __tablename__ = "customer_ai_recommendations"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE")
    )
    snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer_ai_snapshot_daily.id"), nullable=True
    )
    model_version: Mapped[str] = mapped_column(String(50))
    action_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column()
    priority_score: Mapped[float] = mapped_column()
    expected_impact: Mapped[float | None] = mapped_column(nullable=True)
    due_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20))
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    context_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class CustomerAIFeedback(TimestampMixin, Base):
    __tablename__ = "customer_ai_feedbacks"

    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("customer_ai_recommendations.id", ondelete="CASCADE")
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE")
    )
    verdict: Mapped[str] = mapped_column(String(20))
    usefulness: Mapped[int | None] = mapped_column(nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    revenue_impact: Mapped[float | None] = mapped_column(nullable=True)
    cost_impact: Mapped[float | None] = mapped_column(nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator: Mapped[str | None] = mapped_column(String(100), nullable=True)


class CustomerAISnapshotDaily(TimestampMixin, Base):
    __tablename__ = "customer_ai_snapshot_daily"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE")
    )
    snapshot_date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    health_score: Mapped[float | None] = mapped_column(nullable=True)
    churn_risk_score: Mapped[float | None] = mapped_column(nullable=True)
    value_score: Mapped[float | None] = mapped_column(nullable=True)
    urgency_score: Mapped[float | None] = mapped_column(nullable=True)
    recency_days: Mapped[int | None] = mapped_column(nullable=True)
    frequency_90d: Mapped[int | None] = mapped_column(nullable=True)
    monetary_180d: Mapped[float | None] = mapped_column(nullable=True)
    overdue_followups: Mapped[int | None] = mapped_column(nullable=True)
    open_opportunities: Mapped[int | None] = mapped_column(nullable=True)
    outstanding_amount: Mapped[float | None] = mapped_column(nullable=True)
    feature_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class CustomerAIAction(TimestampMixin, Base):
    __tablename__ = "customer_ai_actions"

    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("customer_ai_recommendations.id", ondelete="CASCADE")
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE")
    )
    action_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    assignee: Mapped[str | None] = mapped_column(String(100), nullable=True)
    executed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    result_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
