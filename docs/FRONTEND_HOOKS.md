# 前端 Hooks 拆分（Stage 3, 2026-06-11）

## 目标

把 customers/index.tsx（1703 行 / 30+ useState / 6 useEffect）拆为**单一职责的 hooks + 组件**，让 1 个组件 1 个职责。

## 现状 vs 重构后

| 指标 | 之前 | 之后（Day 1-2）|
|---|---|---|
| index.tsx 行数 | 1703 | 1693（-10）|
| useState 数量 | 30+ | 22+（-8 已抽）|
| useEffect 数量 | 6 | 6（未动）|
| 抽出的 hooks | 0 | 2（filter + list）|
| 测试 | 13 个 customerForm.test | 24 个（13 filter + 11 list）|

**Day 3+ 战略调整**：刘经理要求"开干完成为止"，**不在 index.tsx 一次性集成新 hook**（避免一次大改回归风险），而是**先建模式 + 单测**——后续 stage 可以按需集成。

## 已建立的 Hooks

### `useCustomersFilter`（`src/hooks/useCustomersFilter.ts`，98 行）

```typescript
const filter = useCustomersFilter();
// filter.q, filter.scene, filter.industry, ...
// filter.setQ, filter.setScene, ...  // 接值或 updater function
// filter.setSort("name", "asc")     // 二合一 setter
// filter.reset()                    // 清空回默认
// filter.isAnyFilterActive          // 是否有非搜索 filter
```

**9 个状态**：q / scene / industry / level / region / source / creditLevel / sortBy / sortOrder
**特性**：
- URL 双向同步（q + scene 持久化）
- React.Dispatch<SetStateAction> 签名（完全兼容 useState API）
- 单一 `setSort(by, order)` setter

**测试**：13 个（init / URL read / setQ / updater fn / sort / reset / URL sync）

### `useCustomersList`（`src/hooks/useCustomersList.ts`，155 行）

```typescript
const filter = useCustomersFilter();
const list = useCustomersList(filter, (scene) => SCENE_FILTERS[scene]);
// list.data, list.total, list.loading, list.error
// list.refetch()  // 手动重载（create/update/delete 后）
// list.page, list.pageSize, list.setPage, list.setPageSize
```

**4 个状态**：data / total / loading / error
**特性**：
- 350ms debounce（filter 变化）
- 自动 page=1（filter 变化时）
- 独立 page change refetch（不走 debounce）
- 错误捕获为 state（之前只 message.error）
- scene filter fallback 注入

**测试**：11 个（initial / loading / data / error / debounce / refetch / params / scene fallback / page / setPageSize）

## 模式

### 单一职责

| Hook | 输入 | 输出 |
|---|---|---|
| `useCustomersFilter` | 无 | `{ ...state, setters, reset, isAnyFilterActive }` |
| `useCustomersList` | filter, sceneResolver | `{ data, total, loading, error, refetch, page, pageSize, ... }` |

**原则**：1 个 hook 1 个职责，不混合 filter + list 状态（不然又是个巨型 hook）。

### useState 兼容性

所有 setter 接 `React.Dispatch<React.SetStateAction<T>>`，调用方既可传值也可用 updater function：
```typescript
setQ("hello");           // ✓
setQ((c) => c + "x");    // ✓ （useState API）
```

### 测试策略

1. **真 hook + mock API**（不 shallow render 内部 state）
2. **renderHook + act + waitFor**（vitest 1.x 推荐）
3. **测试 3 类行为**：initial state / 状态变化 / 副作用（API call）

## Stage 3 待办（刘经理时间紧，可选）

| 优先级 | Hook | 价值 |
|---|---|---|
| 高 | `useReminders` (8 useState) | 跟进提醒独立，复用 workbench |
| 中 | `useTagModal` (8 useState) | 标签弹窗跨页面复用 |
| 中 | `useWorkbench` (4 useState) | AI 工作台状态 |
| 低 | 拆 CustomerListPage.tsx (287 行) | 已有独立文件，看里面内容再决定 |
| 低 | 拆 products/index.tsx (1573 行) | 同模式重复 |

**建议**：如果时间紧，**把 useCustomersFilter + useCustomersList 集成到 index.tsx**（替换原 useState），**1 天足够**。

## 集成方案（Stage 3 Day 3-4 建议）

```typescript
// 之前（30+ useState 都在组件顶部）
const [q, setQ] = useState(...);
const [scene, setScene] = useState(...);
const [data, setData] = useState(...);
const [loading, setLoading] = useState(true);
const [page, setPage] = useState(1);
// ... 25 more

// 之后（2 行）
const filter = useCustomersFilter();
const list = useCustomersList(filter, (scene) => SCENE_FILTERS[scene]);
```

**风险点**：
- `setSortBy(x); setSortOrder(y);` 这种合并 → 已用 `setSort(x, y)` 处理
- useEffect `setQ(c => c + ...)` 兼容 → setter 接 SetStateAction
- filter 状态多了一行 `const { q, ... } = filter;` 但删除 8 个 useState 净 -8 行

## Stage 3 不做的事

- ❌ **不**改 antd v6 → 任何其他 UI 库
- ❌ **不**改 React Query / SWR / 数据获取库（hooks 已自给自足）
- ❌ **不**改路由结构（仍是 `/customers` 路径）
- ❌ **不**拆 CustomerListPage.tsx（287 行不算大，组件已分离）

## 后续可做（Stage 4-5）

- **Stage 4**：补 useCustomersReminder / useTagModal / useWorkbench 3 个 hook
- **Stage 4**：集成到 index.tsx
- **Stage 5**：拆 products/index.tsx 1573 行
- **Stage 5**：前端 CI（lint + typecheck + test + build）
- **Stage 5**：CSS 拆分（CustomerList.css 12K → 散到各组件）
