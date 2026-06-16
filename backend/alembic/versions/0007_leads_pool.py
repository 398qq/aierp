"""0007 leads pool — developer leads for product (e.g. WK2124-ISSG).

跟 customers 表完全隔离，用于"开发新客户"前期记录潜在买家线索：
- 标记 source（web_search / cross_reference / manual / referral）
- 标记 fit_score / fit_reason，量化产品-客户匹配度
- 支持 status 流转：new → researching → contacted → qualified → converted/lost
- 转化后写 converted_customer_id 关联到 customers 表（不修改 customers）

Rev: 0007
Down rev: 0006
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # 关联产品
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        # 公司基础信息
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("short_name", sa.String(100), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("company_size", sa.String(50), nullable=True),  # 小/中/大/上市
        sa.Column("annual_revenue", sa.Numeric(18, 2), nullable=True),
        # 联系信息
        sa.Column("contact_name", sa.String(100), nullable=True),
        sa.Column("contact_title", sa.String(100), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_wechat", sa.String(100), nullable=True),
        # 线索管理
        sa.Column(
            "source",
            sa.String(50),
            nullable=False,
            server_default="manual",
            comment="web_search | cross_reference | manual | referral | import",
        ),
        sa.Column("source_detail", sa.String(500), nullable=True),  # 哪个搜索/客户/活动
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="new",
            comment="new | researching | contacted | qualified | lost | converted",
        ),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default="medium",
            comment="high | medium | low",
        ),
        sa.Column("assigned_to", sa.String(100), nullable=True),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_action", sa.String(255), nullable=True),
        # 量化匹配度
        sa.Column("fit_score", sa.Float(), nullable=True, comment="0-100, 产品-客户匹配度"),
        sa.Column("fit_reason", sa.Text(), nullable=True, comment="为什么打分"),
        sa.Column("estimated_annual_volume", sa.Integer(), nullable=True, comment="预估年用量(pcs)"),
        sa.Column("estimated_annual_value", sa.Numeric(18, 2), nullable=True, comment="预估年金额"),
        # 转化
        sa.Column(
            "converted_customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    # 索引
    op.create_index("ix_leads_product_id", "leads", ["product_id"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_priority", "leads", ["priority"])
    op.create_index("ix_leads_source", "leads", ["source"])
    op.create_index("ix_leads_fit_score", "leads", ["fit_score"])
    op.create_index("ix_leads_company_name", "leads", ["company_name"])
    op.create_index("ix_leads_next_action_at", "leads", ["next_action_at"])


def downgrade() -> None:
    op.drop_index("ix_leads_next_action_at", table_name="leads")
    op.drop_index("ix_leads_company_name", table_name="leads")
    op.drop_index("ix_leads_fit_score", table_name="leads")
    op.drop_index("ix_leads_source", table_name="leads")
    op.drop_index("ix_leads_priority", table_name="leads")
    op.drop_index("ix_leads_status", table_name="leads")
    op.drop_index("ix_leads_product_id", table_name="leads")
    op.drop_table("leads")
