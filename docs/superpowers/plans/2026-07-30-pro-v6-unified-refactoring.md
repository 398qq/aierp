# Pro v6 统一重构实现计划

> **面向 AI 代理的工作者：** 必需子技能：`superpowers:subagent-driven-development`。
> 步骤使用复选框（`- [ ]`）语法来跟踪进度。
>
> **目标：** 统一 79 个页面的 Pro v6 实现模式，消除混用的旧 antd 写法。
>
> **架构：** 参照 `CustomerListPage.tsx` 已验证模式，将全部 `axios`/`ahooks useRequest` 替换为 `useApiQuery`/`useApiMutation`，将 `message` 静态调用替换为 `App.useApp()`。
>
> **技术栈：** React 19, TypeScript 6, Ant Design Pro v6, TanStack Query v5, UmiJS Max 4

---

## 文件变更概览

| 职责 | 文件 |
|------|------|
| **参考模板** | `frontend/src/pages/customers/CustomerListPage.tsx` |
| **基础设施** | `frontend/src/lib/queries.ts`（已就绪） |
| **Tier 1 页面** | `frontend/src/pages/system/AuditLogList.tsx` |
|  | `frontend/src/pages/system/UomsList.tsx` |
|  | `frontend/src/pages/system/ApprovalList.tsx` |
|  | `frontend/src/pages/warehouse/WarehouseList.tsx` |
|  | `frontend/src/pages/tickets/TicketList.tsx` |
|  | `frontend/src/pages/notifications/index.tsx` |
|  | `frontend/src/pages/finance/AccountList.tsx` |
|  | `frontend/src/pages/finance/JournalEntryList.tsx` |
| **Tier 2 页面** | `frontend/src/pages/sales/OpportunityList.tsx` |
|  | `frontend/src/pages/sales/QuotationList.tsx` |
|  | `frontend/src/pages/sales/SalesOrderList.tsx` |
|  | `frontend/src/pages/sales/InvoiceList.tsx` |
|  | `frontend/src/pages/sales/PaymentList.tsx` |
|  | `frontend/src/pages/sales/DeliveryNoteList.tsx` |
|  | `frontend/src/pages/sales/PurchaseOrderList.tsx` |
|  | `frontend/src/pages/sales/ContractList.tsx` |
|  | `frontend/src/pages/sales/TargetList.tsx` |
| **Tier 3 页面** | `products/index.tsx`、`brands/index.tsx`、`suppliers/index.tsx`、`inventory/index.tsx`、`dashboard/index.tsx` 等 |

---

## 标准迁移模式

每页重构遵循以下统一模式：

### A. 数据获取 — 4 步

**Step 1：识别现有数据获取代码**

找到类似以下旧代码：
```tsx
// ❌ 旧：直接 axios
const [data, setData] = useState([]);
useEffect(() => {
  axios.get('/api/v1/entities', { params }).then(r => setData(r.data.data));
}, [params]);
```

或：
```tsx
// ❌ 旧：ahooks useRequest
const { data, loading, refresh } = useRequest(() => axios.get('/api/v1/entities', { params }));
```

**Step 2：替换为 useApiQuery**

`queries.ts` 的实际签名：`useApiQuery(key, url, params?, options?)`

```tsx
// ✅ 新
import { useApiQuery } from "@/lib/queries";

// 在组件内（key 第二成员自动作为 params hash）
const { data, isLoading } = useApiQuery(
  ['entityList', params],
  '/api/v1/entities',   // URL 字符串，不是函数
  params,
  { keepPreviousData: true }
);
```

> 如果 API 层（`api/` 目录）尚未封装该端点，需先在 `api/index.ts` 或对应域文件（如 `api/sales.ts`）中添加：
> ```tsx
> export const getEntities = (params?: Record<string, unknown>) =>
>   client.get('/api/v1/entities', { params });
> ```
> 然后在页面中 import 使用。

**Step 3：替换 message 调用**

```tsx
// ❌ 旧
import { message } from 'antd';
message.error(getApiErrorMessage(e, "操作失败"));

// ✅ 新
import { App } from 'antd';
const { message } = App.useApp();
message.error(getApiErrorMessage(e, "操作失败"));
```

**Step 4：替换 actionRef.reload()**

```tsx
// ❌ 旧
actionRef.current?.reload();

// ✅ 新
import { useQueryClient } from "@/lib/queries";
const queryClient = useQueryClient();
// 在 mutation 的 onSuccess 中
queryClient.invalidateQueries({ queryKey: ['entityList'] });
```

### B. ProTable 标准结构

```tsx
import { ProTable } from "@ant-design/pro-components";
import { useApiQuery, useApiMutation, useQueryClient } from "@/lib/queries";
import { App } from "antd";

export default function EntityList() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // ✅ useApiQuery 统一数据获取
  const { data, isLoading, refetch } = useApiQuery(
    ['entityList', filterParams],
    '/api/v1/entities',
    filterParams,
    { keepPreviousData: true }
  );

  // ✅ useApiMutation 统一写操作（method, url, options）
  const deleteMutation = useApiMutation(
    'delete',
    (id: number) => `/api/v1/entities/${id}`,
    { invalidateKeys: [['entityList']] }
  );

  const columns: ProColumns<Entity>[] = [
    { title: '名称', dataIndex: 'name' },
    { title: '状态', dataIndex: 'status', valueType: 'select', valueEnum: STATUS_ENUM },
  ];

  return (
    <ProTable
      params={filterParams}
      request={async (params) => {
        // params 包含 search/filter/pagination，无需额外 useState
        return {
          data: data?.list ?? [],
          success: true,
          total: data?.total ?? 0,
        };
      }}
      columns={columns}
      isLoading={isLoading}
      rowSelection={{
        selectedRowKeys,
        onChange: (keys) => setSelectedRowKeys(keys as number[]),
      }}
    />
  );
}
```

---

## Phase 1 — Tier 1 页面（系统/仓储/工单/财务）

### 任务 1：`system/AuditLogList.tsx`

**文件：** `frontend/src/pages/system/AuditLogList.tsx`

- [ ] **步骤 1：分析现状**

运行以下命令了解当前代码结构：
```bash
head -80 frontend/src/pages/system/AuditLogList.tsx
grep -n "axios\|useRequest\|message\.\|actionRef" frontend/src/pages/system/AuditLogList.tsx
```

- [ ] **步骤 2：替换 message import**

找到：
```tsx
import { message } from 'antd';
```
改为：
```tsx
import { App } from 'antd';
```

- [ ] **步骤 3：添加 useApiQuery**

在组件内添加：
```tsx
const { message } = App.useApp();
const { data, isLoading } = useApiQuery(
  ['auditLogs', filterParams],
  '/api/v1/audit-logs',
  filterParams,
  { keepPreviousData: true }
);
```

- [ ] **步骤 4：替换 message 调用**

```tsx
// message.error(getApiErrorMessage(e, "加载失败"))
// 改为：
message.error(getApiErrorMessage(e, "加载失败"));
```

- [ ] **步骤 5：替换 actionRef.reload()**

找到 `actionRef.current?.reload()` 所在位置，改为：
```tsx
const queryClient = useQueryClient();
queryClient.invalidateQueries({ queryKey: ['auditLogs'] });
```

- [ ] **步骤 6：更新 ProTable**

确保 ProTable 使用 `params` + `request` 结构：
```tsx
<ProTable
  params={filterParams}
  request={async (params) => {
    return { data: data?.list ?? [], success: true, total: data?.total ?? 0 };
  }}
  // ...其他 props
/>
```

- [ ] **步骤 7：验证构建**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

- [ ] **步骤 8：运行测试**

```bash
cd frontend && npx vitest run 2>&1 | tail -10
```

- [ ] **步骤 9：Commit**

```bash
git add frontend/src/pages/system/AuditLogList.tsx
git commit -m "refactor(system/AuditLogList): unify Pro v6 patterns with useApiQuery"
```

---

### 任务 2：`system/UomsList.tsx`

**文件：** `frontend/src/pages/system/UomsList.tsx`

- [ ] **步骤 1-9：执行与任务 1 相同的 8 步模式**

```bash
head -80 frontend/src/pages/system/UomsList.tsx
grep -n "axios\|useRequest\|message\.\|actionRef\|Form\.useForm" frontend/src/pages/system/UomsList.tsx
```

**模式要点：**
- `import { message } from 'antd'` → `import { App } from 'antd'` + `const { message } = App.useApp()`
- `axios.get/axios.post` → `useApiQuery` / `useApiMutation`
- `actionRef.current?.reload()` → `queryClient.invalidateQueries`
- `Form.useForm()` → `ProForm.useForm()`

```bash
git add frontend/src/pages/system/UomsList.tsx
git commit -m "refactor(system/UomsList): unify Pro v6 patterns with useApiQuery"
```

---

### 任务 3：`system/ApprovalList.tsx`

**文件：** `frontend/src/pages/system/ApprovalList.tsx`

- [ ] **执行与任务 1 相同模式**

```bash
head -80 frontend/src/pages/system/ApprovalList.tsx
git add frontend/src/pages/system/ApprovalList.tsx
git commit -m "refactor(system/ApprovalList): unify Pro v6 patterns with useApiQuery"
```

---

### 任务 4：`warehouse/WarehouseList.tsx`

**文件：** `frontend/src/pages/warehouse/WarehouseList.tsx`

- [ ] **执行与任务 1 相同模式**

```bash
git add frontend/src/pages/warehouse/WarehouseList.tsx
git commit -m "refactor(warehouse/WarehouseList): unify Pro v6 patterns with useApiQuery"
```

---

### 任务 5：`tickets/TicketList.tsx`

**文件：** `frontend/src/pages/tickets/TicketList.tsx`

- [ ] **执行与任务 1 相同模式**

```bash
git add frontend/src/pages/tickets/TicketList.tsx
git commit -m "refactor(tickets/TicketList): unify Pro v6 patterns with useApiQuery"
```

---

### 任务 6：`notifications/index.tsx`

**文件：** `frontend/src/pages/notifications/index.tsx`

- [ ] **执行与任务 1 相同模式**

```bash
git add frontend/src/pages/notifications/index.tsx
git commit -m "refactor(notifications): unify Pro v6 patterns with useApiQuery"
```

---

### 任务 7：`finance/AccountList.tsx`

**文件：** `frontend/src/pages/finance/AccountList.tsx`

- [ ] **执行与任务 1 相同模式**

```bash
git add frontend/src/pages/finance/AccountList.tsx
git commit -m "refactor(finance/AccountList): unify Pro v6 patterns with useApiQuery"
```

---

### 任务 8：`finance/JournalEntryList.tsx`

**文件：** `frontend/src/pages/finance/JournalEntryList.tsx`

- [ ] **执行与任务 1 相同模式**

```bash
git add frontend/src/pages/finance/JournalEntryList.tsx
git commit -m "refactor(finance/JournalEntryList): unify Pro v6 patterns with useApiQuery"
```

---

### Phase 1 合入检查

- [ ] `npm run build` 成功
- [ ] `npx vitest run` 全部通过
- [ ] `npx tsc --noEmit` 无新增错误
- [ ] `git log --oneline` 确认 8 个 Tier 1 commit 已生成

---

## Phase 2 — Tier 2 页面（销售主线）

### 任务 9-17：销售模块列表页（OpportunityList / QuotationList / SalesOrderList / InvoiceList / PaymentList / DeliveryNoteList / PurchaseOrderList / ContractList / TargetList）

每页执行相同 8 步模式。

**关键差异点（销售模块）：**

1. **AI 风险标签** — `aiMap` state 需评估是否迁移到 `useApiQuery` 或保持独立 mutation
2. **PDF 导入** — `importSalesOrderPDF` 保持不变，改为 `useApiMutation`
3. **批量操作** — `batchDeleteSalesOrders` 同上

```bash
# 每个文件完成后单独 commit
git add frontend/src/pages/sales/OpportunityList.tsx
git commit -m "refactor(sales/OpportunityList): unify Pro v6 with useApiQuery"
# ... 重复至 TargetList
```

---

## Phase 3 — Tier 3 页面（重型页面）

### 任务 18：`products/index.tsx`

**文件：** `frontend/src/pages/products/index.tsx`（1839 行）

- [ ] **步骤 1：评估子组件**

先分析文件结构，识别内嵌的子组件（`ProductCustomerCodesCard`、`InventoryManage` 等），判断是否先拆分再迁移。

```bash
head -50 frontend/src/pages/products/index.tsx
grep -n "export default\|const.*= \|function " frontend/src/pages/products/index.tsx | head -30
```

- [ ] **Phase 3 完成后评估是否需要拆分**

---

## 合入标准（每次 PR）

- [ ] `npm run build` 成功
- [ ] `npx vitest run` 全部通过
- [ ] `npx tsc --noEmit` 无新增错误
- [ ] 无 `import { message } from 'antd'`（改用 `App.useApp()`）
- [ ] 无 `axios.get/post` 在页面组件内直接调用（API 走 `api/` 目录）
- [ ] ProTable 使用 `params` + `request` 模式，不用 `actionRef.reload()`

---

## 执行方式

**推荐：子代理驱动（subagent-driven-development）**

每个页面（任务 1-17）调度一个子代理，按顺序执行。每个子代理完成后审查再进行下一个。

**执行命令：**
```bash
# 启动子代理执行 Tier 1 任务
```

**Tier 1 完成后再执行 Tier 2（销售模块），最后 Tier 3（重型页面先拆分再迁）。**
