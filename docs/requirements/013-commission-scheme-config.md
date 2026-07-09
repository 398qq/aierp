# 013 — 提成方案配置（Commission Scheme Config）

> 在 012 佣金管理的基础上，引入灵活的提成方案配置层，支持阶梯式提成、封顶/保底、不同销售员不同比例、按产品线差异化提成。
> 工程基线遵循 `CLAUDE.md` 9 大底线（状态机、Decimal、软删、RBAC、审计、request_id 等）。

---

## 1. 概述

### 1.1 背景
012 佣金管理实现了佣金记录全生命周期管理，但**提成方案**仍是硬编码的单一比例（每个销售员一个固定 `rate`）。Robin 在实际使用中发现以下场景无法满足：

- **阶梯提成**：月销售额 ≤ 10 万提 3%，10–30 万提 5%，≥ 30 万提 7%
- **封顶/保底**：单笔佣金上限 ¥5,000，月度保底 ¥2,000
- **差异化比例**：资深销售员 5%，新人 2%，按产品线（主动器件 3%、被动器件 5%）分别设比例
- **临时促销**：Q3 某产品线提成翻倍，到期自动恢复
- **客户分级**：A 类客户提成比例上浮 20%

当前每次调比例需要财务改数据库，过程不可审计、不可追溯，且无法做"假设推演"（如果改方案，各销售员收入变化多少）。

### 1.2 范围
**包含**：
- 提成方案（CommissionScheme）CRUD
- 多规则组合的阶梯/封顶/保底引擎
- 方案版本管理（生效日期 + 版本号）
- 方案模拟（"what-if" 推演）
- 按销售员、产品线、客户等级等维度的差异化规则
- 临时促销方案到期自动失效
- 方案继承与覆盖层级

**不包含**：
- 方案自动审批流程（需在更大的审批工作流引擎中实现）→ 后续 PRD
- 与外部 HR/工资系统集成 → PRD-014
- 多币种提成 → PRD-015
- 佣金红冲 → PRD-016

### 1.3 关键约束
- 方案一经引用（已有佣金记录使用了该方案）即不可删除，仅可停用（`soft_delete`）
- 金额一律 `Decimal`，DB 列 `NUMERIC(18, 4)`，计算用 `Decimal(str(...))` 防浮点漂移
- 方案版本号单调递增，不支持版本回退（可通过创建新版本覆盖）
- 生效日期支持未来日期（预设方案），到期后自动失效
- 权限控制：方案配置仅 `admin` + `finance_mgr` 可修改，`sales_mgr` 可查看

---

## 2. 目标

| 目标 | 衡量标准 | 验证方式 |
|------|---------|---------|
| Robin 1 分钟内完成一次方案调整 | 从编辑到保存 < 60s | 手工验收 |
| 方案变更可审计 | 每次创建/修改记录 actor + timestamp + diff | `commission_scheme_versions` 表查询 |
| 阶梯计算准确 | 10 组边界值覆盖，断言 Decimal 精确等值 | `test_tier_calculation` |
| 方案模拟 < 2s | 100 条佣金 × 3 方案对比 < 2s API 响应 | `test_scheme_simulation_perf` |
| 临时促销到期自动失效 | cron 次日 02:00 扫描并标记过期 | `test_auto_expire` |

---

## 3. 用户故事

### US-013-1 财务经理 — 配置阶梯提成方案
**作为**财务经理，**我希望**创建一套阶梯提成方案（月销售额 0–10 万提 3%、10–30 万提 5%、≥ 30 万提 7%），**以便**系统自动按阶梯计算佣金。

- **AC-1**：我可以定义 N 个阶梯（≤ 10），每个阶梯有下限、上限、比例
- **AC-2**：阶梯之间边界值清晰（`10万` 算第一档还是第二档——定义区间为左闭右开 `[low, high)` ）
- **AC-3**：保存后系统验证阶梯无重叠、无断层（上一个阶梯的 high = 下一个阶梯的 low）
- **AC-4**：可以为阶梯选择维基（月销售额、季度销售额、单笔订单金额）

### US-013-2 Robin — 按销售员设不同方案
**作为**老板 Robin，**我希望**对资深销售员使用 5% 固定比例、对新入职销售员使用阶梯方案、对实习生使用 2% 封顶 ¥2,000，**以便**灵活管理团队成本。

- **AC-1**：支持按 `sales_user_id` 分配方案，一个用户同一时间只能有一个生效方案
- **AC-2**：未分配方案的用户使用"默认方案"（全局兜底）
- **AC-3**：覆盖层级：用户级 > 角色级 > 默认级

### US-013-3 财务经理 — 设置封顶/保底
**作为**财务经理，**我希望**在方案中设置单笔封顶 ¥5,000 和月度保底 ¥2,000，**以便**控制单笔佣金风险和保障新人收入。

- **AC-1**：封顶 `cap_amount` ≥ 0，0 表示不封顶
- **AC-2**：保底 `floor_amount` ≥ 0，0 表示不保底
- **AC-3**：先按比例计算 → 保底兜底 → 封顶截断
- **AC-4**：在佣金明细中显示每一步（算前、保底后、封顶后），方便对账

### US-013-4 销售总监 — 按产品线差异化提成
**作为**销售总监，**我希望**对主动器件（IC）提 3%、被动器件（电阻电容）提 5%、整机产品提 2%，**以便**引导销售团队聚焦高利润品类。

- **AC-1**：方案支持按 `product_category` 设置不同比例，覆盖阶梯方案中的统一比例
- **AC-2**：未匹配到产品线规则的订单按方案默认比例计算
- **AC-3**：可指定 N 个产品线规则（≤ 50）

### US-013-5 Robin — 临时提成促销
**作为**老板 Robin，**我希望**在 Q3 对某产品线设置"提成翻倍"临时方案，2026-07-01 自动生效，2026-09-30 自动失效，**以便** 618/双十一等促销季激励团队。

- **AC-1**：方案有 `effective_from` / `effective_to` 日期
- **AC-2**：到期前 7 天发送站内信通知相关角色
- **AC-3**：APScheduler cron 每日 02:00 扫描过期方案并标记 `expired`
- **AC-4**：过期方案不参与佣金计算，历史佣金不受影响（按当时的快照为准）

### US-013-6 财务经理 — 方案模拟（What-if）
**作为**财务经理，**我希望**在正式启用新方案前，选择上个月的销售数据做"假设推演"，**以便**评估新方案对成本和销售员收入的影响。

- **AC-1**：选择模拟期间（最多 3 个月）+ 新方案 → 系统重算佣金并与实际对比
- **AC-2**：结果展示：总额差异、人均差异、差异 > 20% 的销售员标红
- **AC-3**：模拟结果只读，不计入实际佣金，不可审批/发放

### US-013-7 销售员 — 查看我的提成方案
**作为**销售员，**我希望**查看当前生效的提成方案细则（阶梯表、封顶、保底），**以便**我知道每单能拿多少提成。

- **AC-1**：在"我的佣金"页面显示当前方案名称 + 有效期
- **AC-2**：点击展开阶梯明细表（可视化 bar chart：预估收入 vs 实际）
- **AC-3**：方案变更时收到通知（站内信）

---

## 4. 功能需求

### 4.1 提成方案模型

方案由一组规则组成，按优先级依次匹配：

```
Scheme
├── base_rules (默认规则)
│   ├── tiers[]          — 阶梯定义
│   ├── cap_amount       — 封顶
│   └── floor_amount     — 保底
├── product_rules[]      — 按产品线覆盖
├── customer_rules[]     — 按客户等级覆盖
└── assignment           — 分配对象
    ├── user_ids[]
    ├── role_ids[]
    └── is_default       — 是否全局兜底
```

**计算顺序**：
1. 确定方案（按覆盖层级）
2. 按 `product_category` 匹配产品线规则
3. 按 `customer_level` 匹配客户规则
4. 取匹配到的规则中的阶梯计算
5. 保底 → 封顶

### 4.2 阶梯类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `monthly_sales` | 月累计销售额 | 0–10 万 3%、10–30 万 5% |
| `quarterly_sales` | 季累计销售额 | 0–50 万 4%、50 万+ 6% |
| `single_order` | 单笔订单金额 | 0–1 万 2%、1 万+ 4% |
| `fixed_rate` | 固定比例（无阶梯） | 3.5% |

### 4.3 方案版本管理

- 每次修改创建新版本（`scheme_versions`），保留完整 history
- 版本号 `version_no` 从 1 开始递增
- 佣金记录创建时 `snapshot` 当前方案（记录当时的阶梯表 + 比例），后续方案变更不影响已发放佣金
- `schemes.effective_from` 为未来日期时状态为 `pending`，到期后为 `active`，过期后为 `expired`
- 同一时间一个用户只能有一个 `active` 方案（可有一个 `pending` 等待生效）

### 4.4 状态机

```
        ┌─────────┐
        │ draft   │
        └────┬────┘
             │ activate
             ▼
        ┌─────────┐
        │ pending │ ← effective_from 为未来
        └────┬────┘
             │ (cron: date reached)
             ▼
        ┌─────────┐
        │ active  │ ← 生效中
        └────┬────┘
             │ (cron: effective_to reached)
             ▼
        ┌─────────┐
        │ expired │ (terminal)
        └─────────┘

    draft/pending → deactivate (manual) → inactive (human操作停用)
```

### 4.5 方案生效规则

- 创建方案时 `effective_from` 默认当天
- 如果当天已有生效方案，新方案 `status = pending`，到生效日自动切换
- 旧方案在生效日自动 `expired`（cron 扫描）
- 手动停用一个方案会将所有关联用户的方案降级为默认方案

### 4.6 通知

- 方案分配/变更 → 通知相关销售员（站内信）
- 方案到期前 7 天 → 通知财务经理 + 销售总监
- 方案自动失效 → 通知相关销售员

### 4.7 方案模拟

- 选择方案 + 历史期间 → 系统读取该期间实际佣金 base_amount，应用新方案重算
- 结果按销售员分组对比：旧方案 vs 新方案，差异绝对值 + 百分比
- 差异率 > 20% 的销售员单独标红
- 模拟结果导出为 CSV

### 4.8 权限矩阵

| 操作 | admin | finance_mgr | sales_mgr | sales | 备注 |
|------|-------|-------------|-----------|-------|------|
| 查看方案列表 | ✅ | ✅ | ✅ | ❌ | 全员可见（财务+销售管理层） |
| 查看方案详情 | ✅ | ✅ | ✅ | ❌ | 含阶梯明细 |
| 创建方案 | ✅ | ✅ | ❌ | ❌ | |
| 编辑方案 | ✅ | ✅ | ❌ | ❌ | 仅 draft/pending 可编辑 |
| 激活方案 | ✅ | ✅ | ❌ | ❌ | |
| 停用方案 | ✅ | ✅ | ❌ | ❌ | |
| 删除方案 | ✅ | ❌ | ❌ | ❌ | 仅从未被引用的方案 |
| 方案模拟 | ✅ | ✅ | ✅ | ❌ | |
| 查看我的方案 | ✅ | ✅ | ✅ | ✅ | 仅查看已分配给自己 |

---

## 5. 非功能需求

### 5.1 性能
- 方案列表查询 P95 ≤ 200ms（索引覆盖）
- 阶梯计算单次 < 10ms
- 方案模拟（1000 条佣金 × 1 方案）< 2s
- 自动过期扫描 < 1s（50 条方案）

### 5.2 安全
- 方案金额字段对 `sales` 角色不可见
- 方案修改记录全部进 `audit_logs`（diff 格式）
- 方案不可删除已被引用的版本

### 5.3 可用性
- 阶梯配置校验实时返回错误（前端 + 后端双校验）
- 方案过期后自动降级到默认方案，不影响佣金生成
- 方案变更不追溯历史佣金（已按旧方案发放的不重新计算）

### 5.4 兼容性
- 不破坏 012 现有佣金模块
- 不引入新依赖
- DB migration 可回滚

### 5.5 可观测性
- 阶梯计算日志：`tier_match base=125000 tier=100000-300000 rate=0.05 → amount=6250`
- 方案变更打 INFO 日志
- 自动过期任务打 INFO 日志

---

## 6. 数据模型

### 6.1 ER 图

```
┌────────────────────────────┐
│  commission_schemes        │
│                            │
│  id BIGSERIAL PK           │
│  name VARCHAR(100)         │
│  description TEXT          │
│  version_no INT            │
│  status VARCHAR(20)        │
│  effective_from DATE       │
│  effective_to DATE (NULL)  │
│  is_default BOOLEAN        │
│  created_by BIGINT FK      │
│  + TimestampMixin          │
├────────────────────────────┤
│  scheme_tiers              │ ← 1:N
│  ┌──────────────────────┐  │
│  │ id BIGSERIAL PK      │  │
│  │ scheme_id BIGINT FK  │  │
│  │ tier_no INT           │  │
│  │ metric_type VARCHAR   │  │
│  │ low_amount NUMERIC    │  │
│  │ high_amount NUMERIC   │  │
│  │ rate NUMERIC(8,4)    │  │
│  │ cap_amount NUMERIC    │  │
│  │ floor_amount NUMERIC  │  │
│  │ product_category      │  │
│  │ customer_level        │  │
│  └──────────────────────┘  │
├────────────────────────────┤
│  scheme_assignments        │ ← 1:N
│  ┌──────────────────────┐  │
│  │ id BIGSERIAL PK      │  │
│  │ scheme_id BIGINT FK  │  │
│  │ assignee_type VARCHAR │  │
│  │ assignee_id INT       │  │
│  └──────────────────────┘  │
├────────────────────────────┤
│  scheme_versions           │ ← 1:N (audit)
│  ┌──────────────────────┐  │
│  │ id BIGSERIAL PK      │  │
│  │ scheme_id BIGINT FK  │  │
│  │ version_no INT       │  │
│  │ snapshot JSONB       │  │
│  │ changed_by INT       │  │
│  │ changed_at TIMESTAMPTZ│ │
│  └──────────────────────┘  │
```

### 6.2 核心表 DDL

```sql
-- 提成方案主表
CREATE TABLE commission_schemes (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    version_no INT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'pending', 'active', 'expired', 'inactive')),
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_schemes_status ON commission_schemes(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_schemes_effective ON commission_schemes(effective_from, effective_to) WHERE deleted_at IS NULL;

-- 阶梯定义
CREATE TABLE scheme_tiers (
    id BIGSERIAL PRIMARY KEY,
    scheme_id BIGINT NOT NULL REFERENCES commission_schemes(id) ON DELETE CASCADE,
    tier_no INT NOT NULL,
    metric_type VARCHAR(20) NOT NULL DEFAULT 'monthly_sales'
        CHECK (metric_type IN ('monthly_sales', 'quarterly_sales', 'single_order', 'fixed_rate')),
    low_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    high_amount NUMERIC(18, 4),  -- NULL = 无上限
    rate NUMERIC(8, 4) NOT NULL CHECK (rate >= 0 AND rate <= 1),
    cap_amount NUMERIC(18, 4) DEFAULT 0,    -- 0 = 不封顶
    floor_amount NUMERIC(18, 4) DEFAULT 0,  -- 0 = 不保底
    product_category VARCHAR(100),           -- NULL = 适用于所有品类的默认规则
    customer_level VARCHAR(20),             -- NULL = 适用于所有级别
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT ck_tier_range CHECK (low_amount >= 0 AND (high_amount IS NULL OR high_amount > low_amount)),
    CONSTRAINT ck_tier_cap_floor CHECK (floor_amount <= cap_amount OR cap_amount = 0)
);

CREATE INDEX idx_tiers_scheme ON scheme_tiers(scheme_id) WHERE deleted_at IS NULL;

-- 方案分配（用户/角色 → 方案）
CREATE TABLE scheme_assignments (
    id BIGSERIAL PRIMARY KEY,
    scheme_id BIGINT NOT NULL REFERENCES commission_schemes(id) ON DELETE CASCADE,
    assignee_type VARCHAR(10) NOT NULL CHECK (assignee_type IN ('user', 'role')),
    assignee_id INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    UNIQUE (assignee_type, assignee_id, deleted_at)
);

CREATE INDEX idx_assignments_scheme ON scheme_assignments(scheme_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_assignments_assignee ON scheme_assignments(assignee_type, assignee_id) WHERE deleted_at IS NULL;

-- 方案版本审计（保留每次变更的快照）
CREATE TABLE scheme_versions (
    id BIGSERIAL PRIMARY KEY,
    scheme_id BIGINT NOT NULL REFERENCES commission_schemes(id) ON DELETE CASCADE,
    version_no INT NOT NULL,
    snapshot JSONB NOT NULL,  -- 完整方案配置快照（含 tiers + assignments）
    changed_by INT NOT NULL REFERENCES users(id),
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scheme_versions ON scheme_versions(scheme_id, version_no DESC);
```

### 6.3 索引策略
- `idx_schemes_status`（partial）→ 列表筛选
- `idx_schemes_effective`（composite）→ 过期扫描 cron
- `idx_tiers_scheme`（partial）→ 方案详情加载
- `idx_assignments_assignee`（composite）→ 用户方案查找
- `idx_scheme_versions`（composite + DESC）→ 版本历史

### 6.4 字段脱敏策略
| 字段 | sales_mgr | finance_mgr | admin |
|------|-----------|-------------|-------|
| rate | ✅ | ✅ | ✅ |
| cap_amount | ✅ | ✅ | ✅ |
| floor_amount | ✅ | ✅ | ✅ |
| snapshot 历史 | ✅ | ✅ | ✅ |

`sales` 角色不可见方案模块（仅查看自己当前方案名称）。

---

## 7. API 设计

所有路由前缀 `/api/v1/finance/commission-schemes`，统一 `{ code, msg, data }` 响应（遵循 API 规范统一后的标准）。

### 7.1 端点列表

| Method | Path | 权限 | 说明 |
|--------|------|------|------|
| GET | `/` | `scheme.read` | 方案列表（filter: status, effective_from, q） |
| GET | `/{id}` | `scheme.read` | 方案详情（含阶梯 + 分配） |
| POST | `/` | `scheme.create` | 创建方案 |
| PUT | `/{id}` | `scheme.update` | 编辑方案（仅 draft/pending） |
| DELETE | `/{id}` | `scheme.delete` | 删除方案（仅未引用） |
| POST | `/{id}/activate` | `scheme.activate` | 手动激活（draft → pending/active） |
| POST | `/{id}/deactivate` | `scheme.deactivate` | 手动停用（active → inactive） |
| PUT | `/{id}/assign` | `scheme.assign` | 分配方案给用户/角色 |
| DELETE | `/{id}/assign` | `scheme.assign` | 移除某项分配 |
| GET | `/my-scheme` | `scheme.read`（self） | 当前用户生效方案 |
| POST | `/simulate` | `scheme.simulate` | 方案模拟（what-if） |
| GET | `/my-scheme` | `scheme.read`（self） | 当前用户生效方案 |
| GET | `/{id}/versions` | `scheme.read` | 版本历史 |
| GET | `/{id}/versions/{version_no}` | `scheme.read` | 版本快照详情 |

### 7.2 创建方案

```
POST /api/v1/finance/commission-schemes
```

```json
{
  "name": "2026-Q3 标准提成方案",
  "description": "Q3 月度阶梯提成，IC 3%、被动 5%",
  "effective_from": "2026-07-01",
  "effective_to": "2026-09-30",
  "is_default": false,
  "tiers": [
    {
      "tier_no": 1,
      "metric_type": "monthly_sales",
      "low_amount": 0,
      "high_amount": 100000,
      "rate": 0.03,
      "cap_amount": 5000,
      "floor_amount": 2000,
      "product_category": null,
      "customer_level": null
    },
    {
      "tier_no": 2,
      "metric_type": "monthly_sales",
      "low_amount": 100000,
      "high_amount": 300000,
      "rate": 0.05,
      "cap_amount": 10000,
      "floor_amount": 0,
      "product_category": null,
      "customer_level": null
    },
    {
      "tier_no": 3,
      "metric_type": "monthly_sales",
      "low_amount": 300000,
      "high_amount": null,
      "rate": 0.07,
      "cap_amount": 20000,
      "floor_amount": 0,
      "product_category": null,
      "customer_level": null
    }
  ],
  "assignments": [
    { "assignee_type": "role", "assignee_id": 3 },
    { "assignee_type": "user", "assignee_id": 7 }
  ]
}
```

响应 201：
```json
{ "code": 0, "msg": "success", "data": { "id": 1, "version_no": 1, ... } }
```

### 7.3 方案模拟

```
POST /api/v1/finance/commission-schemes/simulate
```

```json
{
  "scheme_id": 1,
  "period_from": "2026-04-01",
  "period_to": "2026-06-30",
  "user_ids": [3, 7, 12]
}
```

响应：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "summary": {
      "total_old": 125000.00,
      "total_new": 158000.00,
      "diff_amount": 33000.00,
      "diff_pct": 26.4,
      "affected_users": 3
    },
    "by_user": [
      {
        "user_id": 3,
        "name": "张三",
        "old_amount": 50000,
        "new_amount": 65000,
        "diff_pct": 30.0,
        "flag": "red"
      }
    ]
  }
}
```

### 7.4 方案计算引擎（内部 API）

```
async def compute_commission(
    user_id: int,
    base_amount: Decimal,
    product_category: str | None,
    customer_level: str | None,
    period: str,
    ref_date: date,
) -> CommissionResult:
    """根据用户 + 日期确定方案，计算提成金额。"""
```

返回：
- `scheme_id` — 使用的方案 ID
- `tier_matched` — 匹配到的阶梯描述
- `rate` — 最终比例
- `amount_before_cap` — 封顶前金额
- `amount` — 最终金额
- `snapshot` — 方案快照（用于存入 Commission 记录）

### 7.5 错误码

| code | 含义 | HTTP |
|------|------|------|
| 0 | 成功 | 200/201 |
| 400 | 参数错误（阶梯重叠、断层等） | 400 |
| 404 | 方案/用户不存在 | 404 |
| `SCHEME_TIER_OVERLAP` | 阶梯区间重叠 | 422 |
| `SCHEME_TIER_GAP` | 阶梯区间断层 | 422 |
| `SCHEME_ACTIVE_CONFLICT` | 同一用户已有生效方案 | 409 |
| `SCHEME_REFERENCED` | 方案已被引用不可删除 | 409 |
| `PERMISSION_DENIED` | 权限不足 | 403 |

---

## 8. UI/UX 设计

### 8.1 设计基线
遵循 `DESIGN.md`「ERP Operational Screens」章节 + 012 已有组件风格：
- `<PageHeader>`, `<SearchBar>`, `<StatusTag>`, `<MetricBand>`, `<EmptyState>`, `<ErrorBoundary>`
- 新增 `<TierTable>` 组件（阶梯可视化编辑）
- 金额复用 `<MoneyCell>`（或新建 `DecimalCell` 组件）
- `size="middle"` 表格

### 8.2 页面结构

```
┌─ Breadcrumb: 财务 / 提成方案 ─────────────────────┐
│                                                   │
│  [PageHeader] 提成方案配置                          │
│  description: 管理销售提成计算规则                   │
│  actions: [+ 新建方案]                              │
├───────────────────────────────────────────────────┤
│  [Tabs: 生效中 | 待生效 | 已过期 | 全部]             │
├───────────────────────────────────────────────────┤
│  [Table size="middle"]                             │
│  │方案名称 │版本│状态│生效日  │到期日  │分配人数│操作      │
│  │Q3标准   │3  │生效│07-01  │09-30  │12人    │详情 停用│
│  │…         │   │    │       │       │        │         │
├───────────────────────────────────────────────────┤
│  共 5 条  [<] 1/1 [>]                               │
└───────────────────────────────────────────────────┘
```

### 8.3 新建/编辑方案 Drawer（宽度 720px）

```
┌─ Drawer: 新建提成方案 ─────────────────────────┬─┐
│                                                │
│  ┌─ 基本信息 ─────────────────────────────────┐ │
│  │ 方案名称: [___________]                     │ │
│  │ 描述:     [___________]                     │ │
│  │ 生效日期: [📅 2026-07-01]                   │ │
│  │ 到期日期: [📅 2026-09-30]  (可选)           │ │
│  │ □ 设为默认方案                               │ │
│  └────────────────────────────────────────────┘ │
│                                                │
│  ┌─ 阶梯配置 ─────────────────────────────────┐ │
│  │ 指标类型: [月销售额 ▼]                      │ │
│  │                                              │ │
│  │  ┌───────────────────────────────────────┐   │ │
│  │  │ #│下限(¥) │上限(¥)  │比例(%)│封顶  │保底│   │ │
│  │  │ 1│0       │100,000 │3.0   │5,000 │2,000│   │ │
│  │  │ 2│100,000 │300,000 │5.0   │10,000│0    │   │ │
│  │  │ 3│300,000 │∞       │7.0   │20,000│0    │   │ │
│  │  │                              [+ 添加]  │   │ │
│  │  └───────────────────────────────────────┘   │ │
│  │  (实时校验提示：阶梯无重叠无断层 ✅)         │ │
│  └────────────────────────────────────────────┘ │
│                                                │
│  ┌─ 产品线覆盖（可选） ───────────────────────┐ │
│  │ 产品线        │比例(%)│封顶    │保底    │操作│ │
│  │ IC/主动器件   │3.0   │10,000 │0      │[×] │ │
│  │ 被动器件(RCL)│5.0   │10,000 │0      │[×] │ │
│  │                                   [+ 添加]│ │
│  └────────────────────────────────────────────┘ │
│                                                │
│  ┌─ 分配对象 ─────────────────────────────────┐ │
│  │ 分配给:                                     │ │
│  │  [角色: 销售经理 ▼] [+ 添加]                │ │
│  │  ● 张三 (sales)  ×                          │ │
│  │  ● 李四 (sales)  ×                          │ │
│  │  ● 角色: 销售经理 ×                        │ │
│  └────────────────────────────────────────────┘ │
│                                                │
│  [保存草稿] [激活方案]                           │
└────────────────────────────────────────────────┘
```

### 8.4 阶梯校验规则（前端实时）
- 每个阶梯的 `low` = 上一个阶梯的 `high`（自动填充）
- 修改 `low` 时联动调整上一个阶梯的 `high`
- 比例输入 `0–100`（前端显示为百分比，后端存小数）
- 封顶 ≥ 保底（输入时校验）
- 最后一行的上限默认显示 ∞

### 8.5 方案详情页

```
┌─ 方案详情: Q3 标准提成方案 ─────────────────┐
│                                               │
│  状态: ● 生效中  │ 版本: v3 │ 分配: 12 人     │
│  生效: 2026-07-01 │ 到期: 2026-09-30          │
│                                               │
│  ┌─ 阶梯可视化 ────────────────────────────┐  │
│  │  📊 [柱状图: 预估收入 vs 销售额阶梯]    │  │
│  │  横轴: 月销售额 (0–1000K)               │  │
│  │  纵轴: 提成金额                         │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌─ 阶梯明细 ─────────────────────────────┐  │
│  │ #│区间           │比例│封顶    │保底    │  │
│  │ 1│0 – ¥100,000  │3%  │¥5,000 │¥2,000  │  │
│  │ 2│¥100K–¥300K   │5%  │¥10K   │-       │  │
│  │ 3│≥ ¥300K       │7%  │¥20K   │-       │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌─ 分配对象 ─────────────────────────────┐  │
│  │  ● 张三 (sales)  ● 角色: 销售经理     │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  [编辑] [停用] [模拟] [版本历史]               │
└───────────────────────────────────────────────┘
```

### 8.6 方案模拟页

```
┌─ 提成方案模拟 ────────────────────────────┐
│                                            │
│  选择方案: [Q3 标准提成方案 ▼]              │
│  模拟期间: [📅 2026-04-01] ~ [📅 2026-06-30]│
│  [执行模拟]                                 │
│                                            │
│  ┌─ 汇总对比 ──────────────────────────┐   │
│  │ 旧方案总额: ¥125,000                 │   │
│  │ 新方案总额: ¥158,000  ▲ +26.4%      │   │
│  │ 影响人数: 3 / 12                     │   │
│  └─────────────────────────────────────┘   │
│                                            │
│  ┌─ 按销售员明细 ─────────────────────┐   │
│  │ 姓名│旧方案   │新方案   │差异    │标记│   │
│  │ 张三│¥50,000 │¥65,000 │+30% 🔴 │   │
│  │ 李四│¥40,000 │¥42,000 │+5%     │   │
│  │ 王五│¥35,000 │¥51,000 │+45% 🔴 │   │
│  │                     [导出 CSV]    │   │
│  └─────────────────────────────────────┘   │
└────────────────────────────────────────────┘
```

### 8.7 关键交互

| 操作 | UI | 反馈 |
|------|-----|------|
| 阶梯编辑 | 行内输入框（数字列自动千分位） | 失焦校验：重叠/断层实时提示 |
| 添加阶梯 | 底部 "+ 添加" 按钮 | 新行插入，low 自动填充上一个的 high |
| 删除阶梯 | 行末 "×" 按钮（仅可删除首尾） | 确认弹窗「删除后将合并区间」 |
| 分配用户 | 搜索式下拉 `<UserSelect>` | 多选，已选的显示 tag |
| 验证方案 | "检验阶梯" 按钮 | 后端校验返回结果（绿色/红色） |
| 方案模拟 | 选择方案+期间 → "执行模拟" | 加载中 Spin，完成后显示对比表 |

### 8.8 空/错/加载态
- 空：`<EmptyState description="还没有提成方案 — 点击「+ 新建方案」创建第一个" />`
- 加载：`<Spin>` 居中
- 阶梯校验失败：内联红色提示 "阶梯 2 的上限与阶梯 3 的下限不连续"
- 方案不可删除：toast "该方案已被佣金记录引用，无法删除"

---

## 9. 测试策略

### 9.1 单元测试（32 用例）

| 测试类 | 用例数 | 覆盖点 |
|--------|--------|--------|
| `TestTierValidation` | 8 | 无重叠校验、无断层校验、首尾边界、∞ 处理 |
| `TestTierCalculation` | 10 | 单阶梯、多阶梯、边界值、封顶截断、保底兜底 |
| `TestSchemeAssignment` | 6 | 用户级覆盖角色级、角色级覆盖默认、无方案降级 |
| `TestProductCategoryOverride` | 4 | 匹配产品线规则、不匹配回退默认 |
| `TestSchemeLifecycle` | 4 | draft→pending→active→expired 全流程 |

### 9.2 集成测试（15 用例）

| 用例 | 路径 | 期望 |
|------|------|------|
| 创建完整方案 | `POST /` | 201 + 自动 version_no=1 + 阶梯写入 |
| 阶梯重叠拒绝 | `POST /` 重叠阶梯 | 422 SCHEME_TIER_OVERLAP |
| 编辑方案 | `PUT /{id}` | 200 + 自动 version_no+1 |
| 激活方案 | `POST /{id}/activate` | 200 + status = active |
| 同一用户两方案 | 创建第二个 active 方案 | 409 SCHEME_ACTIVE_CONFLICT |
| 方案自动分配 | 分配用户后查询 `/my-scheme` | 返回正确方案 |
| 方案模拟 | `POST /simulate` | 200 + 对比数据 |
| 删除被引用方案 | `DELETE /{id}` | 409 SCHEME_REFERENCED |
| 过期扫描 | cron task | expired 标记正确 |

### 9.3 边界值测试

| 场景 | 输入 | 期望 |
|------|------|------|
| 销售额正好在阶梯边界 | 100,000 | 按第一档（左闭右开 `[0, 100000)`） |
| 封顶生效 | base=200,000, rate=5%, cap=5,000 → amount=5,000 | 5,000 |
| 保底生效 | base=10,000, rate=2%, floor=500 → amount=500 | 500 |
| 封顶 < 保底 | cap=1,000, floor=2,000 | 校验拒绝 |
| 多个产品线匹配 | 订单含 2 个产品线 | 各产品线按各自比例分别计算后相加 |
| 无分配方案 | 用户没有指定方案 + 无默认方案 | 使用系统硬编码兜底 3% |

### 9.4 验收清单

- [ ] 32 个单元测试通过
- [ ] 阶梯配置校验覆盖所有边界
- [ ] 方案模拟与手动计算结果一致
- [ ] Decimal 计算无浮点漂移
- [ ] 软删过滤全列表
- [ ] RBAC 种子含 `scheme.*` 5 项权限
- [ ] API 集成测试 15 用例通过
- [ ] `make lint` 通过（ruff + mypy + tsc）
- [ ] 过期 cron 扫描逻辑可测试（mock datetime）

---

## 附录 A：变更影响

### A.1 新增文件
- `backend/app/models/commission_scheme.py`
- `backend/app/schemas/commission_scheme.py`
- `backend/app/api/v1/finance/commission_schemes.py`
- `backend/app/services/commission_scheme_service.py`
- `backend/app/migrations/013-add-commission-schemes.sql`
- `backend/tests/test_commission_scheme.py`
- `frontend/src/pages/finance/CommissionSchemeList.tsx`
- `frontend/src/pages/finance/CommissionSchemeDetail.tsx`
- `frontend/src/ui/TierTable.tsx`
- `docs/requirements/013-commission-scheme-config.md`（本文件）

### A.2 修改文件
- `backend/app/models/finance.py`（可选：或独立 model 文件）
- `backend/app/schemas/finance.py`（+5+ schema）
- `backend/app/services/finance_service.py`（+commission 模块 v2）
- `backend/app/api/v1/finance/commissions.py`（计算逻辑改为从方案读取比例）
- `backend/app/api/v1/router.py`（+1 import +1 include）
- `backend/app/jobs/scheduler.py`（+ cron 扫描过期方案）
- `frontend/src/types/index.ts`（+方案相关类型）
- `frontend/src/api/finance.ts`（+API 调用）
- `frontend/src/App.tsx`（+路由）
- `frontend/src/layouts/MainLayout.tsx`（+菜单项）

### A.3 依赖
无新增。

### A.4 部署
1. 跑 migration `make db-migrate`
2. 重启后端
3. 前端 `npm run build`
4. RBAC：`scheme.*` 5 个权限授予 admin + finance_mgr

---

## 附录 B：与 012 的集成点

| 012 已有组件 | 013 改动 |
|-------------|---------|
| `Commission` 模型 | 新增 `scheme_snapshot` JSONB 字段（记录计算时的方案快照） |
| `commission_amount` 计算逻辑 | 从硬编码 `base * rate` 改为调用 `compute_commission()` 引擎 |
| 默认 `rate` | 从用户属性中移除，改为从方案中读取 |
| 批量审批 | 不变 |
| 仪表盘 | 新增「方案覆盖率」指标 |
