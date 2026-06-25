# AIERP PostgreSQL 统一方案

日期：2026-06-25

## 结论

AIERP 的主业务数据库应统一为 PostgreSQL。

统一范围是客户、供应商、产品、报价、销售订单、出库单、发票、收款、采购、入库、库存流水、权限、审批、审计日志和报表基础数据。Redis、文件存储和异步任务状态不纳入“全部改 PostgreSQL”的范围。

## 当前状态

项目已经具备 PostgreSQL 主库基础：

- `backend/app/config.py` 通过 `DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME` 生成 `postgresql+asyncpg` 和 `postgresql+psycopg2` 连接串。
- `backend/app/database.py` 使用 `create_async_engine(settings.DATABASE_URL)`，并包含多处仅 PostgreSQL 执行的 schema/index/pgvector 初始化逻辑。
- `docker-compose.yml` 已包含 PostgreSQL 和 Redis。
- `Makefile` 已包含 PostgreSQL reset、backup、restore、migrate、health-check 等操作命令。
- `backend/.env.example` 已以 PostgreSQL 和 Redis 为默认运行模型。

仍然存在的混用点：

- `backend/tests/conftest.py` 默认 `TEST_DATABASE_URL=sqlite+aiosqlite:///./test.db`。
- 多个测试文件使用 SQLite 内存库。
- `backend/requirements-dev.txt` 仍包含 `aiosqlite`。
- 项目根和 `backend/` 下存在 `test.db` 类本地测试文件。
- 文档中仍记录“测试用 SQLite”的旧约定。

## 执行状态

2026-06-25 已执行：

- 已完成全量数据库备份，目录为 `backups/all_databases_20260625_091845`。
- 已确认 `aierp_test` PostgreSQL 测试库可连接，并已安装 `vector` 扩展。
- `backend/tests/conftest.py` 默认测试库已从 SQLite 切换为 `postgresql+asyncpg://aierp:aierp@localhost:5432/aierp_test`。
- 测试初始化增加安全护栏：默认只允许自动 drop/create 名称以 `_test` 结尾或 `test_` 开头的数据库。
- `Makefile` 新增 `make test-postgres`，用于显式运行 PostgreSQL 测试。
- `backend/scripts/orders_7d.py` 已去除硬编码数据库连接，改为读取 `app.config.settings.DATABASE_URL_SYNC`。
- 跟进记录写入和更新时统一按项目约定归一化为 UTC，避免 PostgreSQL `timestamptz` 受服务器时区影响。
- PostgreSQL 测试改为每个测试进程独立 schema，并通过 `search_path` 隔离数据，避免并发测试互相污染。
- pytest async loop 调整为 session 级，消除 asyncpg 在 function loop 销毁时产生的连接取消清理警告。
- Vite 构建按 Ant Design、图标、表格、日期选择器等拆分 chunk，并设置 1.3MB ERP 后台构建预算。

仍需继续：

- 将少量显式 SQLite 内存测试按类型分类：纯单元测试保留，核心 API/单据流测试迁移到 PostgreSQL。
- 清理或更新文档中旧的 SQLite 测试约定。
- 对核心表补充外键、唯一约束、partial index 和金额字段精度审计。
- 将 `test.db` 类文件纳入清理策略，避免误认为业务数据。

## 专业测试报告

测试日期：2026-06-25

已通过：

- PostgreSQL 连接检查：`aierp_test` 可连接，当前用户为 `aierp`。
- PostgreSQL 测试库准备：确认 `vector` 扩展已安装。
- PostgreSQL schema 隔离检查：测试结束后未残留 `aierp_test_%` schema。
- 后端全量 PostgreSQL 测试：`make test-postgres` 通过，`1317 passed in 491.62s`，无 warnings summary。
- 后端静态检查：`ruff check app/database.py tests/conftest.py tests/test_commission_batch.py tests/test_commission_scheme.py tests/test_date_format.py tests/test_phase56_api.py tests/test_sales_api.py` 通过。
- 客户跟进核心 API：6 个 PostgreSQL 集成用例通过，覆盖新增、列表、更新、计划时间更新、逾期跟进统计。
- 销售核心链路：20 个 PostgreSQL 集成/用例测试通过，覆盖报价转订单、订单确认、取消、领域事件和 sales-v2 API。
- 前端客户列表定向测试：2 个测试文件、24 个用例通过。
- 前端类型检查：`npx tsc --noEmit` 通过。
- 前端生产构建：`npx vite build` 通过，无 chunk-size 警告。
- 代码空白检查：`git diff --check` 通过。
- 项目级 lint 现状：`ruff check app/` 已通过；`make lint` 后续 mypy 阶段仍有历史类型债务，当前为 65 个 mypy errors，集中在缓存、安全、库存批次、客户统计、编排、AI embedding、dashboard、finance payments 等既有文件。

测试中发现并已处理：

- session 级 asyncpg engine 被多个事件循环复用，导致跨 loop 连接错误。已改为 function 级 engine，并在测试结束后 dispose。
- function 级 pytest async loop 销毁时 asyncpg 会出现 `Connection._cancel was never awaited` 清理警告。已改为 session 级 async loop，保留 function 级数据库 schema 隔离，全量测试不再出现 warnings summary。
- PostgreSQL `timestamptz` 暴露跟进记录 naive datetime 受服务器时区转换的问题。已在创建和更新路径统一调用 `to_utc()`。
- PostgreSQL 外键约束暴露销售用例库存 fixture 直接写死 `product_id=1`、`warehouse_id=1`。已改为使用真实 flush 后的主键。
- 测试连接池 `pool_size=1` 不足以支撑接口层和 UoW 嵌套访问，导致连接等待超时。最终改为 function 级 engine + `NullPool`，由 PostgreSQL schema 隔离保证测试独立性。
- 全量 PostgreSQL 测试暴露佣金、财务凭证、发货单测试依赖硬编码主键。已改为通过真实用户、客户、订单、会计科目创建测试数据。
- PostgreSQL/SQLite 字符串拼接差异导致 `date_format(..., "YYYYMM")` 在 PostgreSQL 下不可用。已改为 SQLAlchemy `||` 拼接并补充回归测试。
- PostgreSQL 集成测试共用 schema 存在并发污染风险。已改为按进程/worker 生成 `aierp_test_*` schema，并通过 `search_path` 隔离。
- JWT 测试默认密钥长度不足产生告警。已在测试导入应用前设置 32 字节以上测试密钥。
- 前端客户详情抽屉存在 Ant Design 类型问题和场景枚举遗漏。已补充 `Drawer` 引入、移除 `Statistic.size`、补齐 `public_sea` 场景类型。
- Vite 默认 600 kB chunk 预算对 ERP Ant Design 后台过低。已拆分主要 vendor chunk，并将预算调整为 1.3MB，保留异常膨胀预警。

剩余风险：

- 本轮数据库切换和测试体系风险已关闭；当前无阻塞 PostgreSQL 统一方案的已知测试风险。
- 后续工作属于治理增强：继续清理历史 SQLite 文档、审计核心表约束/索引、确认本地 `test.db` 是否仅为可删除测试产物。

## 推荐目标架构

| 类型 | 推荐组件 | 用途 |
| --- | --- | --- |
| 主业务数据库 | PostgreSQL | ERP 主数据、交易单据、库存流水、财务数据、RBAC、审计、报表基础数据 |
| 缓存 | Redis | 列表缓存、版本号、登录/安全缓存、短期状态 |
| 文件存储 | 本地 uploads 或对象存储 | 附件、PDF、导入文件、OCR 原文件 |
| 搜索/向量 | PostgreSQL pgvector 起步 | 客户/产品语义搜索；规模扩大后再评估独立向量库 |
| 单元测试 | 无数据库或轻量 fake repository | 状态机、金额、权限、纯函数 |
| 集成测试 | PostgreSQL 测试库 | API、事务、约束、单据流、报表查询 |

不建议把 Redis、文件和所有任务队列都改成 PostgreSQL。PostgreSQL 负责强一致业务数据，Redis 和文件系统继续承担更适合自己的职责。

## 统一原则

1. 生产、开发、核心集成测试使用同一种数据库行为。
2. 所有 schema 变更必须走 Alembic 或明确的迁移 SQL。
3. 核心金额字段使用 `NUMERIC`/`Decimal`，禁止用 `float` 承担业务金额。
4. 核心列表接口必须分页，并针对查询条件建立索引。
5. 单据流写入必须在同一事务内完成。
6. 缓存失效必须跟随业务写入，例如客户、跟进、订单、发票更新后 bump 对应 cache version。
7. 文件不直接入库，只存元数据和路径。

## 分阶段计划

### 阶段 1：确认 PostgreSQL 为唯一业务主库

目标：统一运行和部署认知。

任务：

- 明确生产环境只使用 PostgreSQL。
- 更新文档中“测试默认 SQLite”的过时说明。
- 保留 `.env.example` 的 PostgreSQL 配置。
- 对 `start.sh`、临时脚本、报表脚本中的硬编码数据库连接做配置化处理。

验收：

- `make dev` 使用 PostgreSQL。
- `make health-check` 能检查 PostgreSQL 和 Redis。
- 文档中不再把 SQLite 描述为核心集成测试标准。

### 阶段 2：测试体系分层

目标：避免“SQLite 测试通过，PostgreSQL 生产失败”。

任务：

- 单元测试继续允许无数据库或内存 fake。
- API/集成测试默认使用 PostgreSQL 测试库。
- 将核心流程测试迁移到 PostgreSQL：
  - 客户与跟进
  - 报价转订单
  - 订单确认
  - 出库单
  - 发票
  - 收款
  - 库存流水
  - 权限和审计
- 保留少量 SQLite 测试仅用于纯 SQL 兼容工具函数，并标记清楚。

建议配置：

```bash
TEST_DATABASE_URL=postgresql+asyncpg://aierp:aierp@localhost:5432/aierp_test
```

验收：

- 核心 API 测试能在 PostgreSQL 测试库运行。
- 测试前自动清库或使用事务隔离。
- SQLite 不再是默认核心集成测试数据库。

### 阶段 3：迁移和约束补强

目标：让数据库替业务守住底线。

重点表：

- `customers`
- `customer_follow_ups`
- `opportunities`
- `quotations`
- `quotation_items`
- `sales_orders`
- `sales_order_items`
- `delivery_notes`
- `invoices`
- `payments`
- `purchase_orders`
- `inventory_transactions`
- `audit_logs`

任务：

- 梳理所有表的外键、唯一约束、非空约束。
- 给常用查询补索引：
  - `deleted_at`
  - `status`
  - `customer_id`
  - `order_date`
  - `invoice_date`
  - `created_at`
  - `assigned_to`
- 对软删除表使用 partial index。
- 对金额字段确认 `NUMERIC` 精度。
- 对 JSON/JSONB 字段确认是否需要 GIN 索引。

验收：

- 迁移能从空库跑到最新版本。
- 迁移能在已有数据环境安全执行。
- 核心列表和报表查询有可解释的索引策略。

### 阶段 4：数据迁移和清理

目标：清理 SQLite/test.db 和临时脚本风险。

任务：

- 检查是否有有效业务数据还停留在 SQLite/test.db。
- 如有业务数据，写一次性迁移脚本导入 PostgreSQL。
- 删除或忽略生成的 `.coverage`、`coverage/`、`test.db`。
- 对 `backend/scripts/orders_7d.py` 这类脚本改为读取环境变量，不硬编码账号密码。

验收：

- 业务数据只以 PostgreSQL 为准。
- 本地测试数据库文件不再被误认为业务数据。
- 脚本不再硬编码数据库凭据。

### 阶段 5：运行保障

目标：让 PostgreSQL 统一后可运维。

任务：

- 使用 `scripts/backup-pg.sh` 建立每日备份。
- 建立恢复演练流程。
- 保留慢查询日志，定期分析。
- 对核心报表建立性能基线。
- 健康检查覆盖 PostgreSQL、Redis、磁盘和内存。

验收：

- 能从备份恢复到测试库。
- 有慢查询日志输出。
- 生产故障时能判断是 DB、Redis、文件还是应用层问题。

## 不建议做的事

- 不建议把 Redis 缓存全部改成 PostgreSQL 表。
- 不建议把 PDF、图片、附件二进制直接存入 PostgreSQL。
- 不建议在核心 ERP 单据测试中继续依赖 SQLite 行为。
- 不建议绕过迁移脚本直接手动改生产库结构。
- 不建议让前端承担唯一业务规则校验。

## 优先执行清单

1. 新增 `aierp_test` PostgreSQL 测试库。
2. 修改测试默认配置，让核心 API 测试使用 PostgreSQL。
3. 清点并标记仍使用 SQLite 的测试。
4. 把客户、跟进、报价、订单、发票、收款流程测试迁到 PostgreSQL。
5. 梳理核心表外键、唯一约束、索引和金额字段类型。
6. 修正文档中 SQLite 作为默认集成测试库的旧说明。
7. 处理硬编码数据库连接脚本。

## 推荐验证命令

```bash
make health-check
make db-migrate
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://aierp:aierp@localhost:5432/aierp_test .venv/bin/pytest tests/test_customers_api.py -q
cd backend && .venv/bin/ruff check app tests
cd frontend && npx vite build
```

## 决策记录

推荐决策：

- PostgreSQL 是 AIERP 唯一业务主数据库。
- Redis 继续作为缓存和短期状态组件。
- 文件继续放文件系统或对象存储，数据库只保存元数据。
- 核心集成测试逐步从 SQLite 迁移到 PostgreSQL。

该方案优先降低生产和测试环境差异，提升 ERP 单据流、财务数据、库存流水和报表查询的一致性。
