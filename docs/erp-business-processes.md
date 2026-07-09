# AIERP 业务流程手册

> 版本: 2.0 | 2026-06-22 | 适用对象: 中小型电子元器件贸易企业

---

## 1. 销售全流程 (Lead-to-Cash)

### 1.1 流程总览

```
询价 → 商机 → 报价 → 订单 → 发货 → 发票 → 收款
  │       │      │      │      │      │      │
  │       │      │      ├─合同─┤      │      │
  │       │      │      │      ├─退货─┤      │
  │       │      │      │      │      ├─冲红─┤
  ↓       ↓      ↓      ↓      ↓      ↓      ↓
 客户生命周期状态自动流转
```

### 1.2 各环节详解

#### 1.2.1 询价 (Inquiry)

| 属性 | 说明 |
|------|------|
| **触发** | 客户通过 Web/微信/邮件/API 提交产品咨询 |
| **角色** | 销售助理 |
| **AI 辅助** | `InquiryAutoReply` — 自动匹配产品、生成回复草稿 |
| **出口** | 转为报价单或标记为"已回复" |

**状态流转**: `pending → replied → converted`

#### 1.2.2 商机 (Opportunity)

| 属性 | 说明 |
|------|------|
| **触发** | 销售发现潜在客户需求，或询价转化 |
| **角色** | 销售经理 |
| **AI 辅助** | 商机评分、赢单概率预测、推荐行动 |
| **出口** | 赢单 → 创建报价；输单 → 记录原因 |

**状态流转**: `active → won | lost`（lost 可重新激活为 active）

#### 1.2.3 报价 (Quotation)

| 属性 | 说明 |
|------|------|
| **触发** | 商机赢单后，客户要求正式报价 |
| **角色** | 销售经理 |
| **AI 辅助** | 报价健康度检查、风险条款识别、验证报价→订单转换 |
| **产出** | PDF 报价单（ReportLab 生成） |
| **出口** | 客户接受 → 转销售订单 |

**状态流转**: `draft → sent → accepted → won`（可 rejection/expiry 终止）

#### 1.2.4 销售订单 (SalesOrder)

| 属性 | 说明 |
|------|------|
| **触发** | 报价被接受后转订单，或客户直接下单 |
| **角色** | 销售经理/销售助理 |
| **AI 辅助** | 订单交付风险评估 |
| **关键动作** | 确认订单自动锁库存、转发货、关联合同 |
| **产出** | PDF 销售订单、库存预留 |

**状态流转**: `pending → confirmed → shipped → delivered → completed | cancelled`

#### 1.2.5 发货单 (DeliveryNote)

| 属性 | 说明 |
|------|------|
| **触发** | 销售订单确认后创建发货单 |
| **角色** | 仓库管理员 |
| **关键动作** | 发货时自动扣减库存（shipped/delivered/completed）、标记收款 |
| **出口** | 发货完成 → 转发票/退货单 |

**状态流转**: `pending → shipped → delivered | cancelled`

**转换端点**:
- `POST /sales-orders/{id}/convert-to-delivery` — 订单转发货（自动 pending→confirmed）
- `POST /delivery-notes/{id}/convert-to-invoice` — 发货转发票
- `POST /delivery-notes/{id}/convert-to-return` — 发货转退货
- `POST /delivery-notes/{id}/mark-paid` — 标记收款

#### 1.2.6 发票 (Invoice)

| 属性 | 说明 |
|------|------|
| **触发** | 发货完成后生成发票 |
| **角色** | 财务人员 |
| **关键字段** | 金额、税额（默认 13%）、到期日 |
| **出口** | 收款核销 |

**状态流转**: `draft → sent → paid | overdue → paid | cancelled`

#### 1.2.7 收款 (PaymentRecord)

| 属性 | 说明 |
|------|------|
| **触发** | 客户付款后记录 |
| **角色** | 财务人员 |
| **关联** | 销售订单 + 发货单 + 发票 |

**状态流转**: `pending → completed | overdue → completed`

---

### 1.3 退货与冲红流程

```
发货(delivered) → 退货(approved) → 完成(completed) → 冲红发票(issued)
                                            ↓
                                     库存回退 + 负金额冲抵
```

| 端点 | 说明 |
|------|------|
| `POST /delivery-notes/{id}/convert-to-return?reason=xxx` | 创建退货单 |
| `POST /return-notes/{id}/complete` | 完成退货 + 自动冲红 |

**CreditNote 状态流转**: `draft → issued | cancelled`

---

### 1.4 合同管理 (Contract)

| 属性 | 说明 |
|------|------|
| **关联** | 客户 + 销售订单 |
| **关键日期** | 签署日期、到期日期 |
| **调度任务** | 到期前 30 天自动提醒 |
| **AI 辅助** | 条款提取、风险评估、返利跟踪 |

**状态流转**: `draft → signed → active → expired | terminated | cancelled`

---

## 2. 采购全流程 (Purchase-to-Pay)

```
采购需求 → 采购单 → 收货单 → 质检 → 入库 → 供应商发票 → 付款
```

### 2.1 采购单 (PurchaseOrder)

| 状态流转 | `draft → approved → ordered → partially_received → received | cancelled` |
|----------|-----------|
| **AI 辅助** | 自动建议采购量、风险评估、供应商优化 |

### 2.2 收货单 (GoodsReceipt)

| 状态流转 | `received → inspected → accepted | rejected`（rejected 可重新 received）|
|----------|-----------|

### 2.3 供应商发票 (SupplierInvoice)

| 状态流转 | `pending → matched → approved → paid | cancelled` |
|----------|-----------|
| **三方匹配** | 采购单金额 ↔ 收货单数量 ↔ 供应商发票金额 |

---

## 3. 库存管理

### 3.1 库存变动追踪

| 事件 | 方向 | 触发点 |
|------|------|--------|
| 订单确认 | **锁定** | `lock_for_sales_order()` — 预留库存 |
| 发货完成 | **扣减** | `deduct_for_delivery()` — shipped/completed/delivered |
| 退货完成 | **回退** | 退货单 completed → 库存恢复 |
| 采购收货 | **增加** | GoodsReceipt accepted → 库存增加 |

### 3.2 批次管理

- 批次号自动生成（收货时）
- 支持手动入库批次号
- 批次成本追踪（先进先出）

---

## 4. 财务管理

### 4.1 科目表 (Chart of Accounts)

```
资产类 / 负债类 / 权益类 / 收入类 / 费用类
```

### 4.2 佣金管理 (Commission)

```
draft → pending_approval → approved → paid | rejected → draft（重提）
```

- 支持批量审批
- 按用户/周期配置费率

### 4.3 提成方案 (Commission Scheme)

- 按产品/客户/销售额阶梯配置
- 自动到期提醒（7 天前）+ 自动过期（调度每日 02:05）

### 4.4 销售目标 (SalesTarget)

- 月度/季度目标设定
- 实际 vs 目标进度跟踪

---

## 5. 客户生命周期

### 5.1 客户 7 状态自动流转

```
new_lead(新潜客) → active(活跃) → converted(已成交) → vip(VIP)
                          ↓                ↓              ↓
                       inactive(不活跃) ←──┴──────────────┘
                          ↓
                       churned(流失) → active(重新激活)
```

| 转换规则 | 触发条件 | 频率 |
|----------|---------|------|
| new_lead → active | 创建首个商机 | 实时 |
| active → converted | 完成首个订单 | 实时 |
| converted → vip | 12 月交易 > ¥500,000 | 每日 02:00 |
| active/converted → inactive | 最后互动 > 90 天 | 每日 02:00 |
| inactive → active | 重新互动 | 实时 |
| any → churned | 手动标记流失 | 手动 |

### 5.2 客户 360° 视图

- RFM 分析（最近/频率/金额）
- 流失预测
- 产品匹配推荐
- 跟进记录 + 提醒

---

## 6. 数据分析与 AI 智能

### 6.1 AI 增强点（覆盖全流程）

| 模块 | AI 能力 |
|------|--------|
| 商机 | 评分、赢单预测、推荐行动 |
| 报价 | 健康度检查、风险识别、转订单验证 |
| 订单 | 交付风险评估 |
| 合同 | 条款提取、风险评级、到期扫描、返利跟踪 |
| 发票 | 发票到期跟踪 |
| 采购 | 自动建议采购量、风险评估、供应商优化 |
| 客户 | RFM 分析、流失预测、自动回复 |
| 看板 | 跨领域异常检测（Watchtower） |

### 6.2 定时任务（APScheduler）

| 任务 | 频率 | 说明 |
|------|------|------|
| 销售洞察刷新 | 每 6h | AI 重新分析销售数据 |
| 逾期提醒 | 每 12h | 发票/收款逾期告警 |
| 目标进度 | 每 24h | 销售目标 vs 实际进度 |
| 合同到期 | 每 24h | 合同到期扫描 |
| 嵌入刷新 | 每 24h | 重新生成向量嵌入 |
| 看板扫描 | 每 4h | 跨域异常检测 |
| 客户洞察 | 每 24h | 客户 AI 分析 |
| 日报 | 每日 18:00 | 销售日报 |
| 通知清理 | 每 24h | 清理旧通知 |
| 客户状态 | 每日 02:00 | 客户生命周期自动流转 |
| 提成到期 | 每日 02:05 | 方案到期 + 7天提醒 |

---

## 7. 权限体系 (RBAC)

| 角色 | 典型权限 |
|------|---------|
| **admin** | 全部权限 |
| **sales** | 客户/商机/报价/订单/发货/合同 读写 |
| **warehouse** | 库存/收货/发货 读写 |
| **finance** | 发票/收款/付款/账务 读写 |
| **viewer** | 全部只读 |

权限粒度: `resource.action`（如 `customers.write`、`finance.read`）

---

## 8. 技术架构关键指标

| 指标 | 值 |
|------|-----|
| API 端点数 | 200+ |
| 状态机 | 16 个实体，全覆盖 |
| 状态机测试 | 157 个单元测试 |
| 集成测试 | 1250+ 通过 |
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存 | Redis 7 (versioned cache) |
| AI 提供商 | SiliconFlow (DeepSeek-V4) |
| 前端 | React 19 + Ant Design 6 + Zustand 5 |
