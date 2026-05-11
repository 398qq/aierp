# 004 — Phase 6: 财务增强 + 消息通知 + 移动适配 + 数据集成

## 1. 概述

Phase 6 在 Phase 5 审批流/RBAC/报表基础上，完善财务管理能力，引入多渠道消息通知，适配移动端，打通外部数据源。覆盖 4 个子模块：**F(财务增强)**、**G(消息通知)**、**H(移动适配)**、**I(数据集成)**。

## 2. 目标

| 目标 | 衡量标准 |
|------|---------|
| 财务核算闭环 | 支持凭证录入、银行对账、利润分析 |
| 消息触达 | 审批/预警/日报通过邮件+企业微信推送 |
| 移动端可用 | 核心页面（列表+详情+审批）适配移动浏览器 |
| 外部数据接入 | 对接至少 1 个电商平台或物流 API |

## 3. 用户故事

- 财务人员：录入收支凭证，月末自动生成损益表，银行流水一键对账
- 销售经理：在手机上审批报价单，收到新商机微信通知
- 总经理：每天早上收到经营日报邮件，包含销售额/回款/库存预警
- 运营人员：从淘宝/1688 同步订单和评价数据到 ERP

## 4. 功能需求

### F — 财务增强

| 功能 | 说明 |
|------|------|
| F1 会计科目 | 预设科目表（资产/负债/权益/收入/费用），支持二级科目 |
| F2 记账凭证 | 凭证录入（借方/贷方），自动校验借贷平衡，凭证号自动生成 |
| F3 银行对账 | 导入银行流水 CSV，自动匹配 ERP 收付款记录，标记差异 |
| F4 损益表 | 月度 P&L：收入合计 - 成本合计 - 费用合计 = 净利润 |
| F5 资产负债表 | 期末资产/负债/权益汇总 |
| F6 应收账龄 | 增强版 AR 报表（已在 Phase 5 实现基础版）— 支持催款提醒 |
| F7 应付账款 | AP 报表：按供应商统计应付金额和账龄 |

### G — 消息通知

| 功能 | 说明 |
|------|------|
| G1 通知渠道 | 站内通知（已有）、邮件（SMTP）、企业微信 Webhook |
| G2 通知模板 | 可配置模板：审批请求、审批结果、预警通知、日报摘要 |
| G3 触发规则 | 审批提交→通知审批人；审批完成→通知提交人；库存预警→通知仓库 |
| G4 日报推送 | 每日 8:00 自动生成并推送经营日报到配置的邮箱/企微群 |
| G5 通知偏好 | 用户可配置接收哪些通知、通过哪个渠道 |

### H — 移动适配

| 功能 | 说明 |
|------|------|
| H1 响应式布局 | Ant Design 已有基础响应式，优化列表页在小屏的展示（卡片替代表格） |
| H2 移动端审批 | 审批列表 + 审批详情 + 通过/驳回 适配移动端操作 |
| H3 移动端看板 | 核心 KPI 卡片适配手机竖屏 |
| H4 PWA | 添加 manifest.json + service worker，支持添加到主屏幕 |

### I — 数据集成

| 功能 | 说明 |
|------|------|
| I1 电商订单导入 | 从 CSV/API 导入淘宝/1688 订单，自动创建客户+销售订单 |
| I2 物流轨迹 | 对接快递鸟/菜鸟 API，查询运单物流轨迹 |
| I3 数据导出增强 | 所有列表页支持 Excel 导出（带筛选条件） |
| I4 Webhook 回调 | 支持外部系统通过 Webhook 推送数据到 ERP |

## 5. 非功能需求

- 邮件发送异步化，不阻塞 API 响应
- 移动端首屏加载 < 3s（4G 网络）
- 银行对账支持单次导入 10000 条流水
- 通知发送失败重试 3 次，失败后记录日志

## 6. 数据模型

### 新表

| 表名 | 关键字段 | 说明 |
|------|---------|------|
| `accounts` | code, name, type(asset/liability/equity/income/expense), parent_id | 会计科目 |
| `journal_entries` | entry_no, date, description, status(draft/posted) | 记账凭证头 |
| `journal_entry_lines` | entry_id, account_id, debit, credit, description | 凭证行 |
| `bank_reconciliations` | payment_id, bank_txn_id, match_type(auto/manual), difference | 银行对账 |
| `notification_templates` | code, name, channel, subject_template, body_template | 通知模板 |
| `notification_preferences` | user_id, event_type, channel, enabled | 用户通知偏好 |
| `integration_configs` | type, name, api_key, endpoint, enabled | 外部集成配置 |

### 修改表

| 表名 | 变更 |
|------|------|
| `notifications` | 添加 `channel`, `template_code`, `external_id` 字段 |
| `purchase_orders` | 添加 `logistics_no`, `logistics_provider` 字段 |

## 7. API 设计

### 财务

| Method | Path | 说明 |
|--------|------|------|
| GET/POST/PUT/DELETE | `/api/v1/accounts` | 会计科目 CRUD |
| GET/POST/PUT | `/api/v1/journal-entries` | 凭证列表/创建/更新 |
| GET | `/api/v1/journal-entries/{id}` | 凭证详情（含行项目） |
| POST | `/api/v1/journal-entries/{id}/post` | 过账 |
| POST | `/api/v1/bank/reconcile` | 上传银行流水对账 |
| GET | `/api/v1/reports/pnl` | 损益表 |
| GET | `/api/v1/reports/balance-sheet` | 资产负债表 |
| GET | `/api/v1/reports/ap` | 应付账款报表 |

### 通知

| Method | Path | 说明 |
|--------|------|------|
| GET/PUT | `/api/v1/notifications/preferences` | 通知偏好 |
| GET/POST/PUT/DELETE | `/api/v1/notifications/templates` | 通知模板 CRUD |
| POST | `/api/v1/notifications/test` | 发送测试通知 |

### 集成

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/integrations/orders/import` | 导入外部订单 |
| GET | `/api/v1/integrations/logistics/{tracking_no}` | 查询物流轨迹 |
| POST | `/api/v1/integrations/webhook/{source}` | 接收外部 Webhook |
| GET/POST/PUT/DELETE | `/api/v1/integrations/configs` | 集成配置管理 |

## 8. UI/UX 设计

### 财务模块

- **科目表**：树形表格，资产/负债/权益/收入/费用五大类
- **凭证录入**：表头（日期/摘要）+ 动态行（科目选择器/借方金额/贷方金额），实时显示借贷差额
- **银行对账**：左侧银行流水列表，右侧 ERP 收付款列表，中间匹配/差异标记
- **损益表**：月度收入/成本/费用/利润汇总，支持月份切换和同比对比

### 移动端

- 列表页在小屏切换为卡片列表（一行一卡）
- 审批操作按钮固定底部，大按钮便于拇指操作
- 侧边栏改为底部 TabBar（仅移动端）

## 9. 测试策略

| 场景 | 测试方法 |
|------|---------|
| 凭证借贷不平衡 | 自动化：提交不平衡凭证应返回 400 |
| 银行对账自动匹配 | 自动化：同名+同金额+同日期±3天应自动匹配 |
| 邮件发送失败重试 | 自动化：Mock SMTP 返回错误，验证重试 3 次 |
| 移动端审批操作 | 手动：Chrome DevTools 模拟 iPhone 14 |
| 电商订单导入 | 自动化：上传标准 CSV，验证客户+订单创建 |
| 物流 API 超时 | 自动化：Mock 超时，验证降级处理 |
