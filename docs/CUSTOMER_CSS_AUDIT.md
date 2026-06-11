# CustomerList.css 审计 + 拆分（Stage 5 Day 2）

## 审计结果：惊喜发现

跑 `comm` 工具对比 `className="..."` 引用 vs CSS 定义：

```
实际被用的 className： 88 个
CustomerList.css 定义的 class： 65 个
CSS 里有但没用的：  37 个
实际用 class 中 CSS 覆盖数：0 个
```

**震惊结论**：CustomerList.css 276 行 / 9.2K 定义的 65 个 class，**0 个**被实际代码用！

所有 88 个 className 散落在 `*.tsx`，走的都是 antd 默认样式。

## 决策

**删掉** `CustomerList.css`，新建一个**最小的** `index.css`，**只**包真被引用的 class。

## 真被引用的 class（11 个）

| Class | 引用方 | 用途 |
|---|---|---|
| `customer-workbench-grid` | index.tsx + CustomerStatsCards.tsx | KPI 网格 |
| `crm-compact-bar` | CustomerCrmToolbar.tsx + index.tsx | 紧凑工具条 |
| `crm-compact-controls` | CustomerCrmToolbar.tsx | 工具条内部布局 |
| `customer-board` | index.tsx | 看板视图容器 |
| `customer-board-column` | index.tsx | 看板列 |
| `customer-board-column-head` | index.tsx | 看板列头 |
| `customer-board-column-meta` | index.tsx | 看板列副标题 |
| `customer-board-list` | index.tsx | 看板卡片列表 |
| `customer-board-card` | index.tsx | 看板卡片 |
| `customer-module-*` | index.tsx + CustomerModuleShell.tsx | 模块壳子 |
| `customer-kpi-*` + `customer-stat-*` | index.tsx + CustomerStatsCards.tsx | KPI 卡片 |

## 拆分结果

| 文件 | 之前 | 之后 | Δ |
|---|---|---|---|
| CustomerList.css | 9.2K / 65 class | **删除** | -9.2K |
| index.css (新建) | - | 1.5K / 11 class | +1.5K |
| **净** | | | **-7.7K** |

## 零回归

- `tsc --noEmit` 0 错误
- 91/91 前端测试全过
- 删的是 0 引用的死代码

## 经验教训

**改之前先审计**——之前的"12K CSS 大拆分"是 0 价值的优化（拆了没人用）。

未来加 CSS 规则前：
1. 先 grep `className="xxx"` 看有没有用
2. 只改**正在用的** class
3. 新规则跟 class 一起放在组件里（不是全局）

## Stage 5 Day 2 后续

可做的（**非阻塞**，可独立排期）：
- 抽 `CustomerStatsCards.css`（4 个 KPI 样式）
- 抽 `CustomerModuleShell.css`（10 个 module 样式）
- 抽 `CustomerBoard.css`（6 个 board 样式）
- 上面每个 30-50 行，1 个组件 1 个文件

但目前 `index.css` 1.5K 够用——**晚点再拆**。
