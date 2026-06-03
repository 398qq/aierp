# AIERP 架构文档

> 架构评估、技术决策记录（ADR）、重构路线图

## 文档索引

| # | 标题 | 日期 | 状态 |
|---|---|---|---|
| 001 | [设计评估报告](./001-design-audit-2026-06-03.md) | 2026-06-03 | 初版 |

## 命名约定

- 编号三位数字（如 `001-`），增量递增
- 文件名采用 kebab-case：`001-design-audit-2026-06-03.md`

## 当前状态（2026-06-03）

- **后端 4 层骨架**（`app/{domain,application,infrastructure,services}`）已建，但 90% 业务代码仍堆在 `services` + `api/v1`
- **API 巨型单文件**：`sales.py` 952 行、`transactions.py` 623 行、`finance.py` 542 行
- **双套销售路由并存**：`sales.py` (legacy) + `sales_v2.py`（演示新架构）
- **前端 `api/index.ts`** 1,184 行单文件
- **前端 `App.tsx`** 60+ lazy + Route 平铺
- **共享 UI 组件** 缺失
- **24 个 mypy 错误**待修（5 类）
- **类型安全**：后端部分 / 前端大量 `Record<string, unknown>` 逃避
- **测试**：815 通过 / 5 pre-existing 失败；新架构层（domain/application）0 单元测试

详见 [001-design-audit-2026-06-03.md](./001-design-audit-2026-06-03.md) §1-3。
