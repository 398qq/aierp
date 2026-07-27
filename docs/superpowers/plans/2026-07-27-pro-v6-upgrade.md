# Pro v6 完整升级 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 完整迁移 `aierp` 前端到 Ant Design Pro v6 生态（Umi Max 工具链 + 配置式路由 + ProLayout + ProComponents 最大化集成）

**架构：** 单 PR 8 阶段顺序实施。阶段 1-3 基础设施（工具链、入口、路由迁移），阶段 4 ProLayout，阶段 5-7 ProComponents 集成（Table/Form/Card+Statistic），阶段 8 E2E + 回归。

**技术栈：** Umi Max 4.6.x + `@ant-design/pro-components` 3.1.14 + `antd` 6.5 + React 19.2 + TypeScript 6.0 + Vite 替代（不再使用）+ Vitest + Playwright

---

## 文件结构

**创建（5 个文件）：**
- `frontend/config/config.ts` — Umi Max 路由清单 + 插件配置
- `frontend/src/access.ts` — 权限定义（`umi-plugin-access`）
- `frontend/src/layouts/ErpRouteLayout.tsx` — 根 layout（认证守卫 + ProLayout）
- `frontend/src/layouts/BlankLayout.tsx` — 公开 layout（Login/InquiryPortal）
- `frontend/playwright.config.ts` — Playwright e2e 配置（已存在则修改）

**修改（1 个文件）：**
- `frontend/package.json` — scripts + devDependencies（+ @umijs/max, @playwright/test）

**删除（4 个文件）：**
- `frontend/src/App.tsx` — 被 max 入口替代
- `frontend/src/routes/AppRoutes.tsx` — 被 Umi config 替代
- `frontend/src/router.ts` — 被 Umi 路由替代
- `frontend/src/layouts/MainLayout.tsx` — 被 ErpRouteLayout + ProLayout 替代

**业务文件（25+ 页面）：** 不修改 API/services/store/components；只重写各页面组件用 ProTable/ProForm/ProCard/Statistic。

---

## 阶段 1：工具链

### 任务 1.1：添加 @umijs/max 依赖

**文件：**
- 修改：`frontend/package.json:43-66`

- [ ] **步骤 1：编辑 package.json 加 umijs/max 和 cross-env**

修改 `frontend/package.json` 在 `devDependencies` 中：

```json
"devDependencies": {
  "@eslint/js": "^10.0.1",
  "@playwright/test": "^1.61.1",
  "@umijs/max": "^4.6.51",
  ...
  "cross-env": "^10.1.0",
  ...
}
```

- [ ] **步骤 2：npm install**

运行：`cd frontend && npm install --no-audit --no-fund`
预期：`added N packages`

- [ ] **步骤 3：验证 umijs/max 安装**

运行：`cd frontend && npx umi --version`
预期：`4.6.51` 或类似

- [ ] **步骤 4：Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "build(frontend): add @umijs/max 4.6.51 for Pro v6 toolchain"
```

### 任务 1.2：重写 scripts 用 max dev/build

**文件：**
- 修改：`frontend/package.json:6-11`

- [ ] **步骤 1：修改 scripts**

```json
"scripts": {
  "dev": "max dev",
  "build": "max build",
  "preview": "max preview --port 3002",
  "test": "vitest run",
  "test:watch": "vitest",
  "test:coverage": "vitest run --coverage",
  "lint": "eslint src/",
  "lint:fix": "eslint src/ --fix",
  "format": "prettier --write src/",
  "format:check": "prettier --check src/",
  "check-bundle-size": "bash scripts/check-bundle-size.sh",
  "analyze:bundle": "bash scripts/check-bundle-size.sh"
}
```

- [ ] **步骤 2：Commit**

```bash
git add frontend/package.json
git commit -m "build(frontend): switch scripts to max dev/build for Pro v6"
```

---

## 阶段 2：入口 + global

### 任务 2.1：创建 config/config.ts 最小配置

**文件：**
- 创建：`frontend/config/config.ts`

- [ ] **步骤 1：写最小配置**

```typescript
import { defineConfig } from '@umijs/max';

const backendPort = process.env.BACKEND_PORT ?? '8080';

export default defineConfig({
  title: 'AIERP',
  npmClient: 'npm',
  proxy: {
    '/api': {
      target: `http://localhost:${backendPort}`,
      changeOrigin: true,
    },
  },
  routes: [
    { path: '/login', component: '@/pages/auth/Login' },
    { path: '/inquiry', component: '@/pages/public/InquiryPortal' },
    {
      path: '/',
      component: '@/layouts/ErpRouteLayout',
      routes: [
        { path: '', component: '@/pages/dashboard/index' },
      ],
    },
    { path: '*', redirect: '/' },
  ],
});
```

- [ ] **步骤 2：Commit**

```bash
git add frontend/config/config.ts
git commit -m "feat(frontend): minimal Umi config with Login + InquiryPortal routes"
```

### 任务 2.2：创建 global.ts 全局样式入口

**文件：**
- 创建：`frontend/src/global.ts`

- [ ] **步骤 1：写 global.ts**

```typescript
import './styles/erp-table.css';
import './styles/erp-form.css';
import './styles/operational-ui.css';
import './styles/typography.css';
```

- [ ] **步骤 2：Commit**

```bash
git add frontend/src/global.ts
git commit -m "feat(frontend): global.ts for Umi-side-effect imports"
```

### 任务 2.3：删除 App.tsx、AppRoutes.tsx、router.ts、MainLayout.tsx

**文件：**
- 删除：`frontend/src/App.tsx`
- 删除：`frontend/src/routes/AppRoutes.tsx`
- 删除：`frontend/src/router.ts`
- 删除：`frontend/src/layouts/MainLayout.tsx`

- [ ] **步骤 1：删除文件**

```bash
git rm frontend/src/App.tsx \
       frontend/src/routes/AppRoutes.tsx \
       frontend/src/router.ts \
       frontend/src/layouts/MainLayout.tsx
```

- [ ] **步骤 2：验证 main.tsx 引用是否需要清理**

运行：`grep -rn "from.*App\|from.*router\|from.*MainLayout" frontend/src/`
预期：无引用（如果有，在后续任务中修复）

- [ ] **步骤 3：Commit**

```bash
git commit -m "refactor(frontend): delete obsolete App.tsx, AppRoutes, router, MainLayout"
```

---

## 阶段 3：路由迁移（25+ 路径）

### 任务 3.1：完整路由清单

**文件：**
- 修改：`frontend/config/config.ts`

- [ ] **步骤 1：用完整 25+ 路由替换 minimal 配置**

```typescript
import { defineConfig } from '@umijs/max';

const backendPort = process.env.BACKEND_PORT ?? '8080';

export default defineConfig({
  title: 'AIERP',
  npmClient: 'npm',
  proxy: {
    '/api': {
      target: `http://localhost:${backendPort}`,
      changeOrigin: true,
    },
  },
  routes: [
    // 公开入口
    { path: '/login', component: '@/pages/auth/Login', layout: false },
    { path: '/inquiry', component: '@/pages/public/InquiryPortal', layout: false },

    // 根 layout
    {
      path: '/',
      component: '@/layouts/ErpRouteLayout',
      routes: [
        { path: '', component: '@/pages/dashboard/index' },

        // Sales (12)
        { path: 'sales', redirect: '/sales/dashboard' },
        { path: 'sales/dashboard', component: '@/pages/sales/SalesDashboard' },
        { path: 'sales/opportunities', component: '@/pages/sales/OpportunityList' },
        { path: 'sales/opportunities/new', component: '@/pages/sales/OpportunityForm' },
        { path: 'sales/opportunities/:id', component: '@/pages/sales/OpportunityDetail' },
        { path: 'sales/opportunities/:id/edit', component: '@/pages/sales/OpportunityForm' },
        { path: 'sales/quotations', component: '@/pages/sales/QuotationList' },
        { path: 'sales/quotations/new', component: '@/pages/sales/QuotationForm' },
        { path: 'sales/quotations/:id', component: '@/pages/sales/QuotationDetail' },
        { path: 'sales/quotations/:id/edit', component: '@/pages/sales/QuotationForm' },
        { path: 'sales/orders', component: '@/pages/sales/SalesOrderList' },
        { path: 'sales/orders/new', component: '@/pages/sales/SalesOrderForm' },
        { path: 'sales/orders/:id', component: '@/pages/sales/SalesOrderDetail' },
        { path: 'sales/deliveries', component: '@/pages/sales/DeliveryNoteList' },
        { path: 'sales/deliveries/new', component: '@/pages/sales/DeliveryNoteForm' },
        { path: 'sales/deliveries/:id', component: '@/pages/sales/DeliveryNoteDetail' },
        { path: 'sales/invoices', component: '@/pages/sales/InvoiceList' },
        { path: 'sales/invoices/new', component: '@/pages/sales/InvoiceForm' },
        { path: 'sales/invoices/:id', component: '@/pages/sales/InvoiceDetail' },
        { path: 'sales/payments', component: '@/pages/sales/PaymentList' },
        { path: 'sales/payments/new', component: '@/pages/sales/PaymentForm' },
        { path: 'sales/contracts', component: '@/pages/sales/ContractList' },
        { path: 'sales/contracts/new', component: '@/pages/sales/ContractForm' },
        { path: 'sales/contracts/:id', component: '@/pages/sales/ContractDetail' },
        { path: 'sales/targets', component: '@/pages/sales/TargetList' },
        { path: 'sales/targets/new', component: '@/pages/sales/TargetForm' },
        { path: 'sales/purchase-orders', component: '@/pages/sales/PurchaseOrderList' },
        { path: 'sales/purchase-orders/new', component: '@/pages/sales/PurchaseOrderForm' },
        { path: 'sales/purchase-orders/:id', component: '@/pages/sales/PurchaseOrderDetail' },
        { path: 'sales/inquiry-auto-reply', component: '@/pages/sales/InquiryAutoReply' },

        // Customers (8)
        { path: 'customers', component: '@/pages/customers/CustomerListPage' },
        { path: 'customers/new', component: '@/pages/customers/CustomerNew' },
        { path: 'customers/stats', component: '@/pages/customers/CustomerDashboard' },
        { path: 'customers/intelligence', component: '@/pages/customers/CustomerIntelligenceDashboard' },
        { path: 'customers/workbench', component: '@/pages/customers/CustomerAIWorkbench' },
        { path: 'customers/segments', component: '@/pages/customers/CustomerSegments' },
        { path: 'customers/:id', component: '@/pages/customers/CustomerDetail' },
        { path: 'customers/:id/360', component: '@/pages/customers/Customer360' },

        // Products (5)
        { path: 'products', component: '@/pages/products/index' },
        { path: 'products/new', component: '@/pages/products/ProductEdit' },
        { path: 'products/:id', component: '@/pages/products/ProductDetail' },
        { path: 'products/:id/edit', component: '@/pages/products/ProductEdit' },
        { path: 'products/:id/360', component: '@/pages/products/Product360' },

        // Suppliers (4)
        { path: 'suppliers', component: '@/pages/suppliers/index' },
        { path: 'suppliers/dashboard', component: '@/pages/suppliers/SupplierDashboard' },
        { path: 'suppliers/:id', component: '@/pages/suppliers/SupplierDetail' },
        { path: 'suppliers/:id/360', component: '@/pages/suppliers/Supplier360' },

        // Brands (4)
        { path: 'brands', component: '@/pages/brands/index' },
        { path: 'brands/dashboard', component: '@/pages/brands/BrandDashboard' },
        { path: 'brands/:id', component: '@/pages/brands/BrandDetail' },
        { path: 'brands/:id/edit', component: '@/pages/brands/BrandEdit' },

        // Inventory (3)
        { path: 'inventory', component: '@/pages/inventory/index' },
        { path: 'inventory/expiring', component: '@/pages/inventory/BatchExpiring' },
        { path: 'inventory/recall', component: '@/pages/inventory/BatchRecall' },

        // Warehouse (3)
        { path: 'warehouse', component: '@/pages/warehouse/index' },
        { path: 'warehouse/traceability', component: '@/pages/warehouse/BatchTraceability' },
        { path: 'warehouse/warehouses', component: '@/pages/warehouse/WarehouseList' },
        { path: 'warehouse/ledger', component: '@/pages/warehouse/InventoryLedger' },
        { path: 'warehouse/batches', component: '@/pages/warehouse/InventoryBatches' },

        // Tickets (3)
        { path: 'tickets', component: '@/pages/tickets/TicketList' },
        { path: 'tickets/new', component: '@/pages/tickets/TicketForm' },
        { path: 'tickets/:id', component: '@/pages/tickets/TicketDetail' },

        // Finance (5)
        { path: 'finance/invoices', component: '@/pages/finance/InvoiceList' },
        { path: 'finance/payments', component: '@/pages/finance/PaymentList' },
        { path: 'finance/journal-entries', component: '@/pages/finance/JournalEntryList' },
        { path: 'finance/journal-entries/new', component: '@/pages/finance/JournalEntryForm' },
        { path: 'finance/commission-schemes', component: '@/pages/finance/CommissionSchemeList' },

        // Other (10)
        { path: 'notifications', component: '@/pages/notifications/index' },
        { path: 'reports', component: '@/pages/reports/index' },
        { path: 'import-export', component: '@/pages/import-export/index' },
        { path: 'settings', component: '@/pages/settings/index' },
        { path: 'procurement', component: '@/pages/procurement/index' },
        { path: 'ai/chat', component: '@/pages/ai/Chat' },
        { path: 'ai/insights', component: '@/pages/ai/Insights' },
        { path: 'system/users', component: '@/pages/system/users/UserList' },
        { path: 'dashboard/watchtower', component: '@/pages/dashboard/WatchtowerDashboard' },
        { path: 'dashboard/global-360', component: '@/pages/dashboard/Global360' },
      ],
    },

    { path: '*', redirect: '/' },
  ],
});
```

- [ ] **步骤 2：验证路由文件存在**

运行：`cd frontend && find src/pages -name "*.tsx" | wc -l`
预期：≥ 50（页面文件）

- [ ] **步骤 3：Commit**

```bash
git add frontend/config/config.ts
git commit -m "feat(frontend): complete 70+ route manifest in Umi config"
```

---

## 阶段 4：ProLayout 根 layout

### 任务 4.1：创建 BlankLayout

**文件：**
- 创建：`frontend/src/layouts/BlankLayout.tsx`

- [ ] **步骤 1：写 BlankLayout**

```typescript
import { Outlet } from '@umijs/max';

export default function BlankLayout(): JSX.Element {
  return <Outlet />;
}
```

- [ ] **步骤 2：Commit**

```bash
git add frontend/src/layouts/BlankLayout.tsx
git commit -m "feat(frontend): BlankLayout for public routes (login, inquiry)"
```

### 任务 4.2：创建 ErpRouteLayout（ProLayout + 认证守卫）

**文件：**
- 创建：`frontend/src/layouts/ErpRouteLayout.tsx`

- [ ] **步骤 1：写 ErpRouteLayout**

```typescript
import { useEffect } from 'react';
import { Spin } from 'antd';
import { ProLayout } from '@ant-design/pro-components';
import { Outlet, Navigate, useLocation } from '@umijs/max';
import { useAuthStore } from '@/store/auth';
import { menuItems } from './menuConfig';

export default function ErpRouteLayout(): JSX.Element {
  const username = useAuthStore((s) => s.username);
  const loading = useAuthStore((s) => s.loading);
  const init = useAuthStore((s) => s.init);
  const location = useLocation();

  useEffect(() => {
    void init();
  }, [init]);

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '120px auto' }} />;
  }
  if (!username) {
    return <Navigate to="/login" replace />;
  }

  return (
    <ProLayout
      layout="mix"
      title="AIERP"
      logo="/icon-192.png"
      location={location}
      menu={{ type: 'group', items: menuItems }}
      menuDataRender={() => menuItems}
      contentWidth="Fluid"
      siderWidth={224}
      fixedHeader
    >
      <Outlet />
    </ProLayout>
  );
}
```

- [ ] **步骤 2：创建 menuConfig.ts**

```typescript
// frontend/src/layouts/menuConfig.ts
import type { MenuProps } from 'antd';

export const menuItems: MenuProps['items'] = [
  { key: '/', icon: 'DashboardOutlined', label: 'Dashboard' },
  { key: '/customers', icon: 'TeamOutlined', label: 'Customers' },
  { key: '/sales', icon: 'ShopOutlined', label: 'Sales' },
  { key: '/products', icon: 'StockOutlined', label: 'Products' },
  { key: '/suppliers', icon: 'ShopOutlined', label: 'Suppliers' },
  { key: '/brands', icon: 'ShopOutlined', label: 'Brands' },
  { key: '/inventory', icon: 'InboxOutlined', label: 'Inventory' },
  { key: '/warehouse', icon: 'HomeOutlined', label: 'Warehouse' },
  { key: '/tickets', icon: 'AlertOutlined', label: 'Tickets' },
  { key: '/finance', icon: 'AccountBookOutlined', label: 'Finance' },
  { key: '/notifications', icon: 'BellOutlined', label: 'Notifications' },
  { key: '/reports', icon: 'BarChartOutlined', label: 'Reports' },
  { key: '/ai/chat', icon: 'RobotOutlined', label: 'AI Assistant' },
  { key: '/settings', icon: 'SettingOutlined', label: 'Settings' },
];
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/layouts/
git commit -m "feat(frontend): ErpRouteLayout with ProLayout + auth guard"
```

### 任务 4.3：创建 access.ts 权限定义

**文件：**
- 创建：`frontend/src/access.ts`

- [ ] **步骤 1：写 access.ts**

```typescript
export default function access(initialState: { currentUser?: { roles?: string[] } }) {
  const { currentUser } = initialState ?? {};
  const roles = currentUser?.roles ?? [];
  return {
    canAdmin: roles.includes('admin'),
    canSales: roles.includes('admin') || roles.includes('sales'),
    canFinance: roles.includes('admin') || roles.includes('finance'),
  };
}
```

- [ ] **步骤 2：Commit**

```bash
git add frontend/src/access.ts
git commit -m "feat(frontend): access control definitions for umi-plugin-access"
```

---

## 阶段 5：ProTable 标准化（8 个核心页）

### 任务 5.1：CustomerListPage 用 ProTable

**文件：**
- 修改：`frontend/src/pages/customers/CustomerListPage.tsx`

- [ ] **步骤 1：用 ProTable 替换 Table**

保留现有 API 调用和数据流。替换 `<Table>` 为 `<ProTable>`，使用 `request` 属性自动加载数据。

```tsx
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';

const columns: ProColumns<Customer>[] = [
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Email', dataIndex: 'email', key: 'email' },
  { title: 'Phone', dataIndex: 'phone', key: 'phone' },
  {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
    valueEnum: {
      active: { text: 'Active', status: 'Success' },
      inactive: { text: 'Inactive', status: 'Default' },
    },
  },
  {
    title: 'Action',
    key: 'action',
    valueType: 'option',
    render: (_, record) => [
      <a key="view" href={`/customers/${record.id}`}>View</a>,
      <a key="edit" href={`/customers/${record.id}/edit`}>Edit</a>,
    ],
  },
];

export default function CustomerListPage(): JSX.Element {
  return (
    <ProTable<Customer>
      columns={columns}
      request={async (params) => {
        const res = await getCustomers(params);
        return { data: res.data.items, success: true, total: res.data.total };
      }}
      rowKey="id"
      search={{ labelWidth: 'auto' }}
      pagination={{ pageSize: 20 }}
      dateFormatter="string"
    />
  );
}
```

- [ ] **步骤 2：验证测试通过**

运行：`cd frontend && npx vitest run`
预期：PASS

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/pages/customers/CustomerListPage.tsx
git commit -m "refactor(customers): CustomerListPage uses ProTable"
```

### 任务 5.2-5.8：剩余 7 个 ProTable 页面

每个页面遵循相同模式（步骤 1 写 ProTable，步骤 2 测试，步骤 3 commit）：

- **任务 5.2**: `frontend/src/pages/products/index.tsx`（products 列表）
- **任务 5.3**: `frontend/src/pages/suppliers/index.tsx`
- **任务 5.4**: `frontend/src/pages/brands/index.tsx`
- **任务 5.5**: `frontend/src/pages/sales/OpportunityList.tsx`
- **任务 5.6**: `frontend/src/pages/sales/QuotationList.tsx`
- **任务 5.7**: `frontend/src/pages/inventory/index.tsx`
- **任务 5.8**: `frontend/src/pages/warehouse/index.tsx`

每个任务的步骤：

- [ ] **步骤 1：用 ProTable 替换现有 Table 组件**（参考 5.1）
- [ ] **步骤 2：cd frontend && npx vitest run**（预期 PASS）
- [ ] **步骤 3：commit**

---

## 阶段 6：ProForm 标准化（6 个表单页）

### 任务 6.1：OpportunityForm 用 ProForm

**文件：**
- 修改：`frontend/src/pages/sales/OpportunityForm.tsx`

- [ ] **步骤 1：用 ProForm 替换 Form**

```tsx
import { ProForm, ProFormText, ProFormSelect, ProFormDigit, ProFormTextArea } from '@ant-design/pro-components';

export default function OpportunityForm(): JSX.Element {
  return (
    <ProForm
      onFinish={async (values) => {
        await createOpportunity(values);
        message.success('Opportunity created');
        history.push('/sales/opportunities');
      }}
    >
      <ProFormText name="name" label="Opportunity Name" rules={[{ required: true }]} />
      <ProFormSelect name="customer_id" label="Customer" request={fetchCustomerOptions} />
      <ProFormDigit name="amount" label="Amount" min={0} />
      <ProFormTextArea name="description" label="Description" />
    </ProForm>
  );
}
```

- [ ] **步骤 2：cd frontend && npx vitest run**（预期 PASS）
- [ ] **步骤 3：commit**

### 任务 6.2-6.6：剩余 5 个 ProForm 页面

- **任务 6.2**: `frontend/src/pages/sales/QuotationForm.tsx`
- **任务 6.3**: `frontend/src/pages/sales/SalesOrderForm.tsx`
- **任务 6.4**: `frontend/src/pages/customers/CustomerNew.tsx`
- **任务 6.5**: `frontend/src/pages/products/ProductEdit.tsx`
- **任务 6.6**: `frontend/src/pages/brands/BrandEdit.tsx`

每个：步骤 1 ProForm 替换 / 步骤 2 测试 / 步骤 3 commit。

---

## 阶段 7：ProCard + Statistic（dashboard 类页）

### 任务 7.1：dashboard/index.tsx 用 Statistic

**文件：**
- 修改：`frontend/src/pages/dashboard/index.tsx`

- [ ] **步骤 1：用 Statistic + ProCard 替换现有 dashboard**

```tsx
import { Statistic, Row, Col } from 'antd';
import { ProCard } from '@ant-design/pro-components';

export default function Dashboard(): JSX.Element {
  return (
    <ProCard split="vertical">
      <Row gutter={16}>
        <Col span={6}>
          <ProCard>
            <Statistic title="Active Customers" value={1234} />
          </ProCard>
        </Col>
        <Col span={6}>
          <ProCard>
            <Statistic title="Open Opportunities" value={56} valueStyle={{ color: '#3f8600' }} />
          </ProCard>
        </Col>
        <Col span={6}>
          <ProCard>
            <Statistic title="This Month Revenue" value={9876.54} precision={2} prefix="$" />
          </ProCard>
        </Col>
        <Col span={6}>
          <ProCard>
            <Statistic title="Conversion Rate" value={23.4} suffix="%" />
          </ProCard>
        </Col>
      </Row>
    </ProCard>
  );
}
```

- [ ] **步骤 2：cd frontend && npx vitest run**（预期 PASS）
- [ ] **步骤 3：commit**

### 任务 7.2-7.4：其余 dashboard 页

- **任务 7.2**: `frontend/src/pages/dashboard/WatchtowerDashboard.tsx`
- **任务 7.3**: `frontend/src/pages/dashboard/Global360.tsx`
- **任务 7.4**: `frontend/src/pages/customers/CustomerDashboard.tsx`

每个：步骤 1 ProCard + Statistic / 步骤 2 测试 / 步骤 3 commit。

---

## 阶段 8：E2E + 回归

### 任务 8.1：Playwright e2e 关键流

**文件：**
- 创建：`frontend/e2e/critical-flows.spec.ts`

- [ ] **步骤 1：写 5 个 e2e 流**

```typescript
import { test, expect } from '@playwright/test';

test('login flow', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('/');
});

test('customer list flow', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.goto('/customers');
  await expect(page.locator('.ant-pro-table')).toBeVisible();
});

test('customer detail flow', async ({ page }) => {
  // login + 访问 detail
});

test('opportunity form flow', async ({ page }) => {
  // 登录 + 访问表单 + 填写 + 提交
});

test('submit + redirect flow', async ({ page }) => {
  // 验证表单提交后跳转
});
```

- [ ] **步骤 2：运行 e2e**

运行：`cd frontend && npx playwright test`
预期：5/5 PASS

- [ ] **步骤 3：Commit**

```bash
git add frontend/e2e/
git commit -m "test(frontend): Playwright e2e critical flows"
```

### 任务 8.2：完整回归

- [ ] **步骤 1：make lint**

```bash
make lint
```

预期：0 errors

- [ ] **步骤 2：make test**

```bash
make test
```

预期：pytest 1589+ pass / vitest 161+ pass

- [ ] **步骤 3：手动 dev 服务器验证**

```bash
make dev
curl http://localhost:8080/health
curl http://localhost:3002/
```

预期：都返回 200

- [ ] **步骤 4：commit regression test result**

```bash
git commit --allow-empty -m "test: regression verification post Pro v6 upgrade"
```

### 任务 8.3：清理 staging 状态

- [ ] **步骤 1：git status 检查**

```bash
git status
```

预期：clean（除非有未跟踪的生成文件）

- [ ] **步骤 2：git push**

```bash
git push origin master
```

预期：push 成功

---

## 验收清单

- [ ] `max dev` 启动成功，http://localhost:3002 渲染 Login
- [ ] 70+ 路由在 Pro v6 下可访问
- [ ] ProTable 在 customers/sales/products 列表工作
- [ ] ProForm 在 opportunity/quotation/order 提交成功
- [ ] Statistic 在 dashboard 正确显示
- [ ] 旧 App.tsx/AppRoutes/MainLayout 删除
- [ ] CI 全过：ruff + mypy + tsc + eslint + pytest + vitest + e2e
- [ ] Backend 端无变更

---

**完成时间估计：** 2 周单人
**下一步：** 调用 subagent-driven-development 或 executing-plans 执行。

---

## 已知省略（参考模式扩展）

阶段 5-7 包含 18 个核心页面任务（ProTable 8 + ProForm 6 + ProCard/Statistic 4）。剩余 7+ 个页面（如 supplier detail、brand detail、ticket list/detail、finance journal entry list、procurement、import-export、reports、settings、ai insights、user list 等）未列具体任务——**实施时**按任务 5.1/6.1/7.1 的模式适配到对应文件。

如果工程师在实施剩余页面时遇到**新模式**（如复杂的 ProDescriptions、StepsForm、ModalForm with drawer），应在该页面新增独立任务而非套用简化模式。