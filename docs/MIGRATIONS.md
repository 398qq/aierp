# 数据库迁移规范（Stage 5 Day 3）

## 当前状态

```
backend/alembic/versions/
├── 0001_baseline.py            # 标记基线（空 upgrade）
├── 0002_critical_indexes.py    # 加关键索引
├── 0003_po_logistics_fields.py # PO 物流字段
└── 0004_status_transition_logs.py # Stage 2 审计表
```

4 个 migration，4 个 down_revision 链：0001 → 0002 → 0003 → 0004。

## 规范

### 1. 命名

`<序号>_<snake_case 描述>.py`

- ✅ `0005_add_user_avatar.py`
- ❌ `add_avatar.py`（无序号）

### 2. 模板

```python
"""<一句话功能>

<背景 + 设计原则 + 表结构>

Revision ID: 0005_<slug>
Revises: <前一个 revision>
Create Date: <ISO 8601>
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_<slug>"
down_revision = "0004_status_transition_logs"  # ← 永远指上一个
branch_labels = None
depends_on = None


def upgrade() -> None:
    """<具体加什么 — 一段一段写 op.add_column / op.create_table>"""
    op.create_table(
        "user_avatars",
        sa.Column("user_id", sa.Integer, primary_key=True),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("uploaded_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_user_avatars_user_id", "user_avatars", ["user_id"])


def downgrade() -> None:
    """回滚 — 必须能干净回滚。drop_index → drop_table。"""
    op.drop_index("ix_user_avatars_user_id", "user_avatars")
    op.drop_table("user_avatars")
```

### 3. 强约束

| 约束 | 原因 |
|---|---|
| 必须有 `downgrade()` | 紧急回滚 |
| `upgrade()` 加列必须可空 | 老数据已存在 |
| 加 NOT NULL 列：分两步（先可空 → backfill → alter）| 避免 5xx 报错 |
| 加索引：标 `IF NOT EXISTS`（PG 9.5+）| 避免重复 |
| 改列类型：用 `op.alter_column` + `using=` 子句 | PG 类型转换 |
| 删列：**先备份**到 `archived_<table>` 或 `_deprecated_<col>` 表 | 后悔药 |

### 4. 不可逆操作

**DROP COLUMN** 不可逆。正确做法：
```python
def upgrade():
    # 1. 数据备份
    op.execute("CREATE TABLE _backup_user_avatars AS SELECT * FROM user_avatars")
    # 2. 软删
    op.alter_column("user_avatars", "url", new_column_name="url_deprecated")

def downgrade():
    op.alter_column("user_avatars", "url_deprecated", new_column_name="url")
```

### 5. 与 SQLAlchemy model 同步

alembic 改表后，**必须**同步 `backend/app/models/<table>.py`：
1. 改 Column 定义
2. 跑 `alembic upgrade head`（本地）
3. 跑 `pytest` 确认测试过

### 6. CI 流程

新增/修改 migration 文件后，**在 PR 描述写**：
```
- migration 序号：
- 改的表：
- 改的列：
- 是否需要 backfill：
- 是否需要停服（ALTER TABLE 大表）：
```

**大表 ALTER 警告**：
- `ALTER TABLE` 锁表（PG < 11 完整锁；PG 11+ 部分锁）
- 100 万行+ 表改列：用 `pg_repack` 或影子表策略
- 1 亿行+ 表改列：必须停服窗口

## 操作命令

```bash
# 本地查当前 migration
alembic current

# 看历史
alembic history --verbose

# 模拟升级（不真跑）
alembic upgrade head --sql

# 实际升级
alembic upgrade head

# 降一级
alembic downgrade -1

# 标记（不跑 upgrade，但记录为已跑过）
alembic stamp head
```

## Stage 2 审计表（0004）作为参考

看 `backend/alembic/versions/0004_status_transition_logs.py`：
- 4 个组合索引（按时间 / 客户 / 聚合）
- 15 列（5 业务 + 5 审计 + 5 元数据）
- append-only 设计（无 UPDATE/DELETE 触发器）
- docstring 解释"为什么这么设计"（背景 + 设计原则 + 表结构）

## 常见错误

### Q: 改了 model 没改 migration
答：CI 加 job 检查（Stage 5 待办）。临时方案：本地 `alembic revision --autogenerate -m "..."` 生成 diff。

### Q: 多人同时改 model 撞了 migration
答：每次改 model 前 `git pull`，本地用 `alembic stamp head` 对齐基线。

### Q: 测试库和线上库结构不同步
答：CI 加 `alembic upgrade head` 在 pytest 之前（Stage 5 Day 3 已加）。

## Stage 5 后续

- [ ] 加 alembic 注释到 pre-commit（每 migration 文件 必填 down_revision）
- [ ] CI 加 `alembic upgrade head --sql > migration.sql` artifact
- [ ] 文档化 008_critical_indexes.sql → alembic 迁移的差异
- [ ] 加 migration 影响评估（lock time / row count / rollback test）
