# Pro v6 UI 重构策略文档

> 日期：2026-07-30
> 目标：统一全部 79 个页面的 Pro v6 实现模式，消除混用的旧 antd 写法

---

## 一、现状分析

### 1.1 范围

79 个页面使用 ProComponents（`ProTable` / `ProForm` / `ProCard`），占总页面数 140 的 56%。

### 1.2 典型混用模式

所有 79 个页面存在以下一种或多种旧写法：

| 问题 | 现状 | 目标模式 |
|------|------|---------|
| **数据获取** | `axios.get()` 直接调用、`ahooks useRequest` | `useApiQuery`（React Query 封装） |
| **提示消息** | `import { message } from 'antd'` 静态调用 | `const { message } = App.useApp()` |
| **Filter 状态** | `useState` 存 `status/q/page` | ProTable `params` + `useApiQuery` 自动同步 |
| **刷新机制** | `actionRef.current?.reload()` | `queryClient.invalidateQueries(['key'])` |
| **表单** | `Form.useForm()` | `ProForm.useForm()` |
| **Modal** | `Modal.confirm({...})` | `App.useApp()` + `Modal.confirm`（保留交互，提升 API） |

### 1.3 已验证的正确模式

参考文件：`frontend/src/pages/customers/CustomerListPage.tsx`

```tsx
// ✅ 数据层
import { useApiQuery } from "@/lib/queries";
const { data, isLoading } = useApiQuery(['customerList', params], () =>
  getCustomers(params)
);

// ✅ 消息提示
import { App } from "antd";
const { message } = App.useApp();
message.success("操作成功");

// ✅ Filter → params 合一
<ProTable
  params={filterParams}
  request={async (params) => {
    // params 包含所有 filter 状态，无需额外 useState
    return { data, success: true, total };
  }}
/>
```

---

## 二、目标模式

### 2.1 统一技术栈

| 层级 | 技术 |
|------|------|
| 数据获取 | `useApiQuery` / `useApiMutation`（`frontend/src/lib/queries.ts`） |
| 列表组件 | `ProTable` |
| 表单组件 | `ProForm` |
| 布局组件 | `ProCard` |
| 消息提示 | `App.useApp()` + `message` / `notification` |
| 状态管理 | React Query（服务端状态）+ Zustand（客户端状态） |
| 页面布局 | `ModuleShell` / `PageHeader` |

### 2.2 ProTable 标准结构

```tsx
import { ProTable } from "@ant-design/pro-components";
import { useApiQuery, useApiMutation, useQueryClient } from "@/lib/queries";
import { App } from "antd";

export default function EntityList() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // ✅ 统一数据获取
  const { data, isLoading, params } = useApiQuery(
    ['entityList', filterParams],
    () => getEntities(filterParams),
    { keepPreviousData: true }
  );

  // ✅ 统一刷新（invalidate 替代 reload）
  const mutation = useApiMutation(
    (id: number) => deleteEntity(id),
    {
      onSuccess: () => {
        message.success("删除成功");
        queryClient.invalidateQueries({ queryKey: ['entityList'] });
      },
    }
  );

  return (
    <ProTable
      params={filterParams}
      request={async (reqParams) => {
        // ProTable 自动把 reqParams merge 进 filterParams
        return {
          data: data?.list ?? [],
          success: true,
          total: data?.total ?? 0,
        };
      }}
      columns={columns}
      rowSelection={rowSelection}
    />
  );
}
```

### 2.3 ProForm 标准结构

```tsx
import { ProForm, ProFormText, ProFormSelect } from "@ant-design/pro-components";
import { App } from "antd";
import { useApiMutation } from "@/lib/queries";

export default function EntityForm({ id }: { id?: number }) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const { run, loading } = useApiMutation(
    (values: FormValues) => id ? updateEntity(id, values) : createEntity(values),
    {
      onSuccess: () => {
        message.success(id ? "更新成功" : "创建成功");
        queryClient.invalidateQueries({ queryKey: ['entityList'] });
      },
    }
  );

  return (
    <ProForm
      onFinish={async (values) => { await run(values); return true; }}
      submitter={{ submitButtonProps: { loading } }}
    >
      <ProFormText name="name" label="名称" rules={[{ required: true }]} />
      <ProFormSelect name="status" label="状态" options={statusOptions} />
    </ProForm>
  );
}
```

---

## 三、重构阶段

### Phase 1 — 数据层统一（核心）

**目标**：把 `axios`/`useRequest` 全部替换为 `useApiQuery`

**影响文件**：79 个使用 ProTable 的页面

**标准动作**：
1. `import { useApiQuery } from "@/lib/queries"`
2. 把 `axios.get().then()` 替换为 `useApiQuery(['key', params], () => api(params))`
3. 把 `message.error(getApiErrorMessage(e))` 改为 `const { message } = App.useApp(); message.error(...)`
4. 把 `actionRef.current?.reload()` 改为 `queryClient.invalidateQueries({ queryKey: ['key'] })`
5. 删除废弃的 `useState` filter 状态（ProTable params 自动同步）

**预计工时**：40-60 小时（79 页 × 30-45 分钟/页）

### Phase 2 — UI 层统一

**目标**：消除剩余的裸 `antd Table`、非标准 Form 写法

**影响文件**：评估后确定（Phase 1 完成后统计剩余问题）

**标准动作**：
1. 裸 `Table` → `ProTable`
2. 裸 `Form` + `Modal` → `ProForm` 在 Drawer/Modal 内
3. `Modal.confirm` 保留，message 改用 `App.useApp()`

**预计工时**：Phase 1 完成后评估

### Phase 3 — 收尾

- 删除 `ahooks useRequest` 相关 import（如有）
- 确认无 `axios.get/post` 在页面组件内直接调用（API 应在 `api/` 目录）
- 运行 `make lint` + `make test` 全量验证

---

## 四、页面优先级

### Tier 1 — 高价值低风险（先做）

已有 React Query 基础设施铺垫、模式清晰的页面：

| 模块 | 文件 |
|------|------|
| system | `AuditLogList`, `UomsList`, `ApprovalList` |
| warehouse | `WarehouseList` |
| tickets | `TicketList` |
| notifications | `index` |
| finance | `AccountList`, `JournalEntryList` |
| customers | `FollowUpList`（已部分完成） |

### Tier 2 — 销售主线（核心业务）

日常高频使用：

| 文件 |
|------|
| `sales/OpportunityList` |
| `sales/QuotationList` |
| `sales/SalesOrderList` |
| `sales/InvoiceList` |
| `sales/PaymentList` |
| `sales/DeliveryNoteList` |
| `sales/PurchaseOrderList` |
| `sales/ContractList` |
| `sales/TargetList` |

### Tier 3 — 重型页面（最后做）

文件大、子模块多，先拆后迁：

| 文件 | 行数 | 备注 |
|------|------|------|
| `products/index` | 1839 | 内嵌多组件，先拆模块 |
| `brands/index` | 1797 | 多视图，需分层 |
| `suppliers/index` | 1272 | 含 Compare/Dashboard |
| `inventory/index` | 807 | 多种列表聚合 |
| `dashboard/index` | 964 | 仪表盘卡片，各自 query |

---

## 五、合入标准

每次 PR 合入前必须满足：

- [ ] `npm run build` 成功
- [ ] `npx vitest run` 全部通过
- [ ] `npx tsc --noEmit` 无新增错误
- [ ] 无 `axios.get/post` 在页面组件内直接调用（API 走 `api/` 目录）
- [ ] 无静态 `import { message } from 'antd'`，改用 `App.useApp()`
- [ ] ProTable 使用 `params` + `request` 模式，不用 `actionRef.reload()`

---

## 六、风险与缓解

| 风险 | 缓解 |
|------|------|
| 79 页改动量大、回归风险高 | 分 Tier 小步快走，每 PR 不超过 5 页 |
| `useApiQuery` 与 ProTable `request` 混用复杂度 | 参照 `CustomerListPage.tsx` 模板 |
| 大量文件并发修改 | 每个 Phase 单独分支，最后合到 master |
