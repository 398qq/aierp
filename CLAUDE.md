# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AIERP — 电子元器件行业 AI 驱动的 ERP 系统，覆盖销售全流程（商机 → 报价 → 订单 → 发货 → 发票 → 回款）、采购（含三单匹配）、库存（含批次追溯）、客户/供应商管理、佣金方案，以及 AI 智能功能（RFM 分析、流失预测、品牌对比、供应商评分、需求预测、询盘自动回复、自然语言查询）。

后端 `2.2.0`（`backend/app/config.py`），前端 `2.1.1`（`frontend/package.json`）。

## 常用命令

```bash
make dev              # 后端 :8080 + 前端 :3002（热重载，Ctrl-C 一起停）
make dev-backend      # 仅后端 / make dev-frontend 仅前端
make lint             # 后端 ruff check + mypy，前端 tsc --noEmit
make test             # 后端 pytest + 前端 vitest
make test-postgres    # 后端测试跑真实 PostgreSQL（默认走 SQLite）
make test-backend-cov # 后端覆盖率（term-missing + html）
make db-migrate       # alembic upgrade head
make db-revision MSG="..."   # 生成 alembic 迁移
make db-reset         # 删库重建（本地开发用）
make db-shell         # psql 进开发库
make security-check   # pip-audit + npm audit
docker compose up -d  # pgvector:pg16 (5432) + redis:7 (6379)
```

单个测试：

```bash
cd backend && pytest -v tests/api/v1/customers/test_crud.py::test_get_customer
cd backend && pytest -v -k "transition"          # 按名字过滤
cd frontend && npx vitest run src/test/queries.test.tsx
cd frontend && npx playwright test e2e/route-smoke.spec.ts   # E2E，需先起 dev
```

`make lint` 里的 mypy 并非全量：`backend/mypy.ini` 对约 49 个遗留模块设了 `ignore_errors=True`；新代码要保证类型通过。pre-commit 只跑 ruff / prettier / detect-secrets / bandit，**不跑 mypy 和 pytest**。

## Skills / Agents / Hooks

本项目挂了 30 个 `superpowers-zh` 技能 + 8 个领域 agent + 3 个项目级 hook。开工前**先看一眼**：

- **`.claude/skills/`** — 30 个 skill（`.claude/skills/using-superpowers/SKILL.md` 是元规则）。**哪怕只有 1% 可能性某个 skill 适用当前任务，都必须用 `Skill` 工具加载并遵循**。常驻调用：`brainstorming`（任何创造性工作前）、`test-driven-development`（写代码前）、`verification-before-completion`（宣称完成前）、`systematic-debugging`（遇到 bug）、`requesting-code-review`（功能完成时）、`writing-plans`（多步骤任务）。`chinese-*` 系列仅在用户显式 `/chinese-*` 时触发。
- **`.claude/agents/`** — 领域 agent，按作用域委派：`aierp-orchestrator`（任务派发）/ `aierp-developer`（全栈实施）/ `backend-architect`（设计，只读）/ `frontend-builder`（前端，限定 `frontend/src/`）/ `db-migrator`（迁移，限定 migration/model）/ `qa-reviewer`（审 PR，只读）/ `brand-analysis-agent`（品牌智能）。每个 agent 工具白名单见对应 `.md`。
- **`.claude/settings.json` 钩子** — `PostToolUse` 自动跑 `format-on-edit.sh`（Prettier/Ruff）、`PreToolUse` 跑 `pre-bash-guard.sh` 拦危险命令、`Stop` 跑 `stop-lint.sh` 收尾 lint。不要在 hook 外手动跑这些。
- **工作分支** 当前 `refactor/full-target-form`；与 `master` 的偏离体现在「前端 List 页全面 Pro v6 化」迁移（见 `docs/frontend/pro-v6-migration-guide.md`、`docs/frontend/x2-prov6-learning-guide.md`）。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| 数据库 | PostgreSQL 16 + pgvector（`Vector(1024)` 语义检索） |
| 缓存 | Redis 7（列表缓存、权限缓存、限流、Telegram 轮询锁） |
| AI | SiliconFlow API — DeepSeek-V4-Flash（对话）、BAAI/bge-large-zh-v1.5（embedding）、MiniMax-M3（`AI_CODE_MODEL`） |
| 前端 | **UmiJS Max 4**, React 19, TypeScript 6, Ant Design 6 + ProComponents 3, TanStack Query 5, Zustand 5, Recharts |
| 调度 | APScheduler `AsyncIOScheduler`（进程内，14 个作业） |
| 测试 | pytest（`asyncio_mode=auto`）/ Vitest + Testing Library / Playwright |

## 架构

### 后端 `backend/app/`

分层正在从「胖 service」向 DDD 迁移，**两套并存**：

```
main.py            # lifespan：init_db → init_uow → 预热连接池 → 调度器 → Telegram 轮询
config.py          # Pydantic Settings；生产环境缺 JWT_SECRET/DB_PASSWORD/CORS 会拒绝启动
database.py        # 异步引擎、init_db()、pgvector 初始化、慢查询日志

# —— 新代码优先走这三层 ——
domain/            # 纯业务逻辑，不依赖 infra
  shared/          #   DomainError 体系、Money 值对象、DomainEvent
  states/          #   状态机转换表 + assert_can_transition_* 函数
  sales/ procurement/ inventory/ finance/   # 实体、事件、三单匹配、批次分配/成本策略
application/       # 用例编排
  uow.py           #   UnitOfWork（成功自动 commit、异常回滚、commit 后才派发事件）
  sales/ procurement/    # ConfirmSalesOrderUseCase、MatchSupplierInvoiceUseCase 等
infrastructure/    # 适配器，如 persistence/inventory_repo.py（version 列乐观锁）

# —— 遗留层，仍承载大部分业务 ——
api/v1/            # 30+ 子路由；小域单文件，大域升级为包（customers/ sales/ finance/ products/ ai/ ...）
models/            # SQLAlchemy ORM，软删除靠 TimestampMixin
schemas/           # Pydantic 契约 + common.py 的 ok()/fail()/paginated_ok()
services/          # 业务逻辑主体（含 ai/、sales_service/、brand_intel/、pdf/、nlp_query/、orchestration/）
core/              # security、permissions、error_handlers、rate_limit、request_context、
                   # security_headers、pii_policy、field_encryption、circuit_breaker、data_isolation
jobs/scheduler.py  # 14 个后台作业
```

中间件注册顺序（`main.py`，最外层先注册）：CORS → RateLimit → RequestLogging → SecurityHeaders → RequestContext。

健康检查：`/health`（DB+Redis+AI，返回 ok/degraded/down）、`/health/ready`（DB 就绪，故障返回 503）、`/health/live`、`/metrics/prometheus`。

### 前端 `frontend/src/`

**这是 UmiJS Max，不是裸 Vite，也没有 `App.tsx`。**

```
../config/config.ts   # Umi 配置：routes 数组（手写，约 75 个页面）、proxy /api → :8080、port 3002
layouts/ErpRouteLayout.tsx  # 认证外壳：QueryClientProvider + OfflineBanner + ProLayout + Outlet
                            # 挂载时 useAuthStore.init() 探测 /auth/me；无 username → 跳 /login
navigation/appNavigation.tsx # 菜单taxonomy + 全局搜索跳转
lib/queries.ts        # useApiQuery / useApiMutation（React Query 封装，自动拆 {code,msg,data} 信封）
lib/queryClient.ts    # staleTime 5min、gcTime 10min、retry 1、refetchOnWindowFocus false
api/                  # 按域拆文件（customers.ts sales.ts finance.ts ...），index.ts 只是 barrel
api/client.ts         # axios：baseURL /api/v1、withCredentials、X-Request-ID、
                      # GET 幂等重试（408/429/5xx）、401 跳登录、getApiErrorMessage 中文化
api/schemas/          # zod 运行时校验试点：safeGet/safePost + customer.ts
ui/                   # 共享原语（见下）
design-tokens.ts      # 设计令牌唯一来源；styles/*.css 用 erp- 前缀类名
store/auth.ts         # Zustand：username/roles/loading/login/logout/init
access.ts             # Umi access 插件契约：canAdmin/canSales/canFinance
```

路由 = `config/config.ts` 的 `routes` 数组，Umi 自动为每个页面生成 `React.lazy`（见生成物 `src/.umi/core/route.tsx`），**业务代码里不用自己写 lazy/Suspense**。

`src/ui/` 现有原语：`PageHeader`、`StatusTag`（语义 tone，非裸 `<Tag color>`）、`SearchBar`、`MetricBand`、`EmptyState`、`ErrorBoundary`（识别 chunk 加载失败与离线）、`ModuleShell`、`OfflineBanner`、`UomSelect`（按类别分组 + 请求去重）、`IndustryRanking`、`FlexBox`、`FullPageLoader`、`useColumnResize`、`pagination.ts`（`erpPagination()`、`ERP_PAGE_SIZE=20`）、`chunkError.ts`、`AntdOverlayGuard`。

### 数据流

```
前端 → useApiQuery/useApiMutation → axios(/api/v1, cookie) → Vite proxy → FastAPI
  → api/v1 路由（薄）→ services/ 或 application/ 用例 → SQLAlchemy async → PostgreSQL
                                  ↕                            ↕
                        AIClient → SiliconFlow        pgvector / Redis
                        APScheduler → 14 个周期作业
```

### 当前在飞的迁移：前端 Pro v6 化

`useApiQuery` + `useApiMutation` 已成为标准数据获取层；`refactor(sales|finance|...): unify Pro v6 patterns with useApiQuery` 是进行中的合流提交前缀。新写 List / Form 必须直接按 `docs/frontend/pro-v6-migration-guide.md` 模板走（`params` + `request` 函数、`keepPreviousData`、`invalidateKeys`），不要新建 `useEffect + axios` 模式。AI Chat 已切到 `@ant-design/x` 的 `useXChat`（自定义 AIERP provider，鉴权走 `/auth/me` 拿到的 token，**不是 localStorage**）。

## 关键约定

**响应信封**：统一 `{code, msg, data, request_id}`。成功用 `ok(data)`（普通 dict，状态码由路由装饰器决定）；失败用 `fail(msg, code=400)`（返回 `JSONResponse`，**HTTP 状态码等于 code**，前端拦截器靠状态码分流）。全局处理器覆盖 `DomainError`（取 `exc.http_status`）、`HTTPException`、`RequestValidationError`（422）、未捕获异常（500，非 DEBUG 不泄漏详情）。

**认证**：JWT 优先 `Authorization: Bearer`，回退 `aierp_token` httpOnly cookie。`get_current_user`（`api/deps.py`）返回 `{user_id, username, roles}`，并校验 Redis 黑名单 `jti` + `User.token_version`。默认 8 小时过期。

**RBAC**：路由声明 `Depends(require_perm(resource, action))`（`core/permissions.py`）——单条 EXISTS 查询、`admin` 角色直通、Redis 缓存 10 秒（允许与拒绝都缓存）。资源码见 `RESOURCES`（customers/products/sales/purchases/finance/inventory/reports/system）。RBAC 变更后要调 `_invalidate_perm_cache()`。部分遗留端点只有 `Depends(get_current_user)`，属待补审计项——新端点必须声明权限。

**状态机**：转换表与守卫在 `domain/states/`（`SALES_ORDER_TRANSITIONS` + `assert_can_transition_sales_order(current, target)` 等，覆盖商机/报价/订单/发货/退货/客户/发票/回款/合同/佣金/采购单/收货/供应商发票/工单/样品）。写路径统一走 `services/state_transition_service.py::transition_status(db, entity, target, guard=..., aggregate_type=..., actor=...)`——同状态返回 `False` 幂等、失败抛 `InvalidStateTransition`、自动写 `StatusTransitionLog`（**不 commit，调用方负责**）。

**迁移**：`backend/alembic/versions/` 是权威（`make db-migrate`）。另有两处历史目录：`backend/app/migrations/*.sql` 是幂等补丁，由 `init_db()` 在启动时自动执行（`CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` 风格）；`backend/migrations/*.sql` 是需手动执行的索引/扩展脚本。**新的结构变更一律写 Alembic。**

**缓存**：`services/cache_service.py` 提供带版本前缀的列表缓存（`cache_bump_version` 使某域缓存整体失效）。写操作后记得 bump。

## 工程底线（不可协商）

### 后端

1. **状态机必定义** — 业务对象的 `status` 用 `Enum` + `domain/states/` 转换表，禁止魔法字符串；改状态走 `transition_status()`。
2. **软删除** — 所有 model 继承 `TimestampMixin`，查询必须过滤 `deleted_at IS NULL`。
3. **路由薄、逻辑下沉** — 路由只做解析 → 调 service/用例 → 返回 schema。services 里不抛 `HTTPException`，抛 `DomainError` 子类（`NotFoundError`/`BusinessRuleViolation`/`InvalidStateTransition`/`ConflictError`/`InsufficientStockError`/`ConcurrentModificationError`）。
4. **金额用 `Decimal`** — `Decimal(str(value))`，DB `NUMERIC(18,4)`，测试断言精确相等。禁止 `float`。
5. **单据总额必须对账** — `SalesOrder.total == sum(line.subtotal) - discount + tax`，Invoice/Quotation/PurchaseOrder 同理；改行项要有触发重算的测试。
6. **慢依赖有界** — AI、OCR、PDF、物流、支付：显式 `timeout` + tenacity 重试（3 次指数退避）+ 安全回退（缓存值/默认值/入队）。禁止裸 `await client.call(...)`。
7. **事务边界** — 通过 `get_db()` 或 `get_uow()`，不在生命周期外 `commit()`。
8. **审计与请求 ID** — `created_by/updated_by` 由事件监听器从 `request_context` 填充；`request_id` 贯穿日志、错误响应、慢查询日志。

### 前端

1. **共享原语从 `@/ui` 导入**，不在页面里内联重造。新模式扩充 `src/ui/`，不散落到页面。
2. **API 调用只在 `src/api/<域>.ts`** — 组件里禁止直接 `axios.*`；新端点先加到对应域文件（必要时从 `index.ts` 导出）。
3. **数据获取走 `useApiQuery`/`useApiMutation`** — query key 用元组（如 `["customers", params]`）；列表页带 `keepPreviousData: true` 避免翻页闪烁；变更用 `invalidateKeys` 失效。
4. **异步状态显式** — 空数据 `<EmptyState>`、加载 `<Spin>`、失败 `message.error(getApiErrorMessage(err))`。半渲染列表算 bug。
5. **表格高密度可扫描** — 行高 40–48px、数字右对齐并用 tabular-nums（`design-tokens.ts` 的 `numericStyle`）、状态列用 `<StatusTag tone>`、操作列 ≤ 3 按钮 + 更多下拉。
6. **表单放 Drawer** — Modal ≤ 4 字段；5+ 字段或多分区用 Drawer；≥ 3 步用向导。提交按钮在 1080p 下无需滚动可达。
7. **权限感知渲染** — 依据 `useAuthStore` 的 `roles` / `access.ts` 隐藏无权操作；服务端必须再校验一次。
8. **样式走令牌** — 用 `design-tokens.ts` 与 `styles/*.css` 的 `erp-` 类名，禁止内联 `style={{ color: '#1890ff' }}` 或新造色值/圆角/字重。
9. **每页 `<ErrorBoundary>`** — 失败给恢复 UI，不要白屏。

### 代码风格

- 后端：`snake_case` 模块、`PascalCase` 类、`test_*.py`；每个函数签名带参数与返回类型注解。
- 前端：`PascalCase` 组件/页面、`camelCase` 函数与 hook（hook 以 `use` 开头）、`@/*` → `src/*`；prettier `printWidth=100`、双引号、结尾分号。
- **文件 ≤ 500 行**；加第 4 个关注点之前先抽 helper。

## 测试

- 后端 `pytest asyncio_mode=auto`，标记 `@pytest.mark.unit` / `@pytest.mark.integration`。默认 SQLite（aiosqlite），`conftest.py` 把 pgvector `Vector` 列替换成 `Text`；`make test-postgres` 走真实 PG（每 worker 建独立 schema，需 pgvector 扩展）。
- 关键 fixture：`async_client`（ASGITransport + 覆盖 `get_db`/`get_uow`）、`test_user`（sales 角色 + customers 权限）、`test_admin`、`auth_headers`/`admin_headers`；autouse 的 Redis 清理（防权限缓存串味）与 Telegram 环境清理；`EMBEDDING_PIPELINE=0` 关掉 fire-and-forget embedding。
- 前端 Vitest + Testing Library，测试集中在 `src/test/`（`setup.ts` 已 stub matchMedia/ResizeObserver/IntersectionObserver/localStorage）；E2E 在 `frontend/e2e/`（Playwright，chromium，baseURL `:3002`）。
- 覆盖率下限（CONTRIBUTING.md）：service 80% / api 70% / utils 90% / 前端组件 60%。
- 性能或超时类修复：在 commit 与 PR 里附前后计时。

## CI（`.github/workflows/`）

`ci.yml` 在 push master/main 与 PR 上跑 6 个 job：`backend-lint`（ruff 0.7.4）、`backend-test`（pytest，SQLite，`pip-audit` 仅告警不阻断）、`frontend-typecheck`（`tsc --noEmit`）、`frontend-lint`、`frontend-test`（vitest）、`frontend-build`（`tsc -b && max build` + npm audit）。另有 `security-audit.yml`（周一严格 pip-audit）、`codeql.yml`（周二，Python + JS/TS）、`dependabot-auto-merge.yml`（patch/minor 自动合并，需 `AUTO_MERGE_TOKEN`）。

提交信息用 Conventional Commits 带 scope（如 `feat(commission): ...`）；PR 正文五段：Why / What / How / Test / Risk。

## 反模式（拒绝）

- 业务逻辑里 `datetime.now()` → 注入 Clock，保证可测可回放。
- 金额用 `float`、状态用裸 `VARCHAR`、硬编码 `if user.role == "admin"`。
- 路由里直接写 DB 查询；service 里抛 `HTTPException`。
- 组件里直接 `axios.*`；绕过 `useApiQuery` 手写 `useEffect` 拉数据。
- 状态列内联 `<Tag color="green">` → 用 `<StatusTag tone="success">`。
- AI/外部调用没有 `timeout`；`try/except: pass` 静默失败。
- 新增结构变更只写 `app/migrations/*.sql` 而不写 Alembic。

## 参考文档

- [AGENTS.md](AGENTS.md) — 仓库简版入口（本文件是其「工程底线与命令参考」）
- [CONTRIBUTING.md](CONTRIBUTING.md) — 分支节奏、Dependabot、覆盖率与 bundle 预算、PR 模板
- [DESIGN.md](DESIGN.md) — 前端设计系统（配色、字号、组件与响应式规范）
- [docs/README.md](docs/README.md) — 文档总索引
- [docs/architecture/adr/](docs/architecture/adr/) — 6 篇 ADR：缓存架构 / 事件总线派发 / 限界上下文拆分 / 用例路由 / AI 编排分层 / 共享 UI 组件库
- [docs/development-workflow.md](docs/development-workflow.md) · [docs/MIGRATIONS.md](docs/MIGRATIONS.md) · [docs/OPS.md](docs/OPS.md) · [docs/CI.md](docs/CI.md) · [docs/frontend/](docs/frontend/)
- **不要读** `GEMINI.md`（已过时，层次与覆盖率说法均不准）· **不要当安全策略**用根目录的 `SECURITY.md`（仍是 GitHub 默认模板，待替换）。
