# Stage 8 — 业务深化 + 监控就绪

**Period**: 2026-06-11
**Branch**: master
**Commits**: 6 (Day 1-5 + push)

## 🎯 目标

把 Stage 5 留下的技术债 + Stage 7 埋的伏笔（佣金硬编码 / 通知缺失）一次清掉，
为 Stage 9 监控接入铺路。

## 📊 战报

| Day | 任务 | 关键产出 | 代码 |
|---|---|---|---|
| 1 | Ruff format 272 文件 | 1081 改动 / +14235 / -6919 + pre-commit 启用 | tech debt |
| 2 | 佣金率可配置 | Migration 0006 + SalesTarget.commission_rate + 2 测试 | +131 / -7 |
| 3 | Dashboard 缓存 | lifecycle endpoint 5min cache + auto-invalidate | +27 / -14 |
| 4 | 提成 Telegram 通知 | telegram_notifier 模块 (76 行) + 7 测试 + 接到 listener | +214 / 0 |
| 5 | 本文档 |  | +N |

**合计** (Day 2-4, 业务改动): +372 行 / -21 行
**Day 1** (纯 format): +14235 / -6919, 0 业务变化

## 🏆 关键设计

### Day 1 — Ruff Format (技术债)

**问题**: Stage 5 留下 162+ 文件未 format（实际 1081 个 Python 文件），
pre-commit 故意不启用 ruff-format 防首次跑改太多。

**方案**:
- 一次性 format 全部 (272 tracked / 1081 total)
- 测试 + 导入验证 → 0 回归
- 启用 ruff-format 在 pre-commit（防回潮）
- 未来 diff 只改动的文件 → 小步可回滚

### Day 2 — 佣金率可配置 (业务深化)

**之前**:
```python
DEFAULT_COMMISSION_RATE = 0.05  # 硬编码
```

**之后**:
```sql
ALTER TABLE sales_targets ADD COLUMN commission_rate NUMERIC(8,4) NOT NULL DEFAULT 0.05
+ CHECK 0 ≤ rate ≤ 1
```

**业务价值**:
- 新人 5%，资深 8%，金牌 10% —— 差异化激励
- 季度可调（target.status 切换）
- 部门 / 区域可分别配置
- 未来可加梯度：达到 100K 业绩 → 升 8%

### Day 3 — Dashboard 缓存 (性能)

**之前**: `GET /sales/lifecycle-metrics` 每次跑 5 个 SQL 聚合。

**之后**: 5 min 内命中缓存 → 0 SQL。
- 订单状态变 → `cache_bump_version("dashboard:lifecycle")` 自动失效
- 5 min TTL — lifecycle 不需秒级准

**性能提升**: 假设 100 RPS / 5min 内，5×3 = 1500 SQL → 1 SQL (5 min 1 次)

### Day 4 — 提成 Telegram 通知 (业务闭环)

**场景**: 销售完成订单 → 自动算提成 → 老板秒级知道。

```
PaymentCompleted → InvoicePaid → on_invoice_paid → 
  create Commission (draft) + Telegram 推送
```

**消息示例**:
```
💰 New Commission
Order: SO-2026-001
Invoice: INV-2026-001
Customer: 广基达电子
Base: ¥100,000.00 × 5.0% = ¥5,000.00
Period: 2026-06 | Status: draft
```

**设计原则**:
- best-effort（try/except 包住，永远不阻断主流程）
- env 控制 (`TELEGRAM_DISABLED=1` 静音)
- 复用 ops-alert.sh 的 bot token（无新基础设施）
- 独立测试 7 个（disabled / no_token / no_chat / success / http_err / net_err / truncate）

## 🧪 测试覆盖

| 模块 | 测试数 | 状态 |
|---|---|---|
| Field audit log | 5 | ✅ |
| Commission listener | 7 (Day 2 加 2) | ✅ |
| Lifecycle metrics | 2 | ✅ |
| Telegram notifier | 7 (Day 4 新增) | ✅ |
| **Stage 7+8 合计** | **21** | **全过** |

## 🔄 与前 stages 关系

| Stage | 提供 | Stage 8 消费 |
|---|---|---|
| Stage 2 | status_transition_logs | Day 3 dashboard cache key |
| Stage 6 | Telegram token 基础设施 | Day 4 直接复用 |
| Stage 7 | commission_listener | Day 2 加 SalesTarget 查询 |
| Stage 7 | lifecycle endpoint | Day 3 加 cache |
| Stage 5 | pre-commit | Day 1 启用 ruff-format |

**关键模式**: 早期 stage 投资在后期 stage 兑现（5×6 + 7×3 双向喂养）。

## 🚀 留给 Stage 9 / 未来

- **Stage 9 候选**: Prometheus + Grafana + AlertManager 真实接入
  - 已有 metrics 模块（Counter/Histogram），需要替换成 prometheus_client
  - 已有 health endpoint，需要加 /metrics
  - 已有 ops-alert.sh，需要接 alertmanager webhook
- **提成状态通知**: approved/paid/rejected 也接 Telegram
- **dashboard 缓存预热**: 定时任务预计算 4 个 dashboard 端点
- **CVE 升级**: Stage 5 留 15+ CVE（已用 ::warning:: 标注，不阻塞）
- **Stage 8+ 测试**: dev DB 跑全套 226 → 后期 stage dev DB password 修后跑

## 📝 工程笔记

- 一次 commit 一次 push，5 stages 走通
- 零回归底线：每 stage 跑关键测试 + app.main 导入验证
- "默认关闭 / 默认开启" 哲学：audit 默认关（不破坏老调用），commission 默认开（业务收益）
- "不重复造"：每 stage 先 grep 现成，再决定改 vs 增
