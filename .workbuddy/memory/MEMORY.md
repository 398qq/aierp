# AIERP 项目记忆

## 项目定位
电子元器件行业 AI 驱动 ERP。销售全流程（商机→报价→订单→发货→发票→回款）、采购三单匹配、库存批次追溯、财务、AI 智能功能（RFM / 流失预测 / NL 查询 / 询盘自动回复）。

## 技术栈
- 后端: Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Pydantic v2
- 前端: UmiJS Max 4 + React 19 + TS + AntD 6（不是裸 Vite，路由在 config/config.ts 手写，无 App.tsx）
- 数据: PostgreSQL 16 + pgvector + Redis 7
- AI: SiliconFlow (DeepSeek + bge-large-zh embedding)
- 调度: APScheduler 14 jobs（进程内）

## 架构关键
- 后端正从「胖 service」向 DDD 迁移，**两套并存**：services/（遗留 ~90% 业务，17k 行）+ application/domain/infrastructure（新，仅销售确认/取消/转报价、采购三单匹配等少量用例）
- 路由 api/v1 薄，按 bounded context 拆子包（sales / finance / finance_accounts / reports / transactions）
- core 横切：JWT 认证、RBAC（require_perm + Redis 缓存 10s）、状态机、缓存（18 族）、审计、PII 加密、熔断
- 响应信封 {code,msg,data,request_id}；成功 ok() 失败 fail()
- 状态机走 transition_status()，禁魔法字符串
- 金额 Decimal / NUMERIC(18,4)，禁 float
- 慢依赖（AI/OCR/PDF）必须 timeout + 重试 + 回退
- 前端 API 调用只在 src/api/<域>.ts，数据获取走 useApiQuery/useApiMutation

## 重构进度 (v6)
- 阶段1: 拆 5 个巨型 API 文件、合并 sales_v2 双路由、前端 api/index.ts 拆 17 域文件 ✅
- 阶段2: 133 个 domain 单测、UI 组件库 v1（src/ui/）、AI 编排分层 ✅
- 阶段3: mypy 清零、6 篇 ADR、zod 试点（customer 域） ✅
- 待办: zod 跨 16 域扫域、orchestration/* 拆分、13 个 *_intel_service 拆分、跨 worker 缓存 Pub/Sub、Playwright E2E

## 常用命令
make dev / make lint / make test / make db-migrate / docker compose up -d (pg+redis)

## 注意
- GEMINI.md 已过时，不要参考
- mypy.ini 对 ~49 个遗留模块设 ignore_errors；新代码必须类型通过
- 5 个后端 pre-existing 测试失败（与重构无关）
- 权威文档：CLAUDE.md（工程底线+命令）、AGENTS.md（简版入口）、DESIGN.md（前端设计系统）
