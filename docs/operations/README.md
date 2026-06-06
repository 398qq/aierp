# Operations — AIERP Claude 配置后的日常操作流程

> 这是一份给项目成员（Robin 和未来接手者）的可执行手册。
> 它告诉你在 AIERP 项目里，**每天 / 每周 / 每次新功能**应该按什么顺序、调用什么工具、与 Claude 怎么对话。

---

## 目录

1. [前置：理解配置](#1-前置理解配置)
2. [启动流程](#2-启动流程每天第一次开工)
3. [新功能开发（端到端）](#3-新功能开发端到端典型-1-2-天)
4. [Bug 修复](#4-bug-修复)
5. [Code Review](#5-code-review)
6. [数据 / 报表任务](#6-数据--报表任务)
7. [权限审计](#7-权限审计)
8. [发布流程](#8-发布流程)
9. [故障与紧急情况](#9-故障与紧急情况)
10. [Subagent 决策树](#10-subagent-决策树)
11. [每日 checklist](#11-每日结束-checklist)
12. [相关文档索引](#12-相关文档索引)

---

## 1. 前置：理解配置

在开始前，**先读完这 3 份文档**（每个新成员入职第一件事）：

| 文档 | 作用 | 必读章节 |
|---|---|---|
| `CLAUDE.md` | 工程底线（9 大不可妥协） | "Engineering Bottom Lines" |
| `AGENTS.md` | 仓库结构 + 编码规范 | "ERP Product Standards" |
| `DESIGN.md` | 设计系统（品牌 + 运营屏） | "ERP Operational Screens" |

**自动加载的工程护栏**（无需提醒）：

- `frontend/src/design-tokens.ts` — 颜色 / 间距 / 字号 / 圆角的源真相
- `.claude/agents/` — 4 个 subagent（按需 spawn）
- `.claude/commands/` — 6 个 slash command（`/` 触发）
- `.claude/hooks/` — 3 个自动化护栏
- `.mcp.json` — `postgres` MCP（直连库）/ `filesystem` MCP

---

## 2. 启动流程（每天第一次开工）

```bash
cd ~/aierp && git pull                  # 同步远端
make dev                                 # 后端 :8080 + 前端 :3002
claude                                   # 启 Claude Code
```

**Claude 启动时已自动应用**：

- 加载 `CLAUDE.md`（每次回答都遵守工程底线）
- 加载 `DESIGN.md`（每次画 UI 都引用设计系统）
- PostToolUse hook：Edit/Write 后自动 `ruff format` Python / `prettier + eslint` TS
- PreToolUse hook：拦截危险命令（`rm -rf /` / `DROP DATABASE` / fork bomb / `curl|sh`）
- Stop hook：回合结束自动跑 ruff + tsc + 检查新 SQL 是否有 `BEGIN/COMMIT`
- 状态栏显示：`[aierp] <模型> on <分支> · <最近 commit>  +<未提交数>`

---

## 3. 新功能开发（端到端，典型 1-2 天）

### 3.1 流程总览

```
[设计 spec] → [建数据层] → [写后端] → [写测试] → [写前端] → [写 PRD] → [验证] → [截图] → [commit]
   ↓              ↓            ↓          ↓          ↓          ↓         ↓         ↓
backend-    db-migrator   主 Claude  主 Claude  frontend-   主 Claude  make    scripts/
architect                            + tests     builder                 lint/test screenshot
```

### 3.2 第 1 步：先设计（不写代码）

对话主 Claude：

```
> 用 backend-architect 设计一个 ReturnOrder 模块
>   业务：客户退货，跟 sales_order 关联
>   状态机：draft → submitted → approved → received → closed / rejected
>   字段：refund_amount, restocking_fee, reason, return_items
>   权限：return_order.{create,read,update,delete,approve,receive}
```

**`backend-architect` 输出**：
- ER 图（ASCII 或 Mermaid）
- 状态机转移表 + 副作用
- SQLAlchemy model 草稿
- Pydantic schema 列表
- API 端点表
- 服务层 outline
- RBAC 矩阵
- 迁移注意事项
- 11 项 open questions

**你不写代码**，只审 spec。

### 3.3 第 2 步：审 spec + 决定

- 跟 Claude 一起改 spec
- 回答 open questions（v1 不实现的标记 TODO）
- 确认状态机终态
- 确认 RBAC 矩阵

### 3.4 第 3 步：建数据层（隔离 subagent）

```
> 用 db-migrator 按上面 spec 生成迁移文件 013-add-return-orders.sql
```

**`db-migrator` 输出**：
- `backend/app/migrations/013-add-return-orders.sql`
- 表 + 5 partial 索引（`WHERE deleted_at IS NULL`）
- 2 CHECK（status enum + rate range）
- 6 FK
- 6 RBAC 种子
- `-- DOWN` 段

**你 review**：
```bash
psql -d aierp_test -f backend/app/migrations/013-add-return-orders.sql
PGPASSWORD=aierp psql -h localhost -U aierp -d aierp -c "\d+ return_orders"
```

### 3.5 第 4 步：写后端 service + API

对话主 Claude（不再 spawn subagent，因为 backend-architect 的 spec 已定）：

```
> 按上面 spec 实现：
>   1. backend/app/models/sales.py 加 ReturnOrder
>   2. backend/app/schemas/sales.py 加 3 个 schema
>   3. backend/app/services/sales_service.py 加 CRUD + 状态机函数
>   4. backend/app/api/v1/return_orders.py 新建
>   5. backend/app/api/v1/router.py 注册
```

**Claude 自动遵守**（无需提醒）：

- 状态机用 `InvalidStateTransition` 领域错误（`app/domain/shared/errors.py`）
- Decimal 算金额（不 float）
- 软删 `deleted_at IS NULL` 过滤
- 每个路由 `Depends(get_current_user)`
- Service 不抛 `HTTPException`，抛 `AppError` / `DomainError`
- Edit/Write 后 `format-on-edit.sh` hook 自动 `ruff format`

### 3.6 第 5 步：写测试

```
> 给 ReturnOrder 写测试，参考 tests/test_commission.py 的结构
```

**期望覆盖**：
- 状态机 100%（合法 + 非法 + 终态 + 未知状态）
- Decimal 精度（含 0.1+0.2 漂移测试）
- 边界（空字符串 / Unicode / 负数 / 超长）
- RBAC 拒绝
- 软删过滤

```bash
cd backend && pytest tests/test_return_orders.py -v
```

### 3.7 第 6 步：写前端（隔离 subagent）

```
> 用 frontend-builder 生成 sales/return-orders 列表页
>   参考 pages/finance/CommissionList.tsx 的模式
```

**`frontend-builder` 强制**（自己遵守）：

- 导入从 `@/ui`（不用 inline）
- 表格 `size="middle"`，操作列 `fixed="right"`
- 金额用 `numericStyle`（`tnum` + 颜色 token）
- 状态用 `<StatusTag tone="...">`
- 整页 `<ErrorBoundary>` 包裹
- 路由 `React.lazy()`
- ❌ 禁碰后端 / 迁移 / `.env`

### 3.8 第 7 步：写 PRD

```
> 写 docs/requirements/013-return-orders.md
>   按 012-commission.md 的 9 章结构：概述 / 目标 / 用户故事 / 功能需求 / 非功能 / 数据模型 / API / UI/UX / 测试
```

PRD 是规范源头，后续维护 / 招人 / 老板汇报都从这取。

### 3.9 第 8 步：跑全套验证

```bash
make lint       # ruff + mypy + tsc
make test       # pytest + vitest
```

**期望**：
- `make lint` 通过
- `make test` 至少新功能 100% 通过
- 旧失败数量不增加

**Stop hook 兜底**：即使你忘了 `make lint`，每回合结束也会自动跑。

### 3.10 第 9 步：截图归档

参考 `scripts/screenshot-commission.py`：

```
> 写 scripts/screenshot-return-orders.py，截图存 docs/screenshots/
```

### 3.11 第 10 步：Commit（分两个）

```bash
# Commit 1：数据层 + 后端
git add backend/app/models/sales.py backend/app/schemas/sales.py \
        backend/app/services/sales_service.py backend/app/api/v1/return_orders.py \
        backend/app/api/v1/router.py backend/app/migrations/013-add-return-orders.sql \
        backend/tests/test_return_orders.py
git commit -m "feat(return-orders): add return order module with state machine

- Status machine: draft → submitted → approved → received → closed / rejected
- Decimal-based refund calc (no float drift)
- 5 partial indexes (filtered on deleted_at IS NULL)
- 6 RBAC seeds (return_order.{read,write,delete,approve,receive,export})
- 21 unit tests covering state machine + math + edge cases"

# Commit 2：前端 + PRD
git add frontend/src/pages/sales/ReturnOrder*.tsx frontend/src/api/sales.ts \
        frontend/src/types/index.ts frontend/src/App.tsx frontend/src/layouts/MainLayout.tsx \
        docs/requirements/013-return-orders.md docs/screenshots/return-orders-*.png
git commit -m "feat(return-orders): add list/detail pages and PRD

- List page with PageHeader + SearchBar + StatusTag + ErrorBoundary
- Status column uses semantic tone from design-tokens
- Money cells use numericStyle (tnum + color)
- 9-chapter PRD in docs/requirements/013-return-orders.md"
```

---

## 4. Bug 修复

### 4.1 紧急 bug（线上问题）

```
> 用 systematic-debugging 调查 production 上 [现象]
> 错误信息：[粘贴堆栈或截图]
> 已尝试：[步骤]
> 期望：[正确行为]
```

Claude 按 `重现 → 隔离 → 假设 → 加日志 → 修复 → 回归测试` 走。

### 4.2 普通 bug

```
> 修这个 bug：
>   - 复现步骤：...
>   - 期望：...
>   - 实际：...
>   - 影响范围：[用户 / 数据 / 性能]
```

Claude 写修复 → 写回归测试（确保不再犯）→ 跑全套。

### 4.3 状态机非法（用户报告「这个按钮点不了」）

```
> /status-flow <entity> --audit
```

输出 spec vs code 的 diff：

- ✅ 匹配
- ⚠️ 漂移（Enum vs UI 标签）
- ❌ 缺失（没 transition 函数 / RBAC 未挂）
- 💡 建议（加版本号列做乐观锁）

---

## 5. Code Review

### 5.1 合并前

```
> 用 qa-reviewer 审查我最近的 5 个 commit
> 重点关注：状态机 / Decimal / RBAC / 软删
```

**`qa-reviewer` 跑**：

1. `ruff check` + `mypy`
2. `pytest --cov=...`
3. 对照 `CLAUDE.md` 9 大底线逐项扫
4. 自动 escalate CRITICAL 反模式：
   - `float` 用在 money
   - `datetime.now()` 在业务逻辑
   - 状态 magic string
   - 新查询无 `deleted_at IS NULL` 过滤
   - 路由无 RBAC 声明
   - 前端页无 `ErrorBoundary`
   - 迁移无 `BEGIN/COMMIT`

输出 markdown 报告：`APPROVE` / `REQUEST CHANGES` / `COMMENT`。

### 5.2 收到同事 review 评论

```
> 用 receiving-code-review 处理这个 review：
>   "[评论原文]"
```

**不直接接受也不直接拒绝**，先用技术严谨性验证：

- 评论的技术依据对吗？
- 在自己代码里能不能复现？
- 是否有反例？

再决定改不改、改多少。

---

## 6. 数据 / 报表任务

### 6.1 临时数据查询

```
> 查 aierp 库里 2026 年 6 月份所有销售订单的金额分布，按客户分组 TOP 20
```

`postgres` MCP 直连，Claude 写 SQL 查，返回结果。

### 6.2 验证索引是否被命中

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM commissions
WHERE deleted_at IS NULL AND sales_user_id = 3 ORDER BY created_at DESC LIMIT 50;
```

期望看到 `Index Scan using idx_commissions_sales_user_id` 而不是 `Seq Scan`。

### 6.3 生成 mock 数据

```
> /data-mock customer 200 --edge-cases
```

生成 200 条客户记录，含：

- 中文公司名（晶科电子、长电科技…）
- 边界（空字符串 / 超长 / 负数 / Unicode emoji）
- 真实格式（中国手机号 / 城市地址）
- 业务边界（0 金额、跨年日期、leap year）

### 6.4 状态机文档归档

```
> /status-flow sales_order > docs/state-flows/sales-order.md
```

输出可贴 wiki 的状态机图 + 转移表 + RBAC + 副作用。

---

## 7. 权限审计

```
> /permission-check finance
```

输出每个路由的：

- 是否有 `permissions=[...]`
- service 层是否 re-check
- 权限码是否在 seed 表里
- 字段脱敏是否到位（销售员看自己 / 销售经理看全部 / 财务看金额）

发现缺口就生成 fix 代码 → 你 review → 提交。

---

## 8. 发布流程

```bash
# 1. 跑全套
make lint
make test

# 2. 跑迁移到生产
psql -h prod-host -U aierp -d aierp -f backend/app/migrations/013-add-return-orders.sql

# 3. 重启后端（保留 PID）
systemctl reload aierp-backend       # 或 supervisorctl / k8s rolling

# 4. 跑 smoke test
curl -s http://prod/api/v1/health | jq
curl -s -H "Authorization: Bearer $PROD_TOKEN" \
  http://prod/api/v1/return-orders?page=1 | jq

# 5. 看慢查询日志
journalctl -u aierp-backend -n 200 | grep slow_query

# 6. Git tag
git tag v2.7.0 && git push --tags
```

**回滚预案**：

```bash
# DB 回滚（migration 的 DOWN 段）
psql -h prod-host -U aierp -d aierp -c "DROP TABLE return_orders;"

# 代码回滚
git revert <merge-commit-sha>
git push
systemctl reload aierp-backend
```

---

## 9. 故障与紧急情况

### 9.1 Claude 改坏了代码

**Stop hook 已自动跑过 lint**，但万一看到回归：

```bash
# 用 git reflog 找最近能跑的 commit
git reflog | head -5
git reset --hard <good-commit>

# 让 Claude 看 diff
> 用 qa-reviewer 看看 HEAD 改坏了什么，定位并回滚
```

### 9.2 危险命令被拦截

```
> bash 提示 "rm -rf node_modules" 被 pre-bash-guard 拦截
```

正确做法是 `rm -rf frontend/node_modules && npm ci`，不会被拦截（不匹配 `/` / `~` / `.` 危险模式）。

如果确实需要危险操作：

```
> 我明确要执行 [危险命令]，理由：[说明]
> 临时绕过 pre-bash-guard，理由：[理由]
```

### 9.3 跑大批量 SQL 怕锁表

```
> 用 postgres MCP 帮我用 SELECT ... FOR UPDATE 锁定这批订单
>   并发安全的批量 update，给出 estimated time
```

### 9.4 Claude 用了 float 算钱（CLAUDE.md 底线违反）

**Stop hook 已经把它从 lint 阶段拦下**。如果漏过：

```
> 用 qa-reviewer 扫最近 10 个 commit，把所有 float 算钱的地方列出来
> 用 receiving-code-review 处理这个 review
```

---

## 10. Subagent 决策树

```
要做什么？
│
├─ 只看 spec / 设计 schema / 状态机
│   └─> backend-architect
│
├─ 改后端代码
│   ├─ 涉及模型/迁移 → db-migrator
│   └─ 涉及 service / API / 业务逻辑 → 直接对话主 Claude
│
├─ 改前端代码
│   └─> frontend-builder
│
├─ 审查 PR / 跑测试
│   └─> qa-reviewer
│
├─ 通用 CRUD 模块
│   └─> /new-entity
│
├─ 加新页面
│   └─> /add-page
│
├─ 查 / 改数据
│   └─> postgres MCP（直接对话 Claude 写 SQL）
│
└─ 不确定
    └─> 直接对话主 Claude；它会按需 spawn subagent
```

**Subagent 速查**：

| Agent | 何时 spawn | 关键能力 |
|---|---|---|
| `backend-architect` | 新模块 / 状态机 / API 契约 | 写 spec（不写代码） |
| `frontend-builder` | 加页面 / 改组件 | 强制用 `@/ui` 不用 inline |
| `db-migrator` | 表结构 / 索引 / RBAC 种子 | SQL 迁移 + 验证 |
| `qa-reviewer` | 合并前 / 改完代码 | 9 大底线扫描 + 测试 |

---

## 11. 每日结束 checklist

```
□ git status 干净（或所有改动已 commit）
□ make test 通过（或已知失败已记录 issue）
□ Stop hook 自动跑过 lint（看 Claude 末尾输出）
□ 没有未提交的 secret
□ 任务日志写入 docs/memory/YYYY-MM-DD.md（按全局 CLAUDE.md 规范）
□ 明天的开放问题列表（如果模块有）
```

---

## 12. 相关文档索引

### 项目根目录

- `CLAUDE.md` — 工程底线（9 大不可妥协）
- `AGENTS.md` — 仓库结构 + 编码规范
- `DESIGN.md` — 设计系统（品牌 + 运营屏）
- `Makefile` — 常用命令
- `frontend/src/design-tokens.ts` — 颜色 / 间距 / 字号 / 圆角源真相

### Claude 配置（`.claude/`）

```
.claude/
├── settings.json          # 权限 + hooks + 主题
├── settings.local.json    # 本地个性化
├── agents/                # 4 subagent
│   ├── backend-architect.md
│   ├── frontend-builder.md
│   ├── db-migrator.md
│   └── qa-reviewer.md
├── commands/              # 6 slash command
│   ├── new-entity.md
│   ├── add-page.md
│   ├── status-flow.md
│   ├── permission-check.md
│   ├── data-mock.md
│   └── i18n-sync.md
├── hooks/                 # 3 自动化护栏
│   ├── format-on-edit.sh
│   ├── pre-bash-guard.sh
│   └── stop-lint.sh
└── helpers/
    └── statusline.cjs
```

### 文档（`docs/`）

- `docs/requirements/NNN-*.md` — 各模块 PRD（9 章齐全）
- `docs/architecture/` — 架构图与决策
- `docs/features/` — 功能模块设计
- `docs/memory/YYYY-MM-DD.md` — 每日工作日志
- `docs/postmortem/` — 事故复盘
- `docs/progress.md` — 整体进度
- `docs/reports/` — 报表与分析
- `docs/screenshots/` — 页面截图归档
- `docs/operations/README.md` — 本文档

### 后端

- `backend/app/models/` — SQLAlchemy 模型（含 `base.py:TimestampMixin`）
- `backend/app/schemas/` — Pydantic
- `backend/app/services/` — 业务逻辑层
- `backend/app/api/v1/` — FastAPI 路由
- `backend/app/domain/shared/errors.py` — 领域异常（必用）
- `backend/app/migrations/` — 原始 SQL 迁移（顺序 `NNN-name.sql`）
- `backend/tests/` — pytest

### 前端

- `frontend/src/api/` — 所有 API 客户端（按域拆文件）
- `frontend/src/types/` — TypeScript 类型
- `frontend/src/ui/` — 6 个共享 UI 组件（PageHeader / SearchBar / StatusTag / MetricBand / EmptyState / ErrorBoundary）
- `frontend/src/components/` — 业务组件
- `frontend/src/pages/` — 页面（按域拆目录）
- `frontend/src/layouts/` — 布局

---

## 一句话总结

> **配置 = 行为，命令 = 工作流，subagent = 角色，hook = 护栏，PRD = 真相。**
> 日常工作就 3 件事：对话 Claude 拿设计 → spawn subagent 实现 → qa-reviewer 审。
> 不重复造轮子，不发明新规范，所有都从 `CLAUDE.md` / `DESIGN.md` / `design-tokens.ts` / 既有模式 长出来。

---

**版本**: v1.0 · 2026-06-05 · 与 Claude Code 2.1.163 + 9 大 subagent/command/hook 配套
