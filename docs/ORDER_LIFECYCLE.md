# 跟单全流程状态机（Stage 2, 2026-06-11）

## 目标

把"一笔单子从入口到回款"做成**6 状态机 + 跨表自动对账 + 完整审计**，让改一处只改一处、谁动了什么时候一目了然。

## 6 个状态机

| 聚合 | 状态数 | 文件 | Stage 2 改 | 测试 |
|---|---|---|---|---|
| **Quotation** 报价 | 6 | `domain/sales/quotation.py` | ✅ v1 已完整 | 已存在 |
| **SalesOrder** 订单 | 5 | `domain/sales/order.py` | 🆕 **新增 v2** | 20 测试 |
| **DeliveryNote** 发货单 | 4 | `domain/sales/delivery.py` | ✅ v1 已完整 | 已存在 |
| **Invoice** 发票 | 4 | `domain/sales/invoice.py` | 🆕 **新增 v2** | 24 测试 |
| **PaymentRecord** 付款 | 4 | `domain/sales/payment.py` | 🆕 **新增 v2** | 同上 |
| **Commission** 佣金 | draft/active | (Stage 2 之外) | ❌ 不动 | - |

## 状态图

```
                    ┌──────────────────────────────────────────┐
                    │  Pre-Sales                               │
                    │  Opportunity → Quotation (DRAFT/SENT)    │
                    └──────────────────────────────────────────┘
                                       │  accept
                                       ▼
                    ┌──────────────────────────────────────────┐
                    │  Sales                                   │
                    │  Quotation ACCEPTED → SalesOrder PENDING │
                    └──────────────────────────────────────────┘
                                       │  confirm
                                       ▼
                    ┌──────────────────────────────────────────┐
                    │  Fulfillment                             │
                    │  SalesOrder CONFIRMED → SHIPPED          │
                    │  + DeliveryNote DRAFT → SHIPPED          │
                    │  （发货时扣库存，订单 shipped）             │
                    └──────────────────────────────────────────┘
                                       │  invoice + complete
                                       ▼
                    ┌──────────────────────────────────────────┐
                    │  Finance                                 │
                    │  Invoice DRAFT → ISSUED → PAID           │
                    │  PaymentRecord PENDING → COMPLETED       │
                    │  （付款完成时自动驱动 invoice 到 PAID）     │
                    └──────────────────────────────────────────┘
                                       │  paid
                                       ▼
                    ┌──────────────────────────────────────────┐
                    │  Done                                    │
                    │  SalesOrder COMPLETED + Commission 计提  │
                    └──────────────────────────────────────────┘
```

## 5 个 SalesOrder 状态

```
PENDING ──confirm──▶ CONFIRMED ──ship──▶ SHIPPED ──complete──▶ COMPLETED
   │                     │
   │                     └─cancel────▶ CANCELLED
   │                                  （append reason）
   └─cancel──▶ CANCELLED
```

**5 状态 / 7 合法转移 / 2 终态**（COMPLETED / CANCELLED）

业务规则：
- 订单必须 ≥ 1 个明细
- 订单必须有 owner 才能 confirm
- 明细只能 PENDING 状态修改
- cancel 必须填原因

## 4 个 Invoice 状态

```
DRAFT ──issue──▶ ISSUED ──pay_full──▶ PAID
   │                 │
   │                 └─pay_partial──▶ ISSUED（累计到 total 才完成）
   │
   └─cancel──▶ CANCELLED
```

## 4 个 PaymentRecord 状态

```
PENDING ──complete──▶ COMPLETED
   │                       │
   │                       └─reverse──▶ REVERSED（退款）
   │
   └─overdue──▶ OVERDUE ──complete──▶ COMPLETED
```

## 跨表自动对账（核心创新）

```
PaymentRecord.complete()
       │
       ├─ 发射 PaymentReceived event
       │     (aggregate_type=PaymentRecord, invoice_id, amount)
       │
       └─ Invoice 监听 event
              │
              ├─ invoice.record_payment(amount)
              │     │
              │     └─ paid_amount += amount
              │
              └─ if paid_amount >= total:
                       │
                       ├─ 状态自动转 PAID
                       │
                       └─ 发射 InvoicePaid event
                             │
                             └─ 触发佣金计提（未来 Stage 3）
```

**测试**：`test_partial_then_full_payment_drive_invoice_to_paid` 验证 3 笔分次付款（500 + 300 + 330）自动驱动发票 PAID。

## 状态审计表

**位置**：`status_transition_logs`（migration `0004_status_transition_logs`）

| 字段 | 类型 | 说明 |
|---|---|---|
| `aggregate_type` | VARCHAR(50) | "SalesOrder" / "Invoice" / ... |
| `aggregate_id` | INTEGER | ORM row id |
| `aggregate_no` | VARCHAR(50) | SO20260611001（人可读）|
| `status_before` | VARCHAR(20) | 上一个状态（create 时为 NULL）|
| `status_after` | VARCHAR(20) | 新状态 |
| `action` | VARCHAR(50) | 业务动作：confirm/ship/complete/cancel/pay_full/issue/... |
| `actor` | VARCHAR(100) | 触发人（user_id str，None=未指定）|
| `reason` | TEXT | 取消/冲销原因 |
| `transitioned_at` | TIMESTAMPTZ | 转移时间 |
| `customer_id` | INTEGER | FK 客户（快速查客户时间线）|
| `sales_order_id` | INTEGER | FK 订单（SO 相关转移）|

**append-only** — 不更新不删除。

**4 个组合索引**：
- `(aggregate_type, aggregate_id)` — 查单聚合时间线
- `(customer_id, transitioned_at)` — 查客户近期活动
- `(transitioned_at)` — 全局时间序
- 单独 `(customer_id)` / `(sales_order_id)` — 外键 JOIN

## audit_service API

```python
from app.services.audit_service import log_transition, get_aggregate_timeline, get_customer_timeline

# 写一行（不 commit，caller 控原子性）
await log_transition(
    db,
    aggregate_type="SalesOrder",
    aggregate_id=100,
    aggregate_no="SO20260611001",
    status_before="pending",
    status_after="confirmed",
    action="confirm",
    actor="sales_alice",
    customer_id=1,
    sales_order_id=100,
)
await db.commit()  # 状态变更 + 审计一起 commit

# 查单聚合时间线（订单时间线 UI）
timeline = await get_aggregate_timeline(db, "SalesOrder", 100)
# 返回 [create@T1, confirm@T2, ship@T3, complete@T4]

# 查客户近期活动（客户详情页用）
timeline = await get_customer_timeline(db, customer_id=1, limit=50)
```

## 状态机 vs ORM 现状

Stage 2 不动 service 层 / 路由层 / ORM。

| 层 | Stage 2 动作 | 未来工作 |
|---|---|---|
| **domain** | 新增 3 个聚合（order/invoice/payment）+ 4 个 events | - |
| **application** | 现有 use case 继续用 entities.py v1 | Stage 3 迁移到 v2 |
| **service** | 加 audit_service，service 层不强制 | Stage 3 在 status 变更时自动 log |
| **api/route** | 不动 | Stage 3 加订单时间线 endpoint |
| **model/ORM** | 加 StatusTransitionLog | - |
| **migration** | 加 0004（已 apply） | - |

**v1/v2 共存策略**：
- `entities.py` (v1) → 4 个 application use case 还在用
- `order.py` (v2) → Stage 2 新增，命名加 V2 后缀避免冲突
- 路由调用 v1，domain 测试用 v2

## 使用 audit log 解决的具体业务问题

1. **"这单为什么是 completed？"** → `get_aggregate_timeline` 查完整路径 + actor
2. **"客户 A 的订单平均几天才确认？"** → SQL `AVG(confirmed_at - created_at)`
3. **"上个月被取消最多的产品？"** → SQL `GROUP BY product_id WHERE action='cancel'`
4. **"张三是几号确认的 SO001？"** → `WHERE aggregate_id=1 AND actor='zhangsan'`
5. **"客户 A 近期所有活动"** → `get_customer_timeline` 跨所有聚合

## 测试覆盖

```
44 + 12 + 7 = 63 状态机 + 审计测试（Stage 2 总和）
+ 60 sales_api（无回归）
= 123 全部通过
```

| 测试文件 | 测试数 | 覆盖 |
|---|---|---|
| `test_sales_order_state_machine.py` | 20 | 订单聚合 v2 |
| `test_invoice_payment_state_machines.py` | 24 | 发票 + 付款 v2 + 跨表对账 |
| `test_audit_service.py` | 12 | audit_service API |
| `test_order_to_payment_lifecycle.py` | 7 | 端到端（Q→SO→DN→INV→PAY）|

## Stage 3 待办

1. **service 层接入 audit log**：
   - `sales_service/orders.py` 的 `update_order` 检测 status 变更时自动 log
   - `finance_service.py` 的 `update_invoice` / `update_payment` 同上
2. **路由加 `/orders/{id}/timeline`** → 用 `get_aggregate_timeline` 输出
3. **客户详情页 /customers/{id}/activity** → 用 `get_customer_timeline`
4. **佣金计提 listener**（订阅 `InvoicePaid` event）
5. **dashboard 报表**：平均停留时长 / cancel 率 / 高频取消客户

## 设计原则

1. **聚合根纯 Python** — 不依赖 SQLAlchemy / FastAPI / 任何框架
2. **events 解耦** — 跨表联动用 event 桥接，service 不直接调用
3. **append-only 审计** — 不更新不删除，全链路可重放
4. **状态机校验前置** — domain 层抛 `InvalidStateTransition`，service 层捕获
5. **测试零 DB 依赖** — sqlite 内存 + 完整 model 注册，CI 跑得快
