# React Query 列表页迁移计划

> 目的：把仍用 ahooks `useRequest` / 直接 axios 拉数据的列表页逐步迁到 `useApiQuery`，
> 统一享受 React Query 缓存、去重、invalidation、`keepPreviousData` 等能力。
>
> 背景：PR #91（`feat(frontend): AI Chat X integration + offline resilience + keepPreviousData`）
> 建立了 `useApiQuery` + `useApiMutation` 基础设施（`frontend/src/lib/queries.ts`）和
> `keepPreviousData` 选项。当前仅 `CustomerListPage` 一个列表页完成了迁移（首例受益方）。
>
> 本文档列出剩余 27 个候选列表页，按"投入产出比"分三个 Tier，作为接下来若干 PR 的范围清单。

## 范围筛选

只列出**有服务端分页或大列表**的顶层列表页（`index.tsx` / `<Entity>List.tsx`）。
BrandDashboard、Customer360、ProductDetail 等详情/仪表类页面不在本批次范围。

`行数` = 现状文件行数（迁移前大致参考）。

## Tier 1 — 高 ROI（先做）

小文件、低风险、列表+基础分页。能快速验证 React Query 在多种表格形态下的表现，
并给后续 PR 提供模板。

| 文件 | 行数 | 主要场景 | 备注 |
|---|---|---|---|
| `frontend/src/pages/system/AuditLogList.tsx` | 84 | 审计日志筛选 | 时间范围筛选用 keepPreviousData |
| `frontend/src/pages/system/UomsList.tsx` | 156 | 计量单位 | 简单 CRUD 列表 |
| `frontend/src/pages/system/ApprovalList.tsx` | 127 | 审批列表 | 状态过滤典型场景 |
| `frontend/src/pages/warehouse/WarehouseList.tsx` | 135 | 仓库列表 | 简单 |
| `frontend/src/pages/tickets/TicketList.tsx` | 95 | 工单列表 | 状态过滤 + keepPreviousData |
| `frontend/src/pages/notifications/index.tsx` | 95 | 通知中心 | 标记已读后 invalidateQueries |
| `frontend/src/pages/finance/AccountList.tsx` | 47 | 会计科目 | 极简，最快完成 |
| `frontend/src/pages/finance/JournalEntryList.tsx` | 47 | 凭证列表 | 极简 |
| `frontend/src/pages/import-export/index.tsx` | 185 | 导入/导出作业 | 进度轮询要不要走 useQuery 自己判断 |

**预计工时**：5-10 小时（每页 30-60 分钟）· 1 个 PR 收口

## Tier 2 — 销售主线（核心业务）

日常业务高频使用列表（报价 → 订单 → 发票 → 收款），分页和筛选都重。

| 文件 | 行数 | 主要场景 | 关键改造 |
|---|---|---|---|
| `frontend/src/pages/sales/InvoiceList.tsx` | 165 | 发票列表 | 状态/时间筛选 + keepPreviousData |
| `frontend/src/pages/sales/PaymentList.tsx` | 258 | 收款列表 | 同上 |
| `frontend/src/pages/sales/ContractList.tsx` | 261 | 合同列表 | 状态机可视化配合 |
| `frontend/src/pages/sales/DeliveryNoteList.tsx` | 277 | 送货单列表 | 状态流转 |
| `frontend/src/pages/sales/PurchaseOrderList.tsx` | 321 | 采购订单列表 | 跟供应商表交叉筛选 |
| `frontend/src/pages/sales/SalesOrderList.tsx` | 329 | 销售订单列表 | 一级功能 |
| `frontend/src/pages/sales/TargetList.tsx` | 155 | 销售目标列表 | 按人/按期聚合 |
| `frontend/src/pages/sales/QuotationList.tsx` | 545 | 报价列表 | 列多、筛选条件多 |
| `frontend/src/pages/sales/OpportunityList.tsx` | 651 | 商机看板列表 | 已有部分 App.useApp 准备（`1b8d26c0`） |
| `frontend/src/pages/customers/FollowUpList.tsx` | 580 | 客户跟进列表 | 跨状态流转 |

**预计工时**：15-20 小时 · 建议拆成 2-3 个 PR（按 sales pipeline 流水分单）

## Tier 3 — 重型页面（最后做）

文件大、内嵌子模块多、需要先评估子页面再动。

| 文件 | 行数 | 阻塞原因 |
|---|---|---|
| `frontend/src/pages/products/index.tsx` | 1839 | 内嵌 ProductCustomerCodesCard / InventoryManage 等多组件，先拆模块 |
| `frontend/src/pages/brands/index.tsx` | 1797 | 内嵌 Compare/Dashboard/360 多视图，需要先做组件分层 |
| `frontend/src/pages/suppliers/index.tsx` | 1272 | 同上，含 Compare/Dashboard |
| `frontend/src/pages/inventory/index.tsx` | 807 | 库存台账 + 低库存预警等多种列表 |
| `frontend/src/pages/dashboard/index.tsx` | 964 | 仪表盘聚合 + 多个子组件，每个卡片可能是独立 query |
| `frontend/src/pages/settings/index.tsx` | 385 | 系统设置，建议整体重构后迁 |
| `frontend/src/pages/finance/CommissionList.tsx` | 338 | 佣金计算跨期/跨人，明细缓存策略要先设计 |
| `frontend/src/pages/finance/CommissionSchemeList.tsx` | 379 | 规则版本变化，需配合缓存失效策略 |
| `frontend/src/pages/customers/AssignmentRulesPage.tsx` / `ReleaseRulesPage.tsx` / `OwnerTransferRequestsPage.tsx` | — | 后续随 customers/ 一起打包迁 |

**预计工时**：40+ 小时 · 建议单独铺一两个前置 PR 拆模块，再迁

## 通用模板（所有 Tier 适用）

迁一页的标准动作：

1. **数据获取**：用 `useApiQuery` 替换 `useRequest` 或裸 axios 拉列表
   ```ts
   const query = useApiQuery<PageData<T>>(
     [entity, { ...searchParams, page, pageSize }],
     `/api/v1/${entity}`,
     { ...searchParams, page, pageSize },
     { keepPreviousData: true },  // 关键：分页列表必开
   );
   ```
2. **变更操作**：用 `useApiMutation` + `invalidateKeys: [[entity], [entity, 'detail', id]]`
3. **副作用**：如筛选条件同步 URL search params，由 `useCustomersFilter` 等 hook 统一处理
4. **错误处理**：复用现 axios 拦截器（避免 #11693 双重提示）
5. **测试**：单测覆盖 queryKey 拼装、invalidate 行为

## 备注

- **ProTable 与 useApiQuery 的边界**（PR #11665 教训）：ProTable 自带 `request` 属性时，
  列表数据走 ProTable 内部，**不**受 `invalidateQueries` 影响 —— 那时必须 `actionRef.reload()`。
  迁移时如果坚持改 ProTable `request` 为 `useApiQuery` 接管，要么改 `request` 为函数引用让 React Query 缓存，
  要么保留 ProTable + 加 `useApiQuery` 仅用于详情/侧栏数据。建议前者，但要测好。
- **`keepPreviousData` 的真值**：在 SaaS 仪表盘场景用户体验提升最大；
  但如果表格只有 5 行 200ms 内返回，开不开都无所谓 —— 起步阶段**所有分页列表都开**最稳。
- **`placeholderData` vs `keepPreviousData`**：v5 中 `keepPreviousData` 已被 deprecated，
  后继为 `placeholderData: keepPreviousData`，本项目现用法是后者；JSDoc 已说明。
