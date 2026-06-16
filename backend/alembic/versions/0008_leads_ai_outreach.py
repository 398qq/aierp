"""0008 — leads.ai_outreach + ai_outreach_at

给 leads 表加 AI 写的个性化开场白 (100-150 字) + 生成时间。
销售员直接复制粘贴发出去/打电话时参考。
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("ai_outreach", sa.Text(), nullable=True))
    op.add_column(
        "leads",
        sa.Column("ai_outreach_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_leads_ai_outreach_at", "leads", ["ai_outreach_at"])


def downgrade() -> None:
    op.drop_index("ix_leads_ai_outreach_at", table_name="leads")
    op.drop_column("leads", "ai_outreach_at")
    op.drop_column("leads", "ai_outreach")
