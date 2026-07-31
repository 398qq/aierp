# AIERP 架构文档

> 架构评估、技术决策记录（ADR）、重构路线图

## ADR 索引

| # | 标题 | 日期 | 状态 |
|---|---|---|---|
| 001 | [缓存架构 — 18-family L1 LRU + L2 Redis](./adr/001-cache-architecture.md) | 2026-05-22 | Accepted |
| 002 | [事件总线 — 进程内 pub/sub + after-commit 派发](./adr/002-event-bus-dispatch.md) | 2026-05-22 | Accepted |
| 003 | [API 与 service 文件的限界上下文拆分](./adr/003-bounded-context-split.md) | 2026-06-03 | Accepted |
| 004 | [销售业务逻辑的 use case 路由](./adr/004-use-case-routing.md) | 2026-06-03 | Accepted |
| 005 | [AI 编排分层 — trigger / orchestration / execution](./adr/005-ai-orchestration-layering.md) | 2026-06-04 | Accepted |
| 006 | [前端共享 UI 组件库 v1](./adr/006-shared-ui-component-library.md) | 2026-06-04 | Accepted |

## 历史文档

| # | 标题 | 日期 | 状态 |
|---|---|---|---|
| 001-design-audit | [2026-06-03 设计评估报告](./001-design-audit-2026-06-03.md) | 2026-06-03 | 初版（前置审计） |

## 命名约定

- ADR 编号三位数字（如 `001-`），增量递增
- ADR 文件名采用 kebab-case：`001-cache-architecture.md`
- 历史（pre-ADR）文档不强制编号，已存在的 `001-design-audit-2026-06-03.md` 保持原名

## 当前状态快照（2026-07-31）

参考 PR #99 合并后的状态，比 2026-06-03 评估时已有进展：

**已修 / 已改**：
- 9 个 mypy 错误清零（`opportunities.py`, `user_preferences.py`） — PR #99
- 后端 4 层骨架（`app/{domain,application,infrastructure,services}`）继续推进，新代码优先走这三层
- 共享 UI 组件库 v1 已落地（见 ADR 006 + `frontend/src/ui/`）

**仍待办**（按 [001-design-audit-2026-06-03.md](./001-design-audit-2026-06-03.md) §1-3 跟踪）：
- 巨型单文件 API 路由继续拆分（`sales.py` / `finance.py` 等）
- 销售业务逻辑向 use case 层的迁移（ADR 004）
- 前端 List 页 Pro v6 化（`useApiQuery` + `useApiMutation`） — 进行中，见 `refactor/full-target-form` 系列
- `domain` / `application` 层的单元测试覆盖

详见 [001-design-audit-2026-06-03.md](./001-design-audit-2026-06-03.md) §1-3。
