"""add logistics fields to purchase_orders

Background
----------
后端 model `PurchaseOrder` 已经声明了 `logistics_no` 和 `logistics_provider` 两个字段，
但实际数据库表一直没有这两列（早期 model 添加字段时没生成 alembic 迁移文件）。
直接查询 PO 详情（`/api/v1/purchase-orders/{id}`）和创建 PO 都会抛
`asyncpg.exceptions.UndefinedColumnError: column "logistics_no" of relation "purchase_orders" does not exist`。

2026-06-03 早上处理 CJC6811A 采购单（PO202606020001）时首次发现并临时 `ALTER TABLE` 修复，
本迁移把这次修复正式纳入版本控制，避免下次部署或新环境又掉坑。

Revision ID: 0003_po_logistics_fields
Revises: 0002_critical_indexes
Create Date: 2026-06-03 08:50:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "0003_po_logistics_fields"
down_revision = "0002_critical_indexes"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str, bind) -> bool:
    insp = inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    """Add logistics tracking columns to purchase_orders.

    Idempotent: 在已存在列的环境（比如之前通过
    `ALTER TABLE` 临时修过）下不会重复添加，方便回放。
    """
    bind = op.get_bind()
    if not _column_exists("purchase_orders", "logistics_no", bind):
        op.add_column(
            "purchase_orders",
            sa.Column("logistics_no", sa.String(length=100), nullable=True),
        )
    if not _column_exists("purchase_orders", "logistics_provider", bind):
        op.add_column(
            "purchase_orders",
            sa.Column("logistics_provider", sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    """Drop logistics tracking columns from purchase_orders."""
    bind = op.get_bind()
    if _column_exists("purchase_orders", "logistics_provider", bind):
        op.drop_column("purchase_orders", "logistics_provider")
    if _column_exists("purchase_orders", "logistics_no", bind):
        op.drop_column("purchase_orders", "logistics_no")
