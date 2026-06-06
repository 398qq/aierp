# 012 — 佣金管理（Commission Module）

> 销售订单 → 佣金计算 → 审批 → 发放 的全生命周期管理。
> 工程基线遵循 `CLAUDE.md` 9 大底线（状态机、Decimal、软删、RBAC、审计、request_id 等）。

---

## 1. 概述

### 1.1 背景
AIERP 当前已覆盖销售全流程（询价 → 报价 → 订单 → 送货 → 发票 → 回款），但**销售提成**只能靠财务手工 EXCEL 计算，月底对账耗时 1-2 天，易出错。Robin 每月需手动核对每个销售员的销售额 × 提成比例，跨月累计、离职交接均无留痕。

### 1.2 范围
**包含**：
- 佣金记录（Commission）的 CRUD
- 佣金计算（基于销售订单基数 × 比例）
- 状态机：草稿 → 待审批 → 已审批 → 已发放 / 已拒绝 / 已取消
- 批量审批、批量发放
- 佣金统计（按销售员、按期间、按客户）
- 操作日志

**不包含**：
- 销售提成方案配置（提成阶梯、封顶等）→ 后续 PRD（013）
- 佣金发放到工资系统集成 → 后续 PRD
- 多币种佣金 → 后续 PRD（当前仅 CNY）

### 1.3 关键约束
- 佣金基数 = 销售订单**已开票**金额（非订单总额，避免坏账佣金）
- 比例范围 0–1，DB 层 `CHECK (rate >= 0 AND rate <= 1)` 强制
- 金额一律 `Decimal`，DB 列 `NUMERIC(20, 6)`，计算用 `Decimal(str(...))` 防浮点漂移
- 状态转换走 `InvalidStateTransition` 领域异常（已有 `app/domain/shared/errors.py`）
- 所有路由 `Depends(get_current_user)`，权限由 RBAC 种子控制（`commission.*` 6 项）
- 软删 `deleted_at IS NULL`，列表查询强制过滤
- 审计：`created_by / updated_by / approved_by / approved_at / paid_at` 全留痕

---

## 2. 目标

| 目标 | 衡量标准 | 验证方式 |
|---|---|---|
| 财务月度佣金对账耗时从 1-2 天降至 ≤ 10 分钟 | 自动按销售员/期间汇总 | 单元测试 `test_commission_stats` |
| 杜绝 0.1+0.2 类浮点漂移 | 所有金额 `Decimal` 计算，测试断言精确等值 | `test_no_float_drift` |
| 非法状态转换零容忍 | DB `CHECK` + service `assert_can_transition_commission` | `test_illegal_transition_raises` |
| 权限到人 | 每个操作需对应 RBAC 权限 | `/permission-check finance` |
| 全链路可审计 | 创建/修改/审批/发放每步有 `user_id + timestamp` | 操作日志查询 |

---

## 3. 用户故事

### US-012-1 销售员 — 提交佣金申请
**作为**销售员张三，**我希望**在销售订单开票后自动生成佣金记录并提交审批，**以便**我能在月底前拿到应得提成。
- **AC-1**：当销售订单的全部关联发票状态变为「已支付」时，系统自动生成佣金记录（状态 = `draft`），基数 = 已开票金额，比例 = 当前用户的默认提成比例（v1 阶段由 admin 手动设置）
- **AC-2**：佣金记录展示在我的「待提交」列表
- **AC-3**：我点击「提交审批」后状态变为 `pending_approval`，不可再修改基数/比例

### US-012-2 销售经理 — 审批佣金
**作为**销售经理李四，**我希望**看到所有待审批的佣金记录，**以便**我批量审批并在异常时驳回。
- **AC-1**：「待审批」列表显示：销售人员、客户、基数、比例、佣金金额、提交时间
- **AC-2**：点击「审批通过」状态变为 `approved`，`approved_by / approved_at` 自动留痕
- **AC-3**：点击「驳回」需填写理由，状态变为 `rejected`，提交人收到通知（v1 站内信，v2 微信）
- **AC-4**：可批量审批 ≤ 50 条，失败的（状态已变化）单独标红

### US-012-3 财务 — 发放佣金
**作为**财务王五，**我希望**看到所有「已审批」未发放的佣金，**以便**我在发薪日批量打款并标记发放。
- **AC-1**：「待发放」列表显示已审批记录，按期间（YYYY-MM）分组
- **AC-2**：点击「标记发放」后状态变为 `paid`，`paid_amount = commission_amount`，`paid_at` 留痕
- **AC-3**：可导出该期佣金清单（Excel），含：单号、销售员、客户、金额、银行卡号（v1 留空，v2 集成 HR 系统）
- **AC-4**：已发放记录不可撤销（财务错误需走红冲流程，v2 PRD）

### US-012-4 老板 — 销售佣金总览
**作为**老板 Robin，**我希望**看到本月各销售员的佣金总额与发放进度，**以便**我做人事决策。
- **AC-1**：仪表盘「销售佣金」卡片显示：本期总额、已发放、待发放、人均
- **AC-2**：点击下钻到按销售员的明细，柱状图
- **AC-3**：跨期对比（本月 vs 上月）涨幅

### US-012-5 销售员 — 查看我的历史佣金
**作为**销售员张三，**我希望**查看自己历史所有佣金，**以便**我对账。
- **AC-1**：「我的佣金」页面显示：时间、关联销售单、基数、比例、金额、状态
- **AC-2**：可按期间筛选、按状态筛选
- **AC-3**：被驳回的记录显示驳回理由，可重新编辑后再次提交

---

## 4. 功能需求

### 4.1 佣金自动生成（v1.1 增强，本期预留）
- **触发**：当 `Invoice.status` 从 `draft/pending` 变为 `paid` 时，APScheduler 任务 `commission_auto_create`（cron 每日 02:00）扫描当日新支付的发票，匹配默认比例，生成 `Commission` 记录
- **去重**：`UNIQUE (sales_order_id, sales_user_id, period)` 防止同一订单同一销售员同一期间重复生成
- **本期不实现**：仅留 `service.commission_service.auto_create_from_invoice(invoice_id)` 函数骨架，标记 TODO

### 4.2 佣金计算
- 公式：`commission_amount = base_amount × rate`
- 输入：`base_amount >= 0`，`rate ∈ [0, 1]`
- 输出：`commission_amount`，`Decimal` 6 位小数（`ROUND_HALF_UP`）
- **防浮点漂移**：内部用 `Decimal(str(base)) * Decimal(str(rate))`，禁止 `float * float`
- **比例变更**：更新 `base_amount` 或 `rate` 时自动重算 `commission_amount`

### 4.3 状态机
```
        ┌────────┐
        │ draft  │
        └───┬────┘
            │ submit (sales / owner)
            ▼
   ┌─────────────────┐
   │ pending_approval│ ─── reject ──→ rejected
   └────────┬────────┘                │
            │ approve                 │ reopen
            ▼                         │
       ┌────────┐                     │
       │approved│ ◀───────────────────┘
       └───┬────┘
           │ mark_paid (finance)
           ▼
       ┌──────┐
       │ paid │ (terminal)
       └──────┘

   任意非 paid 状态可 cancel → cancelled (terminal)
```

| From | To | Trigger | 角色 | 副作用 |
|---|---|---|---|---|
| draft | pending_approval | 「提交审批」按钮 | 销售员本人 / 销售经理 | 通知审批人 |
| pending_approval | approved | 「审批通过」 | 销售经理 / 财务 | `approved_by/at` 留痕；通知提交人 |
| pending_approval | rejected | 「驳回」+ reason | 销售经理 | 记录 reason；通知提交人 |
| approved | paid | 「标记发放」 | 财务 | `paid_at` 留痕；记录到发放清单 |
| * | cancelled | 「取消」 | 销售员本人 / 销售经理 | 记录取消原因 |

### 4.4 列表与搜索
- 默认按 `created_at DESC` 排序
- 过滤：状态、销售员、期间、关联销售单号
- 分页：默认 20/页，最大 100
- 导出：Excel（`read-excel-file` 生成，前端 `/api/v1/finance/commissions/export`）

### 4.5 批量操作
- **批量审批**：`POST /finance/commissions/batch-approve` body `{ids: [1,2,3]}`
  - 全部合法 → 一并通过
  - 任一不合法（状态已变化）→ 整体回滚，返回哪些失败
- **批量发放**：同理 `POST /finance/commissions/batch-mark-paid`
- 单次 ≤ 50 条（v1 限制，避免长事务）

### 4.6 权限矩阵

| 操作 | sales | sales_mgr | finance | admin |
|---|---|---|---|---|
| 查看自己 | ✅ | ✅ | ❌（全部） | ✅ |
| 查看全部 | ❌ | ✅ | ✅ | ✅ |
| 创建 (auto) | n/a | n/a | n/a | n/a |
| 编辑 (draft) | ✅ | ✅ | ❌ | ✅ |
| 提交审批 | ✅ | ✅ | ❌ | ✅ |
| 审批 | ❌ | ✅ | ❌ | ✅ |
| 驳回 | ❌ | ✅ | ❌ | ✅ |
| 标记发放 | ❌ | ❌ | ✅ | ✅ |
| 取消 | ✅（仅自己 draft） | ✅ | ❌ | ✅ |
| 导出 | ❌ | ✅ | ✅ | ✅ |

### 4.7 通知
- `pending_approval` → 通知所有「销售经理」角色
- `approved` → 通知「提交人」+「财务」
- `rejected` → 通知「提交人」（携带 reason）
- `paid` → 通知「提交人」+「老板」
- v1：站内信（已有 Notification 模型）；v2：邮件 + 企微

### 4.8 报表
- `/api/v1/finance/commissions/summary?period=2026-06`
  - 按销售员分组：人数、总额、已发放、待发放
  - 按客户分组：客户数、总额
  - 期间对比：vs 上月
- 前端复用 `MetricBand` 顶部 + `Recharts` 柱状图 + 明细表

---

## 5. 非功能需求

### 5.1 性能
- 列表查询 P95 ≤ 300ms（10 万行表，全索引覆盖）
- 批量审批 50 条 P95 ≤ 1s
- 报表聚合 P95 ≤ 800ms（按 period 索引，5 万行聚合）

### 5.2 安全
- 金额字段对销售员角色脱敏（`commission_amount` 在 list 接口对非 owner + 非管理员返回 `null`）
- 银行卡号（v2）走 `app/core/field_encryption.py` 加密存储
- 操作日志：每条 commission 的所有状态变更都进 `audit_logs`

### 5.3 可用性
- 状态机非法转换 → 返回 422 + 具体允许的转换列表
- 重复生成 → 唯一索引兜底，返回 409
- 网络/服务异常 → 操作日志留痕，user 重试友好

### 5.4 兼容性
- 不破坏现有 25 个 API 模块
- 不引入新依赖
- DB migration 可回滚（migration 文件包含 `-- DOWN`）

### 5.5 可观测性
- 慢查询日志：commission 列表 query > 200ms 触发
- request_id 端到端贯穿
- 状态转换打 INFO 日志（`commission.transition id=123 draft→pending_approval by=user_id=7`）

### 5.6 可测试性
- service 层纯函数（`_compute_commission_amount`）独立测试
- 状态机 100% 覆盖
- Decimal 精度 100% 覆盖
- 集成测试用 SQLite（已有 conftest），pgvector 兼容 patch

---

## 6. 数据模型

### 6.1 ER 图

```
┌──────────────┐         ┌──────────────┐
│   sales_     │         │    users     │
│   orders     │         │              │
└──────┬───────┘         └──────┬───────┘
       │ 1:N                    │ 1:N
       │                        │
       │           ┌────────────┴────────────┐
       └──────────►│       commissions       │◄──────────────┐
                   │                          │               │
                   │  id, commission_no       │               │
                   │  sales_order_id (FK)     │               │
                   │  sales_user_id (FK)      │               │
                   │  customer_id (FK, NULL)  │               │
                   │  base_amount NUMERIC     │               │
                   │  rate NUMERIC            │               │
                   │  commission_amount       │               │
                   │  paid_amount             │               │
                   │  status VARCHAR(20)      │               │
                   │  approved_by (FK users)  │───────────────┘
                   │  approved_at             │
                   │  paid_at                 │
                   │  period VARCHAR(20)      │
                   │  notes TEXT              │
                   │  + TimestampMixin        │
                   └──────────────────────────┘
                            │
                            │ N:1
                            ▼
                   ┌──────────────┐
                   │  customers   │ (optional)
                   └──────────────┘
```

### 6.2 表结构（DDL）

```sql
CREATE TABLE commissions (
    id BIGSERIAL PRIMARY KEY,
    commission_no VARCHAR(64) UNIQUE,                -- CM202606050001
    sales_order_id BIGINT NOT NULL REFERENCES sales_orders(id) ON DELETE RESTRICT,
    sales_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    customer_id BIGINT REFERENCES customers(id) ON DELETE SET NULL,

    base_amount NUMERIC(20, 6) NOT NULL DEFAULT 0,
    rate NUMERIC(8, 4) NOT NULL DEFAULT 0,
    commission_amount NUMERIC(20, 6) NOT NULL DEFAULT 0,
    paid_amount NUMERIC(20, 6) NOT NULL DEFAULT 0,

    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'pending_approval', 'approved', 'paid', 'rejected', 'cancelled')),
    approved_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    period VARCHAR(20),
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    created_by BIGINT REFERENCES users(id),
    updated_by BIGINT REFERENCES users(id),

    CONSTRAINT ck_commission_rate_range CHECK (rate >= 0 AND rate <= 1)
);

CREATE INDEX idx_commissions_sales_order_id ON commissions(sales_order_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_commissions_sales_user_id ON commissions(sales_user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_commissions_status ON commissions(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_commissions_period ON commissions(period) WHERE deleted_at IS NULL;
CREATE INDEX idx_commissions_created_at ON commissions(created_at DESC);
```

### 6.3 索引策略
- `idx_commissions_sales_user_id`（partial, 排除软删）→ 个人历史查询
- `idx_commissions_status`（partial）→ 列表过滤
- `idx_commissions_period`（partial）→ 报表聚合
- `idx_commissions_created_at`（降序）→ 默认列表排序
- v1 不上 pgvector（HNSW 不可用，因为没有 embedding 需求）

### 6.4 字段脱敏策略
| 字段 | 销售员本人 | 销售员他人 | 销售经理 | 财务 | admin |
|---|---|---|---|---|---|
| commission_amount | ✅ | ❌ | ✅ | ✅ | ✅ |
| base_amount | ✅ | ❌ | ✅ | ✅ | ✅ |
| rate | ✅ | ❌ | ✅ | ✅ | ✅ |
| paid_amount | ✅ | ❌ | ✅ | ✅ | ✅ |
| customer_id | ✅ | ❌ | ✅ | ✅ | ✅ |

脱敏在 schema 层做：`CommissionRead` 提供 `amount_for_role(role)` 方法。

---

## 7. API 设计

所有路由前缀 `/api/v1/finance/commissions`，统一 `{ code, msg, data }` 响应。

### 7.1 端点列表

| Method | Path | 权限 | Body / Query | Returns |
|---|---|---|---|---|
| GET | `/` | `commission.read` | `?page&page_size&status&sales_user_id&period&sales_order_id` | `PageData<Commission>` |
| GET | `/{id}` | `commission.read` | - | `Commission` |
| POST | `/` | `commission.create` | `{sales_order_id, sales_user_id, base_amount, rate, period, notes}` | `Commission` |
| PATCH | `/{id}` | `commission.update` | `{base_amount?, rate?, period?, notes?, status?}` | `Commission`（状态变更时校验状态机） |
| DELETE | `/{id}` | `commission.delete` | - | `{id, deleted: true}` |
| POST | `/{id}/transition` | `commission.update` + 角色判断 | `{to, reason}` | `Commission`（专用状态流转端点） |
| POST | `/batch-approve` | `commission.approve` | `{ids: number[]}` | `{succeeded: [], failed: [{id, reason}]}` |
| POST | `/batch-mark-paid` | `commission.pay` | `{ids: number[]}` | `{succeeded: [], failed: []}` |
| GET | `/summary` | `commission.read` | `?period=2026-06` | `{by_user: [], by_customer: [], by_status: {}, vs_last_period: {}}` |
| GET | `/export` | `commission.read` + 角色 | `?period` | Excel 文件流 |

### 7.2 状态流转端点（重点）

`POST /finance/commissions/{id}/transition`

```json
// Request
{ "to": "approved", "reason": "Q1 销售数据已核对" }

// Response 200
{ "code": 0, "msg": "ok", "data": { ...Commission... } }

// Response 422（非法转换）
{ "code": "INVALID_STATE_TRANSITION", "msg": "illegal commission transition: paid → cancelled",
  "data": null, "current": "paid", "target": "cancelled", "allowed": [] }

// Response 404（不存在）
{ "code": 404, "msg": "commission not found", "data": null }
```

### 7.3 批量审批

`POST /finance/commissions/batch-approve`

```json
// Request
{ "ids": [101, 102, 103] }

// Response 200（全部成功）
{ "code": 0, "msg": "ok", "data": { "succeeded": [101, 102, 103], "failed": [] } }

// Response 207（部分失败）
{ "code": 0, "msg": "partial", "data": {
    "succeeded": [101, 103],
    "failed": [{ "id": 102, "reason": "INVALID_STATE_TRANSITION: already approved" }]
}}
```

### 7.4 错误码

| code | 含义 | HTTP |
|---|---|---|
| 0 | 成功 | 200 |
| 400 | 参数错误 | 400 |
| 404 | 佣金记录不存在 | 404 |
| `INVALID_STATE_TRANSITION` | 非法状态转换 | 422 |
| `BUSINESS_RULE_VIOLATION` | 业务规则违反（如 rate 越界） | 422 |
| `PERMISSION_DENIED` | 权限不足 | 403 |
| 500 | 内部错误 | 500 |

---

## 8. UI/UX 设计

### 8.1 设计基线
遵循 `DESIGN.md`「ERP Operational Screens」章节：
- `<PageHeader>` 标题 + 操作
- `<SearchBar>` 过滤
- `<StatusTag tone>` 状态（语义色：draft/info, pending/processing, approved/info, paid/success, rejected/danger, cancelled/neutral）
- `<MoneyCell>` 金额（右对齐 + tnum + 颜色：负红/正绿/0 灰）
- `<ErrorBoundary>` 页面包裹
- `size="middle"` 表格
- Drawer 宽度 560（新建）/ 720（编辑）
- 文件 ≤ 500 行（AGENTS.md）

### 8.2 页面骨架

```
┌─ Breadcrumb: 财务 / 佣金管理 ─────────────────────┐
│                                                   │
│  [PageHeader] 佣金管理                             │
│  description: 销售订单佣金全流程                    │
│  actions: [+ 新建佣金] [批量审批] [导出]            │
├───────────────────────────────────────────────────┤
│  [SearchBar] placeholder="按单号/销售员/客户搜索"  │
│              [重置]                                │
├───────────────────────────────────────────────────┤
│  [Table size="middle" rowSelection]                │
│  □│单号  │销售单│客户 │销售员│基数   │比例│金额  │已发放│状态│操作   │
│  □│CM001│SO0421│晶科 │张三  │¥10,000│5% │¥500  │¥0   │草稿│编辑 提交│
│  ...（数字列 align="right"，状态列 100px，操作列固定右侧 220px）│
├───────────────────────────────────────────────────┤
│  共 234 条  [<] 1/12 [>]  每页[20▼]              │
└───────────────────────────────────────────────────┘
```

### 8.3 状态机可视化（可选 v1.1）
- 顶部进度条：`●草稿 → ○待审批 → ○已审批 → ○已发放`，当前态高亮
- 已驳回：`✕` 红色 + tooltip 显示 reason

### 8.4 关键交互

| 操作 | UI | 反馈 |
|---|---|---|
| 提交审批 | 「提交审批」按钮（仅 draft） | toast「已提交审批」+ 行变 pending_approval |
| 审批通过 | 「通过」按钮（pending_approval） | toast + 行变 approved + 列表自动 refresh |
| 驳回 | 「驳回」按钮 → 弹窗输入 reason（必填） | toast + 行变 rejected + reason 显示在 tooltip |
| 标记发放 | 「标记发放」按钮（approved） | 二次确认弹窗（防误操作） + toast |
| 取消 | 「取消」按钮（draft/pending_approval） | 弹窗确认 + toast |
| 批量审批 | 选中 ≥ 1 → 顶部 `Affix` 提示「已选 N 项」+ 「批量审批」按钮 | 207 多状态结果显示 |
| 新建 | 顶部「+ 新建佣金」 → Drawer 560px | 提交后 Drawer 关闭 + 列表刷新 |

### 8.5 表单字段（新建 Drawer）

| 字段 | 控件 | 校验 | 默认值 |
|---|---|---|---|
| 销售单 ID | `InputNumber` | 必填，> 0 | - |
| 销售人员 ID | `InputNumber` | 必填，> 0 | 当前用户 |
| 佣金基数 (¥) | `InputNumber` step=100 | ≥ 0 | 0 |
| 比例 (0–1) | `InputNumber` step=0.01 min=0 max=1 | 0 ≤ x ≤ 1 | 0 |
| 结算周期 | `Input` | 格式 YYYY-MM | 当月 |

提交后服务端重算 `commission_amount`，前端预览显示「预估佣金 = ¥XXX」。

### 8.6 空/错/加载态
- 空：`<EmptyState description="还没有佣金记录 — 从已完成的销售订单创建第一条" />`
- 加载：`<Spin>` 或骨架屏（> 3 行）
- 错误：`<ErrorBoundary>` 兜底 + 重试按钮
- 部分失败（批量）：内联红条 + 失败明细展开

### 8.7 权限按钮可见性
- 「+ 新建佣金」 → 所有有 `commission.create` 权限的角色
- 「批量审批」 → `commission.approve` 角色
- 「标记发放」 → `commission.pay` 角色
- 其他用户的「编辑/删除/状态流转」 → 不可见

### 8.8 响应式
- ≥ 1440px：完整 10 列
- 1024–1440px：隐藏「客户」「销售员」列，点击行展开
- 768–1023px：Drawer 全屏，列表转卡片
- < 768px：移动端 V1 仅支持查看，不支持操作

### 8.9 已有 `<ui/>` 组件复用
| 用途 | 组件 |
|---|---|
| 页面标题块 | `<PageHeader>` |
| 过滤栏 | `<SearchBar>` |
| 状态显示 | `<StatusTag tone label>` |
| 金额单元格 | `<MoneyCell>`（新建于 `frontend/src/ui/MoneyCell.tsx`，v1.1 提取） |
| KPI 行 | `<MetricBand>`（仪表盘用） |
| 空数据 | `<EmptyState>` |
| 错误兜底 | `<ErrorBoundary>` |

---

## 9. 测试策略

### 9.1 单元测试（已完成 21/21）

| 测试类 | 用例数 | 覆盖点 |
|---|---|---|
| `TestCommissionStateMachine` | 12 | 合法/非法转换、终态、未知状态 |
| `TestCommissionAmountCalculation` | 7 | 零值、典型、高比例、精度、防漂移 |
| `TestCommissionValidation` | 2 | 状态对齐、终态无出边 |

文件：`backend/tests/test_commission.py`

### 9.2 集成测试（v1.1 补）

| 用例 | 路径 | 期望 |
|---|---|---|
| 创建佣金 | `POST /` | 200 + 自动算 commission_amount + 生成 commission_no |
| 列表过滤 | `GET /?status=approved` | 仅返回 approved |
| 状态机端点 | `POST /1/transition {to: 'paid'}` from `draft` | 422 + INVALID_STATE_TRANSITION |
| 批量审批 | `POST /batch-approve {ids: [1,2]}` | 部分成功返回 failed 详情 |
| 软删 | `DELETE /1` 后再 `GET /1` | 404 |
| 权限 | 销售员调 `POST /1/transition {to: 'approved'}` | 403 |

文件：`backend/tests/test_commission_api.py`

### 9.3 前端测试（v1.1 补）

| 用例 | 期望 |
|---|---|
| 列表渲染 | 表格 8 列、状态 tag、金额 tnum |
| 空状态 | 显示 EmptyState |
| 提交审批按钮可见 | draft 行可见，approved 行不可见 |
| 弹窗表单校验 | 销售单 ID 必填 |

文件：`frontend/src/pages/finance/CommissionList.test.tsx`

### 9.4 端到端（Playwright，v1.1）

```typescript
test('sales rep submits commission', async ({ page }) => {
  await login(page, 'sales');
  await page.goto('/finance/commissions');
  await page.getByRole('button', { name: '提交审批' }).first().click();
  await expect(page.getByText('待审批').first()).toBeVisible();
});
```

### 9.5 性能/并发
- 10 万条 commission 列表 P95 < 300ms（EXPLAIN ANALYZE 验证索引）
- 50 条批量审批 P95 < 1s（单事务 + 缓存版本号）
- 并发提交同一佣金 → 一成功一 409（`SELECT ... FOR UPDATE` 或版本号）

### 9.6 验收清单
- [x] 21 个单元测试通过
- [x] `make lint` 通过（ruff + mypy + tsc）
- [x] 状态机非法转换返回 422
- [x] Decimal 计算无浮点漂移
- [x] 软删过滤全列表
- [x] RBAC 6 项种子已迁移
- [ ] API 集成测试补全
- [ ] 前端组件测试
- [ ] Playwright E2E
- [ ] 性能压测

---

## 附录 A：变更影响

### A.1 新增文件
- `backend/app/api/v1/commissions.py`
- `backend/app/migrations/012-add-commissions.sql`
- `backend/tests/test_commission.py`
- `frontend/src/pages/finance/CommissionList.tsx`
- `docs/requirements/012-commission.md`（本文件）

### A.2 修改文件
- `backend/app/models/finance.py`（+1 类）
- `backend/app/schemas/finance.py`（+3 schema）
- `backend/app/services/finance_service.py`（+commission 模块）
- `backend/app/api/v1/router.py`（+1 import +1 include）
- `frontend/src/types/index.ts`（+3 类型）
- `frontend/src/api/finance.ts`（+5 函数 +1 import）
- `frontend/src/App.tsx`（+1 路由）
- `frontend/src/layouts/MainLayout.tsx`（+1 菜单 +1 icon）

### A.3 依赖
无新增。

### A.4 部署
1. 跑 migration `psql -f backend/app/migrations/012-add-commissions.sql`
2. 重启后端（自动 register router）
3. 前端 `npm run build`（新增 lazy chunk `CommissionList`）
4. RBAC：把 `commission.*` 6 个权限授予「销售经理」「财务」角色（admin 操作）

---

## 附录 B：后续 PRD 衔接

- **PRD-013**：提成方案配置（阶梯、封顶、不同销售员不同比例）
- **PRD-014**：佣金发放到工资系统集成（HR API）
- **PRD-015**：佣金多币种 + 跨境销售
- **PRD-016**：佣金红冲（财务错误撤销）
