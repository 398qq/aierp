# Pro v6 全面升级

## 概述

完成 `aierp` 前端到 Ant Design Pro v6 生态的全面升级。包含 Umi Max 工具链、ProLayout、ProTable、ProForm、ProCard 集成。

## 范围

- **基础设施**：@umijs/max + Umi Max 工具链
- **入口与路由**：config-based 路由 + 90+ 路由
- **Layouts**：ErpRouteLayout（认证守卫 + ProLayout）+ BlankLayout
- **ProForm 迁移**：6 个表单
  - OpportunityForm / QuotationForm / SalesOrderForm
  - CustomerNew / ProductEdit / BrandEdit
- **ProTable 迁移**：4 个列表页
  - OpportunityList / ProductsList / BrandsList / WarehouseList
- **Dashboard 迁移**：ProCard + Statistic
  - Dashboard KPI cards / Watchtower / Global360
- **TypeScript 修复**：批量修复 ProTable column 类型、normalize arg 类型、main.tsx 清理
- **react-router-dom 迁移**：Umi 4.6 与 react-router v8 解析冲突修复（见下）

## 验证

- ✅ `npx tsc --noEmit` — 0 errors
- ✅ `npx vitest run` — 150/150 tests pass
- ✅ `max dev` — HTTP 200，673 modules 编译
- ✅ `max build` — SUCCESS, dist/ = 6.6M, 178 chunks
- ⚠️ `eslint` — 36 pre-existing errors（@ts-nocheck 等），与本 PR 无关

## react-router 冲突解决方案

Umi 4.6.82 内嵌 `react-router@6.3.0`（在 `@umijs/preset-umi/node_modules/`）。
Webpack 解析 `react-router` 优先到内嵌 v6，而 v6 的 main entry 不导出 Link。

**修复**：将 78 个应用文件 + 10 个测试文件的导入从 `react-router` 改为 `react-router-dom`（顶层 v6.3.0 有 Link，hooks API 兼容）。

```diff
- import { Link, useNavigate } from "react-router";
+ import { Link, useNavigate } from "react-router-dom";
```

Tests 同步迁移以避免 `<MemoryRouter>` context 不匹配。

## 27 commits 包含

```
build(frontend): add @umijs/max ^4.6.51
build(frontend): switch scripts to max dev/build
feat(frontend): minimal Umi config
feat(frontend): global.ts
refactor(frontend): delete obsolete App.tsx + cleanup
feat(frontend): complete 70+ route manifest
feat(frontend): BlankLayout
feat(frontend): ErpRouteLayout with ProLayout + auth guard
feat(frontend): access control definitions
refactor(products): use ProTable for product list
chore(brands): type columns as ProColumns<Brand>[]
refactor(sales): use ProTable for opportunity list
refactor(warehouse): confirm ProTable usage
refactor: complete ProTable type fixes
refactor(sales): use ProForm for opportunity form
refactor(sales): use ProForm for quotation form
refactor(sales): use ProForm for sales order form
refactor(customers): use ProForm for customer new form
refactor(products): use ProForm for product edit form
refactor(brands): use ProForm for brand edit form
refactor(dashboard): use Statistic + ProCard for KPI cards
refactor(dashboard): use ProCard + Statistic for watchtower
refactor(dashboard): use ProCard + Statistic for global 360
fix(dashboard,sales,customers,inventory,suppliers): batch fix TS errors
fix(frontend): tsc fixes + placeholder index pages
fix(frontend): migrate imports from react-router to react-router-dom
fix(tests): migrate test imports from react-router to react-router-dom
```

## 测试计划

- [x] `tsc --noEmit` clean
- [x] `vitest run` 150/150 pass
- [x] `max dev` HTTP 200
- [x] `max build` SUCCESS
- [ ] 浏览器手动验证 ProLayout 渲染
- [ ] 浏览器手动验证 ProTable 列表
- [ ] 浏览器手动验证 ProForm 创建/编辑
- [ ] 浏览器手动验证 Statistic dashboard

## 后续工作（独立 PR）

- ESLint 清理（36 个 pre-existing 错误）
- Playwright e2e 关键流
- 删除残留 Vite 配置（vite.config.ts + vitest 配置）