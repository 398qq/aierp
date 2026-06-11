# AIERP Architecture (Stage 1 Refactor, 2026-06-11)

## 总体目标

把 27 个 service 各自写 CRUD、2 个 API 文件替代了 service 层、前端 2 个页面比大多数 ERP 还重的"业务逻辑三层散落"问题解决，让改一个字段只在一个地方改。

## 三层架构

```
┌──────────────────────────────────────────────────────────────┐
│ Frontend  (React + antd v6 + zustand)                         │
│  - pages/       业务页面（巨型页面待 Stage 3 拆分）             │
│  - components/  复用组件                                      │
│  - store/       全局状态（zustand）                            │
└──────────────────────────────────────────────────────────────┘
                          │ HTTP / JSON
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ API  (FastAPI)                                                │
│  - api/v1/  → 纯代理层（endpoint → service.method → serialize）│
│  - schemas/ Pydantic 入参/出参                                │
│  - core/    工具：error_handlers / cache / permission / ...     │
└──────────────────────────────────────────────────────────────┘
                          │ session
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ Service  (业务核心，Stage 1 重构目标)                          │
│  - 业务方法（list_orders / get_customer_stats / ...）           │
│  - 跨表聚合（RFM / 账龄 / 健康分 / 跟进提醒）                  │
│  - 跨文档转换（报价转订单 → 订单转发货 → 发货转回款）          │
│  - 状态机校验（assert_can_transition_*）                       │
│  - 库存联动（deduct_for_delivery / lock_for_sales_order）     │
└──────────────────────────────────────────────────────────────┘
                          │ SQL
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ Domain / Models  (SQLAlchemy 2.0 async)                       │
│  - customer / product / sales / finance / approval / ...       │
│  - domain/states.py   状态机定义 + 转移规则                    │
│  - domain/shared/     异常类（DomainError + 6 子类）            │
└──────────────────────────────────────────────────────────────┘
                          │ asyncpg
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ PostgreSQL 16  +  pgvector                                     │
│  - 30+ 张表 / 18+ 迁移（持续演进）                             │
│  - Soft-delete 统一约定（deleted_at IS NULL）                  │
└──────────────────────────────────────────────────────────────┘
```

## BaseCRUDService 抽象

**位置**：`backend/app/services/base_crud.py`（80 行）

**提供**：
- `list(db, *, page, page_size, filters, sort_by, sort_order)` — 分页查询
- `get(db, obj_id)` — 按 ID 查询
- `create(db, data)` — 创建（自动 commit + refresh）
- `update(db, obj, data)` — 更新（None 跳过）
- `delete(db, obj)` — 软删除（设 deleted_at）

**约定**：
- 所有 model 必须有 `deleted_at: datetime | None` 字段（soft-delete）
- 子类设 `model = <SQLAlchemy model>`
- 子类可加业务方法（list_orders / soft_delete_order / get_customer_stats ...）
- 业务方法用**专属名**避免覆盖基类契约

## Stage 1 改造成果

### 路由层瘦身

| 文件 | 之前 | 之后 | 减少 |
|---|---|---|---|
| `api/v1/customers/stats.py` | 832 行 | 149 行 | -683 行 (-82%) |
| `api/v1/products/list.py` | 660 行 | 121 行 | -539 行 (-82%) |

### 新增 service（继承 BaseCRUDService）

| Service | 文件 | 业务方法数 |
|---|---|---|
| CustomerStatsService | services/customer_stats_service.py | 9 |
| ProductService | services/product_service.py | 4 |
| QuotationService | sales_service/quotations.py | 8 |
| SalesOrderService | sales_service/orders.py | 5 |
| DeliveryNoteService | sales_service/delivery_notes.py | 8 |
| SalesConversionService | sales_service/conversions.py | 2 |
| CustomerService | services/customer_service.py | 2 (class wrapper) |
| NotificationService | services/notification_service.py | 6 |

**总计**：8 个 service 升级 / 44 个业务方法进 class / base_crud 使用率 0/27 → 8/27（30%）

### 统一异常体系

位置：`backend/app/domain/shared/errors.py`

| 异常类 | HTTP | 用途 |
|---|---|---|
| DomainError | 400 | 基类（所有业务异常的根） |
| BusinessRuleViolation | 422 | 业务规则失败 |
| InvalidStateTransition | 422 | 状态机禁止转移 |
| NotFoundError | 404 | 聚合根找不到 |
| InsufficientStockError | 422 | 库存不足 |
| ConcurrentModificationError | 409 | 并发冲突 |
| **ValidationError**（新）| 422 | 字段校验失败 |
| **ConflictError**（新）| 409 | 资源状态冲突（如重复键）|

**handler 位置**：`backend/app/core/error_handlers.py`（55 行，统一转换为 `ok({code, msg, ...})` 格式）

## 设计原则

### 1. 行为不变原则
- 重构只搬代码，不改业务
- 字段名/值/格式 100% 保持
- 路由 URL/参数/响应 0 变化
- 调用方零改动（保留模块级函数作为薄代理）

### 2. 服务单例
- 每个 service 文件底部加 `xxx_service = XxxService()` 单例
- 路由层：`from app.services.xxx_service import xxx_service`
- 调用：`await xxx_service.method(...)`

### 3. 命名规范
- 业务方法**不**叫 list/get/create/update/delete（避免覆盖 BaseCRUDService）
- 命名模式：
  - `list_orders` / `list_quotations` / `list_delivery_notes`（实体名后缀）
  - `get_order` / `get_quotation`（实体名）
  - `create_order` / `create_quotation`（动词_实体）
  - `update_order_with_items`（含子对象时）
  - `soft_delete_order`（区分 base_crud.delete）
  - `get_customer_stats` / `get_dashboard_stats`（聚合查询）

### 4. 异常抛出
- Service 层用 `raise NotFoundError(...)` / `raise BusinessRuleViolation(...)` / ...
- Router 不用 try/except 捕获——handler 统一转换
- 保持代码简洁

## 待办（Stage 2+）

### Stage 2：跟单全流程状态机
- 商机→报价→订单→发货→开票→回款，6 个状态
- SQLAlchemy event 自动推进 + 状态变更审计
- 产出：一笔单子从入口到回款全链路可追溯

### Stage 3：前端巨型页面拆分
- customers/index 1703 行 → List/Filter/Drawer/Tabs 4 子组件
- products/index 1573 行 → 同上
- sales/salesUi 786 行 → KanbanBoard / OrderForm / StatusBadge 等
- 统一 data fetching（React Query）+ 全局 store
- 产出：单文件 < 400 行

### Stage 4：测试 + CI
- 跟单全流程集成测试（Pytest + httpx）
- 前端关键组件测试（Vitest + @testing-library）
- GitHub Actions：lint + test + build

### Stage 5：迁移规范 + 文档
- 18 个 migration 整理模板（带 down + 注释）
- 写 ARCHITECTURE.md（已完成本文）
- MIGRATION_BASE_CRUD.md（教新人怎么用）

## 贡献指南

### 新增 service
```python
# services/my_service.py
from app.services.base_crud import BaseCRUDService
from app.models.my_model import MyModel


class MyService(BaseCRUDService):
    model = MyModel
    
    async def list_my_entities(self, db, *, page=1, page_size=20, ...):
        """Business-specific list. Use a distinct name from base.list."""
        ...
    
    async def get_my_entity(self, db, entity_id: int) -> MyModel | None:
        return await self.get(db, entity_id)  # reuse base


# Back-compat module-level wrapper
async def list_my_entities(db, **kwargs):
    return await my_service.list_my_entities(db, **kwargs)


my_service = MyService()
```

### 新增异常
1. 继承 `DomainError`（最常用）或更具体的子类
2. 设 `code`（字符串常量）和 `http_status`（HTTP 状态码）
3. 抛：`raise ValidationError("xxx", field="name")`
4. handler 自动转 `{code, msg, field, ...}` JSON

## 联系方式

- 维护：A-Zhu (CEO Liu 的 AI 助手)
- 反馈：在 Telegram @pis13145 联系
