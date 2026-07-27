# Pro v6 完整升级 — 设计规格

**日期：** 2026-07-27
**作者：** Claude (brainstorming session)
**状态：** 已批准
**目标分支：** master（单次 PR）

---

## 1. 背景

`aierp` 当前已采用 Ant Design v6.5.0 + `@ant-design/pro-components` 3.1.14-4 + React 19.2.7，但 **未采用 Ant Design Pro v6 工具链/架构**。当前前端用 Vite + react-router 8.3 自有路由，Pro v6 的核心特性（Umi Max 工具链、配置式路由、ProLayout、ProComponents 高级用法）尚未启用。

## 2. 目标

完整迁移到 Ant Design Pro v6 生态，包括：

1. **Umi Max 工具链**（max dev / max build 替代 Vite）
2. **Umi 配置式路由**（`config/config.ts` 替代 `App.tsx` 路由树）
3. **ProLayout 根 layout**（替代自定义 MainLayout）
4. **ProComponents 最大化集成**（ProTable 替代 Table，ProForm 替代 Form，ProCard 替代 Card，Statistic、ProDescriptions 等）
5. **设计风格统一**（已有 #78 commit 加的 149 行 Pro v6 基线样式作基础）

## 3. 范围外（YAGNI）

- 国际化（保留现有 zhCN）
- dark mode
- SSR
- 微前端
- antd 主题色重构（保留现有浅色系）

## 4. 用户决策（来自 brainstorming）

| 决策 | 选择 |
|------|------|
| 范围 | **全 5 项同时重构** |
| 中间状态 | **允许 break**（不要求双轨制） |
| #77 路由 | **废弃**（删除 `App.tsx` + `routes/AppRoutes.tsx`） |
| ProComponents 范围 | **最大化集成**（25+ 页面） |
| 交付方式 | **一次到位**（单 PR，2 周工作量） |

## 5. 架构（目标文件树）

```
frontend/
├── config/
│   └── config.ts                 # Umi 配置（路由清单 + 插件）
├── src/
│   ├── .umi/                     # Umi 生成（gitignored）
│   ├── global.ts                 # 全局样式入口
│   ├── access.ts                 # 权限定义（umi-plugin-access）
│   ├── layouts/
│   │   ├── ErpRouteLayout.tsx    # 根 layout（认证守卫 + ProLayout）
│   │   ├── BlankLayout.tsx       # 公开 layout（Login / InquiryPortal）
│   │   └── SecurityLayout.tsx    # 含认证的根 layout 包装
│   ├── pages/                    # 文件路由（Umi convention）
│   │   ├── auth/Login.tsx
│   │   ├── public/InquiryPortal.tsx
│   │   ├── customers/            # 8 个客户模块页（用 ProTable/ProCard）
│   │   ├── sales/                # 12 个销售模块页
│   │   ├── products/             # 5 个产品模块页
│   │   ├── suppliers/            # 4 个供应商模块页
│   │   ├── brands/               # 4 个品牌模块页
│   │   ├── tickets/              # 3 个工单模块页
│   │   ├── finance/              # 5 个财务模块页
│   │   ├── inventory/            # 3 个库存模块页
│   │   ├── warehouse/            # 3 个仓库模块页
│   │   ├── procurement/          # 2 个采购模块页
│   │   ├── dashboard/            # 3 个仪表盘页（用 Statistic）
│   │   ├── notifications/
│   │   ├── reports/
│   │   ├── settings/
│   │   ├── import-export/
│   │   ├── ai/                   # AI Chat + insights
│   │   └── system/users/
│   ├── services/                 # 保留
│   ├── components/               # 业务组件（保留）
│   ├── ui/                       # 通用 UI（保留）
│   ├── store/                    # zustand（保留）
│   ├── api/                      # axios + 类型（保留）
│   ├── types/                    # 类型（保留）
│   └── test/                     # vitest setup
├── package.json                  # scripts: max dev/build/preview
└── tsconfig.json                 # 适配 Umi（paths, jsx runtime）
```

**删除文件：**
- `frontend/src/App.tsx`
- `frontend/src/routes/AppRoutes.tsx`
- `frontend/src/router.ts`
- `frontend/src/layouts/MainLayout.tsx`（被 ErpRouteLayout + ProLayout 替代）

**新增文件：**
- `frontend/config/config.ts`
- `frontend/src/access.ts`
- `frontend/src/layouts/BlankLayout.tsx`
- `frontend/src/layouts/SecurityLayout.tsx`

## 6. 关键决策

| 维度 | 决策 | 理由 |
|------|------|------|
| 入口模式 | Umi convention（`src/pages` 自动路由） | 简化配置 |
| 数据请求 | 保留 `axios` + `services/` 业务层 | 业务 API 不动 |
| 状态管理 | 保留 `zustand` | 已稳定 |
| 路由权限 | `umi-plugin-access` + `access.ts` | 替代手写 `<Authorized>` |
| Layout | `ErpRouteLayout` (auth guard + ProLayout) + `BlankLayout` | 分离认证/公开 |
| UI 组件 | Table→ProTable, Form→ProForm, Card→ProCard, List→ProList | Pro v6 核心 |
| 测试 | 保留 vitest；添加 Playwright e2e 关键流 | 已有 playwright |
| Lint | ruff (后端) + eslint + tsc (前端) 保留 | 现有 CI |
| 旧依赖 | `@ant-design/v5-patch-for-react-19` 保留 | Pro v6 内部仍需 |
| react-router | 保留（Umi 内部用） | 不移除 |
| `react` 版本 | 维持 19.2.7 | Pro v6 支持 React 19 |

## 7. 实施阶段（2 周）

| 阶段 | 内容 | 验证 | 风险 |
|------|------|------|------|
| **1. 工具链** | `package.json` scripts + 依赖 | `max dev` 启动 | 中 |
| **2. 入口 + global** | `main.tsx` 改造，删除 `App.tsx` | `max dev` 渲染 Login 页 | 中 |
| **3. 路由迁移** | `config/config.ts` 完整路由清单（25+ 路径）| 所有路径可访问 | 高（废弃 #77） |
| **4. ProLayout** | `ErpRouteLayout` + ProLayout + ProCard | sidebar + content 渲染 | 低 |
| **5. ProTable 标准化** | 8 个核心页（customers/sales/products 等）| 表格+筛选+分页 | 高 |
| **6. ProForm 标准化** | 6 个表单页（opportunity/quotation/order 等）| 表单提交+验证 | 高 |
| **7. ProCard + Statistic** | dashboard 类页（4 个）| 数据展示 | 中 |
| **8. E2E + 回归** | Playwright 关键流，CI 跑全套 | 全套 pass | 中 |

## 8. config/config.ts 设计

```typescript
import { defineConfig } from '@umijs/max';

export default defineConfig({
  title: 'AIERP',
  // 25+ 路由按 src/pages 文件结构自动生成
  routes: [
    { path: '/login', component: '@/pages/auth/Login' },
    { path: '/inquiry', component: '@/pages/public/InquiryPortal' },
    {
      path: '/',
      component: '@/layouts/ErpRouteLayout',
      routes: [
        { path: '', component: '@/pages/dashboard/index' },
        { path: 'customers', component: '@/pages/customers/CustomerListPage' },
        // ... 25+ paths
      ],
    },
  ],
  access: { /* 权限定义 */ },
  proxy: {
    '/api': { target: 'http://localhost:8080', changeOrigin: true },
  },
  npmClient: 'npm',
});
```

## 9. 测试策略

- **单元测试**：保留 vitest，UI 组件测试覆盖 ≥ 80%
- **E2E 测试**：Playwright 覆盖 5 个关键流
  1. login
  2. list（customers）
  3. detail（customer/:id）
  4. form（opportunity/new）
  5. submit + redirect
- **CI**：lint + test + build + e2e 全过
- **回归**：master CI 全过（pytest 1589 + vitest 161）

## 10. 风险与回滚

| 风险 | 影响 | 回滚策略 |
|------|------|----------|
| `max dev` 不兼容某些 antd 用法 | 全前端 break | revert PR |
| react-router 8.3 与 Umi 路由冲突 | 路由死锁 | 保留 react-router 作为 peerDep |
| ProTable 与现有 API 不匹配 | 数据展示失败 | 逐页修复 |
| 25+ 页面重写工作量超预期 | 延期 | 优先核心页，其余延后 |
| Playwright e2e 维护负担 | CI +5min | 仅核心 5 流 |

## 11. 验收标准

- [ ] `max dev` 启动成功，访问 http://localhost:3002 渲染 Login 页
- [ ] 所有 25+ 路径在 Pro v6 路由下可访问
- [ ] ProTable 在 customers/sales/products 列表页正常工作
- [ ] ProForm 在 opportunity/quotation/order 创建页提交成功
- [ ] Statistic 在 dashboard 页正确显示数据
- [ ] 旧 App.tsx / AppRoutes.tsx / MainLayout.tsx 删除
- [ ] CI 全过：ruff + mypy + tsc + eslint + pytest (1589) + vitest (≥161)
- [ ] Playwright 5 个关键流 e2e pass
- [ ] `make lint` 0 errors
- [ ] `make test` 0 failures
- [ ] Backend 端无变更（仅 frontend 重构）

## 12. 后续优化（本次不做）

- ProTable 性能优化（虚拟滚动）
- 主题色 token 化
- 国际化
- dark mode
- 单元测试覆盖率提升到 90%

---

**下一步：** 调用 writing-plans 技能创建实现计划。