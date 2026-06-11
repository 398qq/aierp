"""add field_change_logs table

Stage 7: 通用字段级 audit log.

背景
----
Stage 2 已有 status_transition_logs（专门给状态机）。
但其他表（customer / supplier / product / quotation / order 等）的
普通字段修改没有 audit —— 不知道谁改了客户邮箱、调了产品价格。

设计
----
一张通用表 field_change_logs + 多条记录：
- table_name + record_id：定位行
- field_name：哪个字段
- old_value / new_value：快照（Text，存序列化字符串）
- actor / reason / changed_at：标准元数据

Service 层通过 BaseCRUDService.update(data, audit=True) 触发。
每次 update 中 N 个字段变化 → 写 N 条记录（一字段一行）。

索引：
- (table_name, record_id)：查某行所有变更历史
- (table_name, field_name, changed_at)：查某字段变更趋势
- actor：查某人的修改历史
- changed_at：时间序查

Revision ID: 0005_field_change_logs
Revises: 0004_status_transition_logs
Create Date: 2026-06-11 16:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_field_change_logs"
down_revision = "0004_status_transition_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "field_change_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("table_name", sa.String(50), nullable=False),
        sa.Column("record_id", sa.Integer, nullable=False),
        sa.Column("field_name", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column("actor", sa.String(100), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_field_change_logs_table_name", "field_change_logs", ["table_name"])
    op.create_index("ix_field_change_logs_record_id", "field_change_logs", ["record_id"])
    op.create_index("ix_field_change_logs_changed_at", "field_change_logs", ["changed_at"])
    op.create_index("ix_field_change_logs_actor", "field_change_logs", ["actor"])
    op.create_index("ix_field_change_logs_record", "field_change_logs", ["table_name", "record_id"])
    op.create_index("ix_field_change_logs_field_time", "field_change_logs", ["table_name", "field_name", "changed_at"])


def downgrade() -> None:
    op.drop_index("ix_field_change_logs_field_time", "field_change_logs")
    op.drop_index("ix_field_change_logs_record", "field_change_logs")
    op.drop_index("ix_field_change_logs_actor", "field_change_logs")
    op.drop_index("ix_field_change_logs_changed_at", "field_change_logs")
    op.drop_index("ix_field_change_logs_record_id", "field_change_logs")
    op.drop_index("ix_field_change_logs_table_name", "field_change_logs")
    op.drop_table("field_change_logs")
