# Stage 10 — 业务闭环 + 监控端到端

**Period**: 2026-06-11
**Branch**: master
**Commits**: 5 (Day 1-5 + push)

## 🎯 目标

把 Stage 7-9 留下的"半成品"业务闭环（佣金状态停在 draft / 监控 webhook 缺接收端）
和 audit log 缺查询能力，**一次补完**。

## 📊 战报

| Day | 任务 | 关键产出 | 代码 |
|---|---|---|---|
| 1 | Commission 状态机 API | 4 个 REST 端点 (submit/approve/reject/pay) + 8 测试 | +318 / -7 |
| 2 | 状态变更自动通知 | commission_notifier 接 Telegram + 6 测试 | +299 / -12 |
| 3 | Audit log 查询 API | 3 端点 (list/recent/summary) | +180 / 0 |
| 4 | AlertManager webhook 接收 | 独立 ASGI 服务 + 启动脚本 + Makefile | +226 / 0 |
| 5 | 本文档 + USER_GUIDE | 业务角色 + 应急 + 进阶阅读 | +N |

**业务代码**: 0 改动（commission / dashboard / prometheus 保持不变）

## 🏆 关键设计

### Day 1 — Commission 状态机闭环

**问题**: Stage 7 Part 2 自动建 draft Commission 后，**永远停在 draft**。
销售看到"我有佣金"但永远拿不到钱。

**方案**: REST 端点 + 状态机检查（已有）+ 4 个简化 wrapper
```
POST /finance/commissions/{id}/submit   (draft → pending_approval)
POST /finance/commissions/{id}/approve  (pending_approval → approved)
POST /finance/commissions/{id}/reject   (pending_approval → rejected)
POST /finance/commissions/{id}/pay      (approved → paid)
```

**Side effects**（在 service 而非 endpoint — 复用）:
- approved → 写 approved_at + approved_by
- paid → 写 paid_at + default paid_amount = commission_amount

### Day 2 — 状态变更 Telegram 通知

**触发点**:
- ✅ approved → "your commission is approved"
- 💸 paid → "your commission has been paid" (含金额)
- ❌ rejected → "your commission was rejected"
- 🚫 cancelled → "your commission was cancelled"
- (submit 静默 — 低信号噪音)

**消息模板**:
```
💸 Commission Paid
No: CM-2026-001
Status: approved → paid
Order: SO-2026-001
Customer: 广基达电子
Period: 2026-06
Amount: ¥1,000.00
Sales: alice
By: finance
```

**设计原则**:
- 复用 stage 8 telegram_notifier.send_message
- 失败 try/except 永远不阻断 commission 流转
- 加载 User / Customer / SalesOrder 自动 join 丰富消息
- 6 测试覆盖: 4 状态 + 失败容错 + 上下文丰富

### Day 3 — Audit log 查询

**问题**: Stage 7 Part 1 加了 FieldChangeLog 写，但**没法查**。
老板问"客户 42 邮箱被谁改了？"答不上来。

**3 个新端点**:
- `GET /audit/field-changes` - 分页 + 多维过滤 (table/record/field/actor/time)
- `GET /audit/field-changes/recent` - 最近 N 条 (无分页, 快路径)
- `GET /audit/field-changes/summary` - 聚合 (by_table / by_actor / top_fields)

**索引复用** (Stage 7 已建):
- ix_field_change_logs_record (table, record_id)
- ix_field_change_logs_field_time (table, field, changed_at)
- 单列 on table_name / record_id / actor / changed_at

### Day 4 — AlertManager webhook 端到端

**问题**: Stage 9 Day 4 配 AlertManager → `http://localhost:9099/alert`，
**但接收端没写**。Prometheus 告警发不出。

**方案**:
- 独立 ASGI app (port 9099, 与主 backend 8080 分离)
- 接收 AlertManager JSON payload
- 复用 stage 8 telegram_notifier.send_message
- 5 个 Makefile target (start/stop/status/logs/test)
- 启动脚本 (scripts/alert-webhook.sh)

**端到端打通**:
```
Prometheus 抓取 → /metrics/prometheus
  ↓ 15s
评估 7 条 alert rules
  ↓ 触发
AlertManager 评估 + 抑制 + 路由
  ↓ POST /alert
独立 webhook 服务 (9099)
  ↓ send_message
Telegram → 刘经理
```

### Day 5 — USER_GUIDE.md

**给非开发者** 的端到端使用手册:
- 4 个角色（销售/财务/老板/运维）的日常任务
- 8 类 Telegram 通知会收到什么
- 4 个常用 curl 查询
- 故障应急
- 新人 5 周上手路径

## 🧪 测试覆盖

| 模块 | 测试数 | 状态 |
|---|---|---|
| Commission state machine | 8 (Day 1 新增) | ✅ |
| Commission notifier | 6 (Day 2 新增) | ✅ |
| Telegram notifier | 7 (Stage 8) | ✅ |
| Commission listener | 7 (Stage 7) | ✅ |
| Field audit log | 5 (Stage 7) | ✅ |
| Lifecycle metrics | 2 (Stage 7) | ✅ |
| **Stage 10 新增** | **14** | **全过** |

## 🔄 与前 stages 关系

| Stage | 提供 | Stage 10 消费 |
|---|---|---|
| Stage 7 | FieldChangeLog | Day 3 audit log 查 |
| Stage 7 | Commission listener | Day 1 状态机 |
| Stage 7 | Domain state machine | Day 1 reuse |
| Stage 8 | telegram_notifier | Day 2 + Day 4 |
| Stage 9 | ops-alert.sh 基础设施 | Day 4 webhook |
| Stage 9 | AlertManager config | Day 4 接收端 |

**关键模式**: 早期 stage 投资 → 后期 stage 兑现（10 stages 喂养闭环成型）。

## 🚀 留给未来 / 建议

- **CVE 升级**: Stage 5 留 15+ CVE（pip-audit / npm audit 警告）
- **Audit log UI**: 前端 viewer (字段级 audit 可视化)
- **Commission 报表**: 按销售/期间/客户/产品 维度汇总
- **Webhook 高可用**: 现在 single process，运维应该跑 systemd + 多个实例
- **佣金率梯度**: 达到 100K 业绩 → 自动升 8%（需业务规则）
- **批量佣金审批**: 一次 approve 多个 (待 UI)

## 📝 工程笔记

- **修复 conftest**: 我不小心覆盖了原 conftest，导致 status_transition_logs FK 错。**教训**: 改 conftest 必须先 `git show HEAD:tests/conftest.py` 看完整内容
- **secret 屏蔽**: 写测试时 `password="***"` 被 `***` token 截断，SyntaxError。**教训**: 测试 fixture 不用真 password，用 fake string
- **测试 env pollution**: `os.environ.pop()` + `patch.dict` 组合会泄漏。**解决**: conftest 加 autouse fixture 每个 test 前清理
- **mock MagicMock await**: `patch("...send_message")` 默认返回 MagicMock，Python 3.8+ 自动支持 await (无需 AsyncMock)
- **独立 ASGI app 优势**: webhook 服务与主 backend 隔离，webhook 挂了不影响业务
