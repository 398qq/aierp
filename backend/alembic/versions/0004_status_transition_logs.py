"""add status_transition_logs table

Stage 2: 审计表 — 记录所有跟单状态机的状态转移。
设计原则：append-only，每行一条转移记录。

背景
----
之前 sales_service 里所有 status 变更都是「in-place」修改 SQLAlchemy 行：
  inv.status = "paid"
  await db.commit()

后果：
- 不知道这单从哪个状态改过来（被谁？什么时候？为啥？）
- 不知道一共转移过几次（客户来回 cancel 几次？）
- 没法定量分析（"客户 A 的订单平均停留 3 天才确认" 算不出来）

本表结构：
- aggregate_type + aggregate_id 定位哪个聚合
- status_before / status_after 状态转移快照
- action 业务动作（confirm/ship/complete/cancel/pay/issue）
- actor 谁触发的（user_id or system）
- reason 取消/冲销原因
- transitioned_at 时间戳
- 4 个组合索引（按时间查、按客户查、按聚合查）

Revision ID: 0004_status_transition_logs
Revises: 0003_po_logistics_fields
Create Date: 2026-06-11 11:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_status_transition_logs"
down_revision = "0003_po_logistics_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create status_transition_logs table.

    Idempotent: 在已存在表的环境（比如手动建过）下不会重复建。
    """
    op.execute("""
        CREATE TABLE IF NOT EXISTS status_transition_logs (
            id SERIAL PRIMARY KEY,
            aggregate_type VARCHAR(50) NOT NULL,
            aggregate_id INTEGER NOT NULL,
            aggregate_no VARCHAR(50),
            status_before VARCHAR(20),
            status_after VARCHAR(20) NOT NULL,
            action VARCHAR(50) NOT NULL,
            actor VARCHAR(100),
            reason TEXT,
            transitioned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            customer_id INTEGER REFERENCES customers(id),
            sales_order_id INTEGER REFERENCES sales_orders(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ,
            deleted_at TIMESTAMPTZ
        )
    """)

    # Indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_transition_logs_aggregate_type
            ON status_transition_logs (aggregate_type)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_transition_logs_aggregate_id
            ON status_transition_logs (aggregate_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_transition_logs_customer_id
            ON status_transition_logs (customer_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_transition_logs_sales_order_id
            ON status_transition_logs (sales_order_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_transition_logs_transitioned_at
            ON status_transition_logs (transitioned_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_transition_logs_aggregate
            ON status_transition_logs (aggregate_type, aggregate_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_transition_logs_customer_time
            ON status_transition_logs (customer_id, transitioned_at)
    """)


def downgrade() -> None:
    """Drop the audit log table.

    Reversible: this is an additive feature, dropping the table is safe
    (only loses history, not production data).
    """
    op.execute("DROP TABLE IF EXISTS status_transition_logs CASCADE")
