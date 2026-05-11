# 003 — Phase 5: 审批工作流 + 采购智能化 + 报表分析 + 权限安全

## 1. 概述

### 背景
AIERP 已完成销售全流程（Phase 2）、AI 基础（Phase 3）和智能平台（Phase 4）。当前缺失企业级 ERP 的核心能力：审批控制、智能采购决策、可定制报表和细粒度权限管理。

### 范围
Phase 5 包含四个子模块：审批工作流（B）、采购智能化（C）、报表与分析（D）、权限与安全（E）。

### 关键约束
- 所有新模型继承 `TimestampMixin`（soft-delete）
- API 遵循 `{ code: 0, message: "ok", data: T }` 响应格式
- 前端保持 Ant Design 5 + React 19 + Zustand 技术栈
- AI 调用通过现有 `ai_client` 单例（SiliconFlow），带 tenacity 重试

---

## 2. 目标

| 目标 | 衡量标准 |
|------|---------|
| 审批流程覆盖核心单据 | 报价、采购订单支持多级审批 |
| 采购决策 AI 自动化 | 补货建议准确率 > 70%，自动匹配最佳供应商 |
| 可定制报表 | 支持自定义维度、筛选、图表类型的报表构建器 |
| 细粒度权限 | 资源级 CRUD 权限控制，角色可配置 |

---

## 3. 用户故事

### B — 审批工作流

**US-B1**: 作为销售经理，我可以配置报价审批规则（如金额 > 5 万需审批），提交报价后自动触发审批流。
- AC: 创建审批规则时可设置条件（单据类型、金额阈值、客户等级），规则保存后立即生效

**US-B2**: 作为审批人，我可以看到待审批列表，查看单据详情，一键通过或驳回并填写意见。
- AC: 审批列表显示提交人、金额、时间；审批操作记录到操作日志

**US-B3**: 作为销售员，我可以看到我提交的审批状态（待审批/已通过/已驳回），驳回后可修改重新提交。
- AC: 驳回后原单据可编辑并重新提审

### C — 采购智能化

**US-C1**: 作为采购员，系统自动扫描低库存产品并生成补货建议列表，我确认后一键生成采购订单。
- AC: 建议列表显示产品名称、SKU、当前库存、安全库存、建议采购量、推荐供应商

**US-C2**: 作为采购员，创建采购订单时系统自动推荐最优供应商（基于价格、交期、历史履约率）。
- AC: 推荐供应商显示综合评分和各项指标对比

**US-C3**: 作为采购经理，我可以看到采购仪表板：在途订单、预计到货、供应商履约统计。
- AC: 仪表板包含 PO 状态分布、供应商延期率、采购金额趋势

### D — 报表与分析

**US-D1**: 作为管理者，我可以创建自定义报表：选择数据源、维度、指标、图表类型，保存后随时查看。
- AC: 支持表格、柱状图、折线图、饼图；配置可保存复用

**US-D2**: 作为财务，我可以查看应收账款报表：按客户、账龄、金额分布。
- AC: 报表支持筛选时间范围、导出 Excel/PDF

**US-D3**: 作为运营，我可以查看库存周转报表、产品销售排行。
- AC: 图表可交互（下钻、tooltip），数据实时刷新

### E — 权限与安全

**US-E1**: 作为管理员，我可以定义权限（如 `product:read`、`product:write`），将权限分配给角色，将角色分配给用户。
- AC: 权限检查在 API 层生效，未授权返回 403

**US-E2**: 作为管理员，我可以查看操作审计日志：谁在什么时间做了什么操作。
- AC: 日志包含用户、操作、目标资源、时间、IP

**US-E3**: 作为销售员，我只能看到自己负责的客户和商机（数据权限隔离）。
- AC: 列表查询自动按 owner 或 assigned_to 过滤

---

## 4. 功能需求

### B — 审批工作流

| ID | 功能 | 描述 |
|----|------|------|
| B-01 | 审批规则 CRUD | 支持按单据类型、金额阈值、客户等级设置触发条件 |
| B-02 | 审批流定义 | 支持多级审批（1-3 级），每级可指定审批人角色或具体用户 |
| B-03 | 审批提交 | 报价/采购订单可提交审批，状态变更为 pending_approval 并锁定编辑 |
| B-04 | 审批操作 | 通过/驳回，填写审批意见；驳回后单据解锁 |
| B-05 | 审批列表 | 我的待审批 / 我提交的，支持筛选状态 |
| B-06 | 审批通知 | 审批提交/通过/驳回时发送站内通知 |

### C — 采购智能化

| ID | 功能 | 描述 |
|----|------|------|
| C-01 | 智能补货建议 | 基于库存水平 + 安全库存 + 需求预测，生成补货建议列表 |
| C-02 | 供应商推荐 | 采购时自动推荐供应商，基于价格、交期、历史质量评分 |
| C-03 | 采购订单优化 | AI 分析 PO 数量、价格、供应商，给出优化建议 |
| C-04 | PO 风险预警 | 发送 PO 延期风险、供应商风险通知 |
| C-05 | 采购仪表板 | PO 状态分布、供应商履约统计、采购金额趋势、预计到货日历 |
| C-06 | 入库联动 | PO 收货自动更新库存（通过 inventory_transactions） |

### D — 报表与分析

| ID | 功能 | 描述 |
|----|------|------|
| D-01 | 报表构建器 | 前端拖拽式配置：数据源 → 维度 → 指标 → 图表类型 |
| D-02 | 预置报表模板 | 销售分析、应收账龄、库存周转、采购分析 4 套模板 |
| D-03 | 报表导出 | 支持 Excel (openpyxl) 和 PDF (ReportLab) 导出 |
| D-04 | 图表交互 | 下钻、tooltip、时间范围选择、数据刷新 |
| D-05 | 报表保存/分享 | 报表配置可保存复用，同角色用户可查看 |

### E — 权限与安全

| ID | 功能 | 描述 |
|----|------|------|
| E-01 | 权限定义 | 资源 + 操作模型：`customers:read`、`customers:write`、`customers:delete` |
| E-02 | 角色管理 | 角色 CRUD，角色关联权限，内置 admin/sales/warehouse/finance 四个角色 |
| E-03 | 用户-角色关联 | 用户可分配一个或多个角色 |
| E-04 | API 权限拦截 | FastAPI 中间件/dependency 检查当前用户权限 |
| E-05 | 数据权限隔离 | sales 角色只看到自己 owner/assigned_to 的客户和商机 |
| E-06 | 审计日志 | 记录所有 CUD 操作：用户、时间、IP、操作类型、目标资源、变更摘要 |
| E-07 | 前端权限控制 | 根据权限隐藏/禁用菜单项和操作按钮 |

---

## 5. 非功能需求

| 类别 | 要求 |
|------|------|
| 性能 | 报表查询响应 < 3s（数据量 < 10 万行）；权限检查开销 < 5ms |
| 安全 | 密码 bcrypt 哈希；JWT 过期 8h；审计日志不可删除 |
| 可扩展 | 权限资源注册机制，新模块可声明自己的权限 |
| 兼容性 | 所有新表支持 soft-delete；现有 API 不破坏 |

---

## 6. 数据模型

### 新增表

```sql
-- 权限
permissions (id, resource, action, name, description, created_at, updated_at, deleted_at)
roles (id, name, description, created_at, updated_at, deleted_at)
role_permissions (role_id FK, permission_id FK)
user_roles (user_id FK, role_id FK)

-- 审批
approval_rules (id, doc_type, min_amount, customer_level, flow_config JSON, enabled, created_at, updated_at, deleted_at)
approval_requests (id, doc_type, doc_id, submitter_id FK→users, status, current_level, flow_snapshot JSON, created_at, updated_at, deleted_at)
approval_actions (id, request_id FK, approver_id FK→users, action, comment, level, created_at, updated_at, deleted_at)

-- 报表
report_templates (id, name, type, config JSON, created_by FK→users, is_public, created_at, updated_at, deleted_at)

-- 审计
audit_logs (id, user_id FK→users, username, action, resource_type, resource_id, summary, ip_address, created_at)
```

### 现有表变更

```sql
ALTER TABLE purchase_orders ADD COLUMN approval_request_id FK→approval_requests;
ALTER TABLE quotations ADD COLUMN approval_request_id FK→approval_requests;
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT true;
```

---

## 7. API 设计

### 审批工作流 `POST/GET/PUT/DELETE /api/v1/approvals/...`

| 端点 | 方法 | 描述 |
|------|------|------|
| `/approvals/rules` | GET/POST | 审批规则列表/创建 |
| `/approvals/rules/{id}` | PUT/DELETE | 编辑/删除规则 |
| `/approvals/requests` | GET | 审批请求列表（支持筛选：status、doc_type、submitter） |
| `/approvals/requests/{id}` | GET | 审批详情（含审批历史） |
| `/approvals/requests/{id}/submit` | POST | 提交审批 |
| `/approvals/requests/{id}/approve` | POST | 通过（body: {comment}） |
| `/approvals/requests/{id}/reject` | POST | 驳回（body: {comment}） |

### 采购智能 `GET/POST /api/v1/ai/procurement/...`

| 端点 | 方法 | 描述 |
|------|------|------|
| `/ai/procurement/restock-suggest` | GET | 智能补货建议（参数：warehouse_id, top_k） |
| `/ai/procurement/supplier-recommend` | GET | 供应商推荐（参数：product_ids, quantity） |
| `/ai/procurement/dashboard` | GET | 采购仪表板数据 |
| `/ai/procurement/po-calendar` | GET | PO 预计到货日历 |

### 报表 `GET/POST /api/v1/reports/...`

| 端点 | 方法 | 描述 |
|------|------|------|
| `/reports/templates` | GET/POST | 报表模板列表/创建 |
| `/reports/templates/{id}` | PUT/DELETE | 编辑/删除模板 |
| `/reports/execute/{template_id}` | POST | 执行报表（参数：filters, date_range） |
| `/reports/export/{template_id}` | POST | 导出报表（参数：format=excel/pdf） |
| `/reports/predefined/sales` | GET | 预置销售分析报表 |
| `/reports/predefined/ar` | GET | 预置应收账龄报表 |
| `/reports/predefined/inventory` | GET | 预置库存周转报表 |
| `/reports/predefined/procurement` | GET | 预置采购分析报表 |

### 权限管理 `GET/POST /api/v1/permissions/...`

| 端点 | 方法 | 描述 |
|------|------|------|
| `/permissions` | GET | 权限列表 |
| `/roles` | GET/POST | 角色列表/创建 |
| `/roles/{id}` | PUT/DELETE | 编辑/删除角色 |
| `/roles/{id}/permissions` | PUT | 设置角色权限 |
| `/users/{id}/roles` | GET/PUT | 用户角色查询/设置 |
| `/audit-logs` | GET | 审计日志列表（支持筛选） |

---

## 8. UI/UX 设计

### 审批工作流
- **审批规则页**: 表格 + 新建/编辑 Modal，条件配置表单（单据类型 Select、金额 InputNumber、客户等级 Select、审批级数、每级审批人选择）
- **审批列表页**: Tabs（待审批 / 我提交的），表格列：单据号、提交人、金额、状态标签、时间
- **审批详情**: 单据摘要 + 审批历史 Timeline + 操作区（通过/驳回按钮 + 意见输入框）

### 采购智能化
- **补货建议页**: 表格 + 批量选择 + "一键生成采购单"按钮，每行显示推荐供应商
- **采购仪表板**: 4 卡片（待审批、在途、已延期、本月采购额）+ PO 状态饼图 + 供应商履约柱状图 + 采购趋势折线图

### 报表与分析
- **报表构建器**: 左侧数据源/维度/指标选择面板，中间图表预览区，右侧配置面板
- **预置报表**: 4 个 Tab 页分别展示，顶部时间筛选 + 导出按钮

### 权限管理
- **角色管理页**: 表格 + Modal 表单 + 权限树形选择器
- **用户管理增强**: 现有用户列表增加角色分配和启用/禁用开关
- **审计日志页**: 时间范围筛选 + 表格（用户、操作、资源、时间、详情链接）

---

## 9. 测试策略

### 单元测试
- 权限中间件：正确权限返回 200，无权限返回 403
- 审批流状态机：draft → pending_approval → approved/rejected → draft (resubmit)
- 报表查询：验证 SQL 聚合正确性

### 集成测试
- 审批流端到端：创建规则 → 提交审批 → 审批人通过 → 单据状态变更
- 采购智能：低库存触发补货建议 → 生成 PO → 收货 → 库存更新
- 权限隔离：sales 角色只能看到自己的客户

### 边缘情况
- 多级审批：第一级驳回不触发第二级通知
- 并发审批：同一审批请求不允许重复操作
- 报表大数据量：10 万行数据查询超时处理
- 权限缓存：角色变更后立即生效（无缓存延迟）
