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
  - 类型修复 + 列定义标准化
- **Dashboard 迁移**：ProCard + Statistic
  - Dashboard KPI cards / Watchtower / Global360
- **TypeScript 修复**：批量修复 ProTable column 类型、normalize arg 类型、main.tsx 清理

## 验证

- ✅ `npx tsc --noEmit` — 0 错误
- ✅ `npx vitest run` — 150/150 tests pass
- ✅ `max dev` — HTTP 200，Webpack 673 modules 编译
- ⚠️ `max build` — 阻塞：Umi 4.6 内嵌 react-router@6.3.0 与项目 react-router@8.3.0 webpack 解析冲突

## 已知问题

**`max build` 失败**：webpack 解析 `react-router` 到 Umi 内嵌 v6.3.0（不导出 Link），需替换为项目 v8.3.0。已尝试 `config.alias` 但破坏 Umi 的 `renderer-react`（内部用 react-router-dom）。需要进一步调研，可能方案：

1. Umi 5 + React 19 兼容性升级
2. 用 webpack resolve 配置（需 Umi 插件）
3. 替换 react-router 导入路径（影响范围大）

## 25 commits 包含

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
```

## 测试计划

- [ ] 浏览器访问 http://localhost:3002（或 8002）验证 Login 页加载
- [ ] 验证 ProLayout + 侧边栏导航
- [ ] 验证 ProTable 在 customers/sales/products/brands 列表
- [ ] 验证 ProForm 在 opportunity/quotation/order 创建/编辑
- [ ] 验证 Statistic 在 dashboard 显示
- [ ] 验证认证守卫（未登录跳转）

## 后续工作

- 修复 `max build` react-router v8 vs Umi v6 冲突（阻塞生产部署）
- 删除残留 Vite 文件（vite.config.ts + vitest 引用）
- Playwright e2e 关键流验证