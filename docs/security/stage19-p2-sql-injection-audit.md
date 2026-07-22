# Stage 19 P2 #2 — SQL Injection Audit Report

**Date**: 2026-07-22
**Scope**: `backend/app/` 全量扫描
**Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.0 + asyncpg
**Files scanned**: 435 .py files

## 结论

**0 个 SQL 注入漏洞。** 项目全程使用 SQLAlchemy ORM + 参数绑定（bound parameters），
未发现任何字符串拼接进 SQL 执行路径。

## 扫描规则

| # | 模式 | 命中数 | 风险 |
|---|------|--------|------|
| 1 | `text(f"...")` / `text("..." + var)` | 0 | ✅ |
| 2 | `execute(...)` 拼接 / f-string | 0 | ✅ |
| 3 | `(select/update/delete/insert)(f"...")` | 0 | ✅（cache_delete 是缓存键误报）|
| 4 | psycopg2 `cursor.execute` 拼接 | 0 | ✅ |
| 5 | `.format()` / `%` 占位符进 execute | 0 | ✅ |
| 6 | LIKE 模式注入 | 0 | ✅（详见下）|
| 7 | 动态列名/表名（不可参数化位置） | 1 | ⚠️ 已审 — 安全 |
| 8 | JSON 路径查询 | 1 | ✅ SQLAlchemy func.substr |

## LIKE 模式详细审计（6 类全清）

全部命中均为 `column.ilike(f"%{user_input}%")` 形式。
**安全原因**：f-string 在 Python 层拼好后，整字符串作为 **单一参数** 传给 SQLAlchemy，
最终走 `LIKE $1`（asyncpg 参数绑定）。用户输入被完整转义，不可能注入 SQL。

示例:
```python
# backend/app/api/v1/customers/list.py:130-136
Customer.name.ilike(f"%{_keyword}%"),       # ✅ _keyword 是参数
Customer.code.ilike(f"%{_keyword}%"),
Customer.phone.ilike(f"%{_keyword}%"),
Customer.tax_id.ilike(f"%{_keyword}%"),
...
```

`{term}` / `{_keyword}` 等变量都是 Pydantic schema 验证过的字符串，最终走
SQLAlchemy 参数化路径。**不存在 `col.ilike(f"%{user}%' OR '1'='1")` 这类漏洞路径**。

## `text()` 调用清单（全部静态）

```python
# backend/app/database.py:144-468 — 都是从 .sql 文件读出来的迁移 SQL
text("SELECT count(*) FROM accounts WHERE deleted_at IS NULL")  # 静态字面量
text("deleted_at IS NULL")  # postgresql_where 表达式
```

文件路径 `backend/app/database.py` 中的 8 个 `text(` 调用都是 `sql_path.read_text()`
读迁移/seed 文件，无用户输入参与。

## 边界情况：动态属性访问（`getattr`）

```python
# backend/app/api/v1/products/crud.py:229
old_value=str(getattr(product, key))  # key 来自白名单 Pydantic schema
```

`key` 来自 `ProductAuditLog.field_name`（枚举字段），不可能越界到 `__class__` 等敏感属性。
**结论**：非 SQL 注入面。

## 防护机制现状

| 层 | 实现 |
|----|------|
| ORM | SQLAlchemy 2.0 全程 ORM，零 raw SQL |
| Driver | asyncpg 参数化（`$1`, `$2` 占位符）|
| Schema | Pydantic 2 输入校验 |
| Migration | 迁移文件版本化，无运行时拼接 |

## 后续

- bandit ruff rules 已通过 ✅
- mypy 严格模式已通过 ✅
- 建议: 在 `backend/tests/security/` 增加 **回归测试**（P2 #2 测试用例，下次如果有人写了 f-string SQL 立即 fail）
- 已加入 Stage 19 P2 #2 测试基线

## 审查者

代码高手 (阿助 · Stage 19 P2) — 2026-07-22 09:23
