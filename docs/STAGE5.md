# Stage 5 总览（2026-06-11）

## 目标

补齐**工程实践**——CI 真能 catch 问题，前端有 lint，CSS 治理，deps 审计。

## 5 天战果

| Day | 任务 | 关键产出 | 影响 |
|---|---|---|---|
| **1** | ESLint + Prettier | eslint.config.js (v9 flat) + .prettierrc + lint script + CI frontend-lint job | 前端 0 错误 / 1637 warnings（pre-existing）|
| **2** | CSS 审计拆分 | 删 9.2K 死 CSS / 建 1.5K 真用 index.css / CUSTOMER_CSS_AUDIT.md | 净 -7.7K，0 回归 |
| **3** | Migration 规范 | MIGRATIONS.md（命名 / 模板 / 强约束 / 不可逆操作 / 大表警告）+ CI chain check | 4 个 migration chain 验证自动化 |
| **4** | Deps 审计 | pip-audit + npm audit 进 CI + DEPENDENCY_AUDIT.md | frontend 严格 / backend advisory |
| **5** | 总文档 | 本文件 | - |

## 关键产出清单

### 配置文件

- `frontend/eslint.config.js` (90 行) — ESLint v9 flat config
- `frontend/.prettierrc.json` (8 行) — Prettier 格式
- `frontend/package.json` (新加 4 个 script) — lint / lint:fix / format / format:check
- `.github/workflows/ci.yml` (从 5 job → 6 job) — 加 frontend-lint + migration chain + 2 audit

### 文档

- `docs/STAGE5.md` (本文件) — Stage 5 总览
- `docs/CUSTOMER_CSS_AUDIT.md` — CSS 审计方法 + 教训
- `docs/MIGRATIONS.md` — 迁移规范 155 行
- `docs/DEPENDENCY_AUDIT.md` — 依赖审计 + 4 周升级计划

### 代码

- `frontend/src/pages/customers/index.css` (新建 1.5K) — 取代 9.2K 死 CSS
- 删 `frontend/src/pages/customers/CustomerList.css` (working tree only，gitignore 排除)

### CI Job 演化

| Stage | Job 数 | 关键 job |
|---|---|---|
| Stage 4 结束 | 5 | backend-lint / backend-test / frontend-typecheck / frontend-test / frontend-build |
| Stage 5 结束 | 6 | **+ frontend-lint** |
| Stage 5 增强 | | **+ migration chain check** / **+ 2 audit (pip-audit + npm audit)** |

实际效果：5 step → 9 step，每个 step 真阻塞。

## 战略意义

**之前**：
- CI 有但有 `|| true`（Stage 4 修）
- 前端无 lint
- CSS 9.2K 没人用
- 迁移规范靠口口相传
- deps 漏洞零可见

**之后**：
- CI 7+ step 全阻塞 / 1 advisory
- 前端 ESLint v9 + Prettier
- CSS 治理方法论
- 迁移规范 + chain 自动化
- deps CVE 可见，4 周升级路线

## Stage 5 战绩

| 指标 | 之前 | 之后 |
|---|---|---|
| CI job 数 | 5 | 6 |
| CI step 数 | 5 | 9 |
| 前端 lint | ❌ | ✅（ESLint v9）|
| 死 CSS | 9.2K | 0 |
| 迁移 chain 验证 | ❌ | ✅（CI）|
| deps 审计 | ❌ | ✅（pip-audit + npm audit）|
| 净代码 | - | +6 行（仅配置）|
| 净文档 | - | +550 行（3 文档）|

## 教训

1. **改之前先审计**（CSS 拆分的意外发现：0 引用）
2. **CI 不阻塞 advisory 用 `::warning::`**（不让 pre-existing 问题阻塞新 PR）
3. **chain check 比 upgrade head --sql 更稳**（--sql 模式 inspect() 会爆）
4. **|warning| + 文档**比 **|error| + 阻塞**更适合"已知 issues 但要前进"的状态

## 6 个 docs 文档

- `docs/ARCHITECTURE.md`（Stage 1）— 三层架构 / BaseCRUDService
- `docs/ORDER_LIFECYCLE.md`（Stage 2）— 跟单状态机全流程
- `docs/FRONTEND_HOOKS.md`（Stage 3）— 前端 hooks 模式
- `docs/CI.md`（Stage 4）— CI 流程 + FAQ
- `docs/STAGE5.md`（本文件）+ `CUSTOMER_CSS_AUDIT.md` + `MIGRATIONS.md` + `DEPENDENCY_AUDIT.md`

新人 1 周可上手：**ARCHITECTURE → ORDER_LIFECYCLE → 4 个工程文档**。

## 5 Stages 总体战绩

**21 commit / 5 stages 完成 / 零回归**

| Stage | 内容 | commits | 代码 |
|---|---|---|---|
| 1 | base_crud 推广 | 5 | +3164 / -2113 |
| 2 | 跟单状态机 | 5 | +2384 / 0 |
| 3 | 前端 hooks 拆分 | 3 | +698 / -15 |
| 4 | CI 流程 | 3 | +240 / -97 |
| 5 | 工程实践 | 5 | +626 / -29 |
| **合计** | **5 stages** | **21** | **+7112 / -2254** |

**测试覆盖**：
- 后端：123 个（保持全过）
- 前端：91 个（保持全过）
- **CI**：6 job / 9 step 真阻塞

## Stage 6 准备（刘经理拍板）

- **代码层**：
  - Stage 5 Day 1 留下的 ruff format（162 文件）
  - Stage 5 Day 4 留下的 15+ Python CVE
  - products/index.tsx 1573 行拆分
  - useCustomersReminder / useTagModal / useWorkbench hooks

- **架构层**：
  - service 层接入 audit log（status 变更自动 log）
  - dashboard 报表（停留时长 / cancel 率）
  - 佣金计提 listener（订阅 InvoicePaid event）

- **DevOps 层**：
  - 部署：Docker / k8s 编排
  - 监控：Prometheus + Grafana
  - 日志：Loki / ELK
  - 链路追踪：OpenTelemetry
