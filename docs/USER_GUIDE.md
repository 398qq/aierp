# AIERP 用户手册

**目标读者**: 销售 / 财务 / 老板 / 运维
**版本**: master (Stage 10)
**最后更新**: 2026-06-11

---

## 🎯 系统是什么

AIERP = AI + ERP，是一套**业务自动化系统**：
- 客户管理（CRM）
- 销售跟单（订单状态机 + 转化率监控）
- 库存 + 采购
- 财务（发票 / 付款 / 合同 / **佣金自动**）
- 报表 + Dashboard
- 业务监控 + Telegram 通知

---

## 👥 角色与日常任务

### 销售 (Sales)

| 任务 | 路径 | 频率 |
|---|---|---|
| 录入新客户 | CRM → 客户 → 新建 | 每天 |
| 创建报价 | CRM → 客户 → 报价单 → 新建 | 每天 |
| 跟进客户 | CRM → 客户 → 跟进 | 每天 |
| 确认订单 | 销售 → 订单 → 确认 | 每天 |
| 完成订单 | 销售 → 订单 → 完成 → 上传发货单 | 订单交付时 |
| 查自己佣金 | 财务 → 佣金 → 筛选(销售=我) | 每周 |

**Stage 7-10 自动化**:
- 客户付款 → **自动**算出你的佣金（默认 5%）
- 你的佣金被**批准** → Telegram 通知你
- 你的佣金**发放** → Telegram 通知你（带金额）

### 财务 (Finance)

| 任务 | 路径 | 频率 |
|---|---|---|
| 录入收款 | 财务 → 付款 → 新建 → 关联发票 | 每天 |
| 审批发票 | 财务 → 发票 → 待审批 | 每天 |
| 审批佣金 | 财务 → 佣金 → 待审批 | 每周 |
| 标记佣金发放 | 财务 → 佣金 → 已批准 → 标记已付 | 月度 |
| 查提成汇总 | 财务 → 佣金 → 筛选(期间=本月) | 每月 |

**自动化**:
- 发票付款完成 → 自动算销售佣金（5% 默认，可按人配）
- 状态机: `draft → pending_approval → approved → paid`
- 4 个 REST 端点: `/submit` `/approve` `/reject` `/pay`

### 老板 / 管理 (Owner)

| 任务 | 路径 | 频率 |
|---|---|---|
| 看月营收 | Dashboard → 月营收 | 每天 |
| 看跟单健康度 | Dashboard → 跟单指标 | 每天 |
| 查谁改了客户 | 审计 → 字段变更 → 筛客户 | 出问题时 |
| 查最近 1h 异常 | 收 Telegram 告警 | 实时 |
| 月度业务回顾 | Dashboard → 跟单指标 + 佣金 | 月度 |

**关键指标**:
- `month_revenue` (本月营收)
- `cancellation_rate_pct` (订单取消率，>30% 警告)
- `avg_time_to_confirm_hours` (平均确认时间，越短越好)
- `stage_conversion_pct` (PENDING → COMPLETED 转化率)

### 运维 (Ops)

| 任务 | 路径 | 频率 |
|---|---|---|
| 健康检查 | `make health-check` | 每天 |
| 备份 | `make db-backup` + cron | 每天 |
| 告警测试 | `make ops-alert` | 每周 |
| 看监控 | Grafana → AIERP Business | 实时 |
| 启动 webhook | `make alert-webhook-start` | 部署时 |

---

## 🆕 新功能速览（最近 4 stages）

### Stage 7 — 业务深化
- **字段级 audit log**: 谁改了客户邮箱？查 `/audit/field-changes?table=customer&record=42`
- **佣金自动计提**: 客户付款 → 自动算 5% 销售佣金
- **Dashboard 跟单指标**: `/sales/lifecycle-metrics` 看停留/取消/转化

### Stage 8 — 业务深化 + 监控就绪
- **佣金率可配置**: 每个销售不同提成率（在 SalesTarget 设）
- **Dashboard 缓存**: 高频访问 5min 内 0 SQL
- **佣金创建通知**: 销售秒级收到 Telegram

### Stage 9 — Prometheus 监控
- **8 个 Grafana 面板**: 订单速率 / AI 延迟 / 缓存命中率 / 内存
- **7 条告警规则**: 订单取消率 / AI 错误率 / 内存 / 零订单
- **/metrics/prometheus**: Prometheus 标准抓取

### Stage 10 — 业务闭环
- **Commission 状态机**: draft → pending → approved → paid (4 个 REST 端点)
- **状态变更自动通知**: 批准/发放/拒绝/取消 → Telegram
- **Audit log 查询 API**: 3 个端点 (list/recent/summary)
- **AlertManager 端到端**: Prometheus → webhook → Telegram

---

## 📱 Telegram 通知（你会收到什么）

| 事件 | 频率 | 严重度 | 消息示例 |
|---|---|---|---|
| 备份失败 | 每天 | ⚠️ | "Latest backup is 411h old" |
| 磁盘满 | 每天 | ⚠️ | "Disk 92% used" |
| 订单取消率 > 30% | 实时 | ⚠️ | "Cancellations exceeding 30%" |
| AI 错误率 > 10% | 实时 | 🚨 | "AI error rate > 10%" |
| 1h 零订单 | 实时 | 🚨 | "No orders confirmed in 1h" |
| 你的佣金被批准 | 实时 | ✅ | "Commission Approved ¥1,000" |
| 你的佣金被发放 | 实时 | 💸 | "Commission Paid ¥1,000" |
| 你的佣金被拒 | 实时 | ❌ | "Commission Rejected" |

---

## 🔑 常用查询

### "客户 X 最近 1 个月谁改了什么？"
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/audit/field-changes?table_name=customer&record_id=42&days_back=30"
```

### "这个月发了多少佣金？"
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/finance/commissions?period=2026-06&status=paid"
```

### "过去 7 天跟单健康度？"
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/sales/lifecycle-metrics?days_back=7"
```

### "本月新客户？"
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/sales/dashboard/overview"
```

---

## 🚨 故障 / 应急

### 备份失败
```bash
make health-check    # 看具体哪挂了
make db-backup       # 手动备份
ls -la ~/date/       # 看历史备份
```

### Prometheus 告警风暴
```bash
make alert-webhook-stop   # 暂停 Telegram 转发
# 修 Prometheus 配置 / ops/prometheus/alerts.yml
make alert-webhook-start  # 恢复
```

### 业务挂了
```bash
make prod-status
make prod-logs
make prod-restart
```

### Telegram bot token 失效
1. 找 @BotFather 要新 token
2. `export TELEGRAM_BOT_TOKEN=***`
3. `systemctl restart aierp-alert-webhook` 或 `make alert-webhook-restart`
4. 测：`make ops-alert` / `make alert-webhook-test`

---

## 📚 进阶阅读

- `OPS.md` — 日常运维 (备份 / Docker / 告警)
- `MONITORING.md` — Prometheus + Grafana 部署 + PromQL
- `ARCHITECTURE.md` — 整体架构
- `STAGE1.md` ~ `STAGE10.md` — 渐进式开发历程
- `FRONTEND_HOOKS.md` — 前端架构
- `CI.md` — CI/CD 流程
- `MIGRATIONS.md` — 数据库迁移

---

## 💡 给新人的上手路径

1. **第 1 天**: 看 `ARCHITECTURE.md` + `USER_GUIDE.md` (本文)
2. **第 2-3 天**: 跑 dev 环境 (`make dev-start`)，点一遍 UI
3. **第 4-5 天**: 看 `STAGE2.md` (跟单状态机) + `STAGE7.md` (佣金)
4. **第 2 周**: 看 `OPS.md` + `MONITORING.md` 理解运维
5. **第 3 周起**: 接需求 / 改代码
