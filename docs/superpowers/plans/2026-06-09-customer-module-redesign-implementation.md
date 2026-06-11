# 客户模块完整重设计 实现计划

> **面向 AI 代理的工作者：** 使用 `superpowers:subagent-driven-development` 逐任务实现。步骤使用 `- [ ]` 语法跟踪进度。

**目标：** 完整重设计客户模块（查找→详情→行动），支持4角色权限、6个自动状态转换，性能目标：列表<2s、虚拟滚动10k+行。

**架构：** 后端权限+状态+缓存 → 前端模块化组件（单文件<500行）。后端优先，前端并行。

**关键文件结构：**
- 后端：models/customer + services/{customer_service, customer_status_manager, customer_permission_service} + jobs/customer_status_updater
- 前端：pages/customers/{components, hooks, types} + CustomerList.tsx 主容器
- 测试：对应 tests/ 目录结构

---

# Phase 1：后端基础（4 任务）

## 任务 1：客户状态枚举 + 自动转换规则

**文件：**
- 修改：`backend/app/models/customer.py`（添加 CustomerStatus 枚举 + last_interaction_at, total_sales_12m 字段）
- 创建：`backend/app/services/customer_status_manager.py`（6个转换规则）
- 创建：`backend/tests/test_customer_status_manager.py`（TDD 测试）

**关键代码框架：**

```python
# CustomerStatus 枚举
class CustomerStatus(str, Enum):
    NEW_PROSPECT = "new_prospect"
    ACTIVE = "active"
    CONVERTED = "converted"
    VIP = "vip"
    INACTIVE = "inactive"
    LOST = "lost"

# 转换规则（TDD：先写测试再实现）
class CustomerStatusManager:
    def handle_opportunity_created(customer) → 新潜客转活跃
    def handle_order_delivered(customer) → 活跃转已成交
    def check_inactive_status(customer) → 最后互动>90天转不活跃
    def check_vip_status(customer) → 12月销售>50万转VIP
    def check_lost_status(customer) → 不活跃>180天转流失
```

**Commit：** `feat: add customer status enum and auto-transition rules`

---

## 任务 2：权限检查服务（4 角色矩阵）

**文件：**
- 创建：`backend/app/services/customer_permission_service.py`
- 创建：`backend/tests/test_customer_permission_service.py`

**权限矩阵实现：**

```python
class CustomerPermissionService:
    FIELD_PERMISSIONS = {
        UserRole.SALES_REP: {
            read: [name, industry, region, status, ...],
            write: [name, industry, region, tags, remark]
        },
        UserRole.FINANCE: {
            read: [name, credit_limit, payment_terms, ...],
            write: [credit_limit, payment_terms]
        },
        UserRole.SALES_MANAGER: {read: [...], write: [...]},
        UserRole.ADMIN: {read: ["*"], write: ["*"]}
    }
    
    def can_view_customer(user, customer_id) → bool
    def can_edit_field(user, field_name) → bool
    def can_delete_customer(user) → bool
    def filter_visible_fields(user, customer_data) → dict
```

**测试用例：** 32个（4角色 × 8操作）  
**Commit：** `feat: add customer permission service for RBAC`

---

## 任务 3：CustomerService（查询+缓存+权限）

**文件：**
- 创建：`backend/app/services/customer_service.py`（主业务逻辑）
- 修改：`backend/app/api/v1/customers.py`（调用新 service）
- 创建：`backend/tests/test_customer_service.py`

**核心方法：**

```python
class CustomerService:
    async def list_customers(user, filters, page, limit):
        # 1. 根据角色构建查询范围
        # 2. 应用筛选条件
        # 3. 检查 Redis 缓存
        # 4. 执行查询（索引优化）
        # 5. 应用字段级权限
        # 6. 缓存 5 分钟
        return {"total": ..., "data": [...]}
    
    async def search_customers(user, query_string):
        # 搜索名称、电话、邮箱
        # 应用权限过滤
    
    async def get_customer_detail(user, customer_id):
        # 权限检查
        # 应用字段权限
    
    async def update_customer(user, customer_id, update_data):
        # 权限检查
        # 字段级权限验证
        # 清除缓存
```

**性能指标：** 查询 <100ms、搜索 <300ms  
**Commit：** `feat: add customer service with caching and permission filtering`

---

## 任务 4：定时任务（APScheduler 自动状态转换）

**文件：**
- 创建：`backend/app/jobs/customer_status_updater.py`
- 修改：`backend/app/jobs/scheduler.py`（添加任务）
- 创建：`backend/tests/test_customer_status_updater.py`

**定时任务安排：**

```python
# 每天 00:01 执行
async def update_inactive_customers():
    # 查询最后互动>90天的客户
    # 更新状态为 INACTIVE

# 每天 00:02 执行
async def update_lost_customers():
    # 查询 INACTIVE 状态>180天的客户
    # 更新状态为 LOST

# 每天 00:03 执行
async def update_vip_customers():
    # 查询 CONVERTED 且 12月销售>50万的客户
    # 更新状态为 VIP
```

**特性：** 100% 自动，销售人员无法手动修改状态  
**Commit：** `feat: add customer status auto-updater job`

---

# Phase 2：前端基础（2 任务）

## 任务 5：TypeScript 类型 + 常量

**文件：**
- 创建：`frontend/src/pages/customers/types/CustomerTypes.ts`
- 创建：`frontend/src/pages/customers/constants.ts`

**类型定义：**

```typescript
// 枚举
enum CustomerStatus { NEW_PROSPECT, ACTIVE, CONVERTED, VIP, INACTIVE, LOST }
enum UserRole { SALES_REP, SALES_MANAGER, FINANCE, ADMIN }

// 接口
interface Customer {
  id, name, industry, region, status, total_sales_12m, 
  credit_limit, credit_score, payment_terms, ...
}
interface CustomerFilters {
  status?, industry?, region?, sales_range?, last_interaction_days?, owner_id?
}

// 权限矩阵
interface FieldPermissions {
  [role]: { readable: string[], writable: string[] }
}
```

**常量：**
- STATUS_DISPLAY_NAMES、STATUS_COLORS
- DEFAULT_PAGE_SIZE = 100
- CACHE_TTL_MINUTES = 5
- SEARCH_DEBOUNCE_MS = 300
- VIRTUAL_SCROLL_HEIGHT = 48px

**Commit：** `feat: add customer types and constants`

---

## 任务 6：useCustomerData Hook（搜索+筛选+缓存）

**文件：**
- 创建：`frontend/src/pages/customers/hooks/useCustomerData.ts`
- 创建：`frontend/src/pages/customers/hooks/useCustomerData.test.ts`

**Hook 功能：**

```typescript
function useCustomerData() {
  // 状态
  const [customers, setCustomers] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [filters, setFilters] = useState({})
  const [page, setPage] = useState(1)

  // 缓存（Map，5min TTL）
  const cacheRef = useRef()

  // 搜索 debounce 300ms
  const handleSearchChange = (query) => {
    // 清除旧 timer，设置新 timer
    // 300ms 后调用 fetchData
  }

  // 筛选立即触发
  const handleFiltersChange = (newFilters) => {
    // 立即调用 fetchData
  }

  // 获取数据（缓存优先）
  const fetchData = async (query) => {
    // 检查缓存
    // 调用 API
    // 缓存结果
  }

  return {
    customers, total, loading, error,
    page, searchQuery, filters,
    setSearchQuery, setFilters, setPage
  }
}
```

**性能：** 缓存命中 <50ms、缓存未中 <500ms  
**测试：** 搜索、筛选、缓存、分页  
**Commit：** `feat: add useCustomerData hook with caching`

---

# Phase 3：前端 UI 组件（5 任务）

## 任务 7：CustomerFilterBar 组件

**文件：** `frontend/src/pages/customers/components/CustomerFilterBar.tsx`

**UI：** 折叠式筛选栏，包含：
- 状态多选（6个）
- 行业多选
- 地区级联（省→市）
- 金额范围（起-止）
- 最后互动（7/30/90天或自定义）
- 所有者（我的/团队/全部，主管可见）

**功能：** onChange 时调用 `useCustomerData.setFilters()`

---

## 任务 8：CustomerListTable 组件（虚拟滚动）

**文件：** `frontend/src/pages/customers/components/CustomerListTable.tsx`  
**库：** `react-window` 虚拟滚动

**表格列：**
| 名称 | 行业 | 地区 | 状态 | 交易额 | 最后订单 | 信用评分 | 操作 |

**特性：**
- 虚拟滚动（行高 48px）
- 支持 10k+ 行
- 行点击进详情面板
- 操作列：【详情】【新增机会】

**性能：** <1s 渲染 10k 行

---

## 任务 9：CustomerDetailPanel 组件

**文件：** `frontend/src/pages/customers/components/CustomerDetailPanel.tsx`

**抽屉式设计，从右侧滑入（400px）**

**Tab 1：基本信息（默认）**
- 客户名称（大标题）
- 行业、地区、状态 Tag
- 关键指标卡（2×2 Grid）：累计交易额、最后订单、信用评分、订单数
- 联系信息（可拨打、发邮件）
- 快捷按钮：【新增机会】【发起跟进】【编辑】【更多】

**Tab 2：360 视图**
- 📊 交易历史（最近 3 笔订单）
- 🏷️ 标签 + 分段（可编辑）
- 👥 联系人列表（可新增）
- 🎯 活跃机会（进行中的）
- ⚠️ 警告规则

**Tab 3：AI 洞察（后续标记）**
- RFM 分析
- 推荐产品
- 流失预警

**编辑模式：** 点击【编辑】→ 切换为表单

---

## 任务 10：CustomerFormEditor 组件

**文件：** `frontend/src/pages/customers/components/CustomerFormEditor.tsx`

**必填字段（第一层）：**
- 客户名称
- 行业（下拉）
- 地区（级联：省→市）
- 主要联系方式（电话/邮箱）
- 信用额度（CNY）
- 备注（可选）

**高级字段（展开后）：**
- 企业注册号
- 税号
- 付款条款（下拉）
- 送货地址
- 自定义字段

**功能：**
- 实时验证（必填字段标红）
- 字段级权限（财务不能编辑 name）
- 自动保存草稿
- 提交前检查所有权限

---

## 任务 11：useCustomerColumns Hook

**文件：** `frontend/src/pages/customers/hooks/useCustomerColumns.ts`

**功能：** 生成 Ant Design 表格列定义，根据用户权限隐藏列

```typescript
function useCustomerColumns(user: CurrentUser): ColumnsType<Customer> {
  // 生成 8 列的定义
  // 根据 user.roles 和 FIELD_PERMISSIONS 隐藏不可见列
  // 返回 ColumnsType
}
```

---

# Phase 4：集成与测试（3 任务）

## 任务 12：CustomerList 主容器

**文件：** `frontend/src/pages/customers/index.tsx`（重构主页）

**响应式布局：**
- 1440px+：三列（导航 | 列表 | 详情面板）
- 1024-1439px：列表 + Modal 详情
- <1024px：全屏列表，点击进页面详情

**整合所有组件：** FilterBar + Table + DetailPanel + Form

---

## 任务 13：后端单元 + 集成测试

**覆盖：** ≥ 80%

**单元测试：**
- `test_customer_status_manager.py`：6 个状态转换规则
- `test_customer_permission_service.py`：32 个权限 case
- `test_customer_service.py`：查询、缓存、权限

**集成测试：**
- `test_customer_api.py`：完整 CRUD + 权限拦截
- 权限隔离：销售代表不能看别人的客户
- 缓存验证：重复查询命中缓存

**Commit：** `test: add backend unit and integration tests (80% coverage)`

---

## 任务 14：前端 + E2E 测试

**单元测试：**
- `useCustomerData.test.ts`：搜索、筛选、缓存
- `CustomerFilterBar.test.tsx`：筛选逻辑
- `CustomerPermissions.test.ts`：字段权限应用

**E2E 测试（Playwright）：**

场景 1：销售代表查找客户
```
1. 登录为销售代表
2. 打开客户列表（仅看自己的）
3. 搜索客户名称
4. 点击行进入详情
5. 点击【新增机会】
6. 验证机会创建成功 + 客户状态转为 ACTIVE
```

场景 2：主管批量导出
```
1. 登录为销售主管
2. 筛选条件（日期范围、金额）
3. 点击【批量操作】→【导出】
4. 验证导出文件包含筛选后的数据
```

场景 3：财务编辑信用
```
1. 登录为财务
2. 搜索客户
3. 点击【编辑】
4. 验证仅 credit_limit 和 payment_terms 可编辑
5. 其他字段灰显
```

**Commit：** `test: add frontend unit and E2E tests`

---

# 文件清单（完整）

## 创建
```
backend/
  app/
    models/
      customer.py (添加枚举 + 字段)
    services/
      customer_status_manager.py
      customer_permission_service.py
      customer_service.py (新增或扩展)
    jobs/
      customer_status_updater.py
  tests/
    test_customer_status_manager.py
    test_customer_permission_service.py
    test_customer_service.py
    test_customer_status_updater.py

frontend/
  src/pages/customers/
    types/
      CustomerTypes.ts
    hooks/
      useCustomerData.ts
      useCustomerColumns.ts
    components/
      CustomerFilterBar.tsx
      CustomerListTable.tsx
      CustomerDetailPanel.tsx
      CustomerFormEditor.tsx
    tests/
      useCustomerData.test.ts
      CustomerFilterBar.test.tsx
      (...)
    constants.ts
    index.tsx (重构主容器)
```

## 修改
```
backend/app/api/v1/customers.py (调用新 service)
backend/app/jobs/scheduler.py (添加新任务)
```

---

# 执行选项

**计划已完成并保存。两种执行方式：**

### 1️⃣ **子代理驱动（推荐）**
- 每个任务启动一个新子代理
- 任务间进行代码审查检查点
- 快速反馈循环

**使用技能：** `superpowers:subagent-driven-development`

### 2️⃣ **内联执行**
- 在当前会话中执行所有任务
- 按 Phase 顺序批量运行
- 每个 Phase 后审查

**使用技能：** `superpowers:executing-plans`

---

**你选哪种方式？**
