"""add marking codes (2026-06-18)

新增 3 个字段到 products 表，捕获晶岳 AF1117 实物 marking 拆解：
- package_marking_code: 封装 marking 码 (例: L = SOT-223)
- env_marking_code: 环保 marking 码 (例: G = RoHS 2.0)
- rohs_version: RoHS 版本 (例: 1.0/2.0/3.0)

业务背景：2026-06-18 老板录入 AF1117 系列时教了完整 chip marking 规则
（AF1117 + XXX + L + G），但 ERP schema 没有对应结构化字段，
之前只能塞进 notes 文本。老板说"没有字段添加上"后，我加这 3 个字段
+ 3 个 index 支持精确筛选。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ff92493188a'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 加 3 个新列
    op.add_column(
        'products',
        sa.Column('package_marking_code', sa.String(length=10), nullable=True)
    )
    op.add_column(
        'products',
        sa.Column('env_marking_code', sa.String(length=10), nullable=True)
    )
    op.add_column(
        'products',
        sa.Column('rohs_version', sa.String(length=20), nullable=True)
    )

    # 2) 加 3 个 index（支持精确筛选）
    op.create_index(
        op.f('ix_products_package_marking_code'),
        'products',
        ['package_marking_code'],
        unique=False
    )
    op.create_index(
        op.f('ix_products_env_marking_code'),
        'products',
        ['env_marking_code'],
        unique=False
    )
    op.create_index(
        op.f('ix_products_rohs_version'),
        'products',
        ['rohs_version'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_products_rohs_version'), table_name='products')
    op.drop_index(op.f('ix_products_env_marking_code'), table_name='products')
    op.drop_index(op.f('ix_products_package_marking_code'), table_name='products')
    op.drop_column('products', 'rohs_version')
    op.drop_column('products', 'env_marking_code')
    op.drop_column('products', 'package_marking_code')
