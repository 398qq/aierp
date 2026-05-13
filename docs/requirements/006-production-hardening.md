# 006 — 生产加固 (Production Hardening)

## 1. 概述

AIERP 已完成 Phase 1-7 功能开发，所有模块（销售、客户、产品、采购、财务、审批、通知、文档、仪表板、导入导出）已就绪，前后端 180 个后端测试 + 7 个前端测试通过。

当前代码处于"功能完成、开发就绪"状态，但要部署到生产环境，需要在安全性、稳定性、性能、可观测性、部署运维五个维度进行加固。本 PRD 定义了生产就绪的最低标准。

**范围：** 安全审计与加固、错误处理完善、性能优化、日志/监控接入、部署配置标准化。

## 2. 目标

| 指标 | 当前状态 | 目标 |
|------|---------|------|
| 安全漏洞 | 未审计 | 0 个 Critical/High CVE |
| 全局错误处理 | 部分 | 前后端统一错误边界 |
| API 限流 | 无 | 关键端点 100 req/min |
| 健康检查 | 无 | `/health` 返回 DB/Redis/AI 状态 |
| 请求日志 | 无结构化 | JSON 格式 + request_id 追踪 |
| 前端包体积 | 未知 | 主 bundle < 500KB gzip |
| Docker 构建 | 基础 Dockerfile | 多阶段构建 + 非 root 用户 |
| 数据库备份 | 手动 | 自动化定时备份 + 恢复脚本 |
| 前端测试覆盖 | 1 文件 7 用例 | 核心页面 smoke test |
| 配置管理 | 硬编码默认值 | .env.example 完整文档 |

## 3. 用户故事

### S1 — 安全加固
- 作为运维人员，我希望所有 API 端点有速率限制，防止暴力破解和 DDoS。
- 作为安全审计员，我希望 CORS 只允许指定的域名，不暴露敏感 header。
- 作为开发者，我希望依赖库没有已知漏洞，CI 能自动扫描。

### S2 — 错误处理
- 作为用户，当页面出错时，我希望能看到一个友好的错误提示，而不是白屏。
- 作为运维人员，当 AI 服务不可用时，系统应优雅降级，不影响核心业务。
- 作为前端开发者，我希望所有 API 调用有统一的错误处理，不遗漏异常。

### S3 — 可观测性
- 作为运维人员，我希望能通过 `/health` 端点快速判断服务是否正常。
- 作为开发者，我希望能通过 request_id 追踪一次请求的完整链路。
- 作为 DBA，我希望能记录慢查询，便于定位性能瓶颈。

### S4 — 性能优化
- 作为用户，我希望首页加载时间在 3 秒以内（3G 网络）。
- 作为运维人员，我希望数据库连接池配置合理，不因连接泄漏导致故障。

### S5 — 部署运维
- 作为运维人员，我希望通过 `docker compose up` 一键启动全部服务。
- 作为 DBA，我希望有自动化的数据库备份和恢复流程。

## 4. 功能需求

### 4.1 安全加固

**F1 — API 速率限制**
- 登录接口：每分钟 20 次 / IP
- 普通 API：每分钟 100 次 / 用户
- AI 接口：每分钟 30 次 / 用户
- 使用 slowapi 库（FastAPI 兼容）
- 超限返回 429 + Retry-After header

**F2 — 安全响应头**
- 添加 `X-Content-Type-Options: nosniff`
- 添加 `X-Frame-Options: DENY`
- 添加 `X-XSS-Protection: 1; mode=block`
- 添加 `Strict-Transport-Security` (HTTPS 环境)
- 添加 `Content-Security-Policy` (基础策略)

**F3 — CORS 收紧**
- 当前：`allow_origins=["*"]`
- 改为：环境变量 `CORS_ORIGINS` 配置白名单
- 开发环境默认 `http://localhost:3002`
- 生产环境必须显式配置

**F4 — 依赖安全扫描**
- 添加 `pip-audit` 检查 Python 依赖
- 添加 `npm audit` 检查 JS 依赖
- Makefile 添加 `make security-check` 目标

**F5 — JWT 安全增强**
- Token 过期时间可配置（默认 24h）
- Refresh token 机制（可选，后续迭代）
- 登出时 token 加入黑名单（Redis）

### 4.2 错误处理

**F6 — 后端全局异常处理器**
- 捕获所有未处理异常，返回统一格式 `{ code: -1, message: "...", data: null }`
- 区分业务异常（ValidationError → 422）和系统异常（Exception → 500）
- 生产环境不暴露 traceback，开发环境保留

**F7 — 前端全局错误边界**
- React Error Boundary 组件，捕获渲染错误
- 显示"页面出错了"友好提示 + 刷新按钮
- 按路由隔离，一个页面崩溃不影响其他页面

**F8 — AI 服务优雅降级**
- AI 调用超时设置（30s）
- AI 不可用时返回友好提示，不阻塞页面加载
- 仪表板 AI 模块（Global360、DailyReport）降级：显示"AI 服务暂时不可用"

**F9 — 前端 API 统一错误拦截**
- Axios response interceptor 统一处理 HTTP 错误
- 401 → 跳转登录页
- 403 → 提示"无权限"
- 500 → 提示"服务器错误"
- 网络错误 → 提示"网络连接失败"

### 4.3 可观测性

**F10 — 健康检查端点**
- `GET /health` — 返回 DB、Redis、AI 服务连通状态
- `GET /health/ready` — Kubernetes readiness probe
- `GET /health/live` — Kubernetes liveness probe

**F11 — 结构化日志**
- 使用 `structlog` 或 Python `logging` JSON formatter
- 每条日志包含：`timestamp`, `level`, `request_id`, `user_id`, `message`
- 敏感字段脱敏（密码、token）

**F12 — 请求追踪**
- 中间件为每个请求生成 `X-Request-ID`
- 响应 header 回传 `X-Request-ID`
- 前端在 API 调用失败时展示 request_id，方便排查

**F13 — 慢查询日志**
- SQLAlchemy 查询耗时超过 500ms 记录 WARNING 日志
- 可配置阈值 `SLOW_QUERY_THRESHOLD_MS`

### 4.4 性能优化

**F14 — 前端包体积优化**
- 检查 Ant Design 按需加载（当前全量导入）
- 大型图表库（recharts）路由级懒加载
- Vite build 生成 bundle 分析报告

**F15 — 数据库连接池**
- 连接池大小可配置（默认 20）
- 连接回收时间 30 分钟
- 添加 `pool_pre_ping=True` 防止连接失效

**F16 — Nginx 静态资源缓存**
- JS/CSS 文件：缓存 1 年（带 hash）
- 图片/字体：缓存 30 天
- HTML：不缓存
- Gzip/Brotli 压缩

**F17 — 前端图片优化**
- 图片懒加载
- WebP 格式支持提示

### 4.5 部署运维

**F18 — Docker 多阶段构建**
- Backend: builder stage (安装依赖) → runtime stage (仅复制必要文件)
- 使用非 root 用户运行
- `.dockerignore` 排除不必要文件

**F19 — 数据库备份脚本**
- `make db-backup` — 自动化 pg_dump，文件名带时间戳
- `make db-restore` — 从备份恢复
- 备份保留策略：最近 7 天每天，最近 4 周每周

**F20 — 环境配置文档**
- 创建 `.env.example` 列出所有必需和可选的环境变量
- 注释说明每个变量的用途和默认值
- 区分必填/可选

## 5. 非功能需求

| 类别 | 要求 |
|------|------|
| **安全** | OWASP Top 10 无 Critical/High 漏洞 |
| **可用性** | 前端 99.9% 无白屏错误 |
| **性能** | 首页 FCP < 2s, LCP < 3s (Fast 3G) |
| **可维护性** | 所有配置通过环境变量，无硬编码 |
| **兼容性** | 支持 Chrome/Firefox/Edge 最新 2 个大版本 |
| **日志** | JSON 格式，stdout 输出，兼容 ELK/Loki |

## 6. 数据模型

无新增业务实体。仅添加基础设施表：

```sql
-- Token 黑名单 (Redis)
-- Key: blacklist:{jti}  Value: 1  TTL: token过期时间

-- 速率限制 (内存 + 可选 Redis)
-- 使用 slowapi 内置存储
```

## 7. API 设计

### 健康检查

```
GET /health
Response: {
  "status": "ok" | "degraded" | "down",
  "checks": {
    "database": "ok" | "error",
    "redis": "ok" | "unavailable",
    "ai_service": "ok" | "unavailable"
  },
  "uptime_seconds": 3600,
  "version": "1.0.0"
}
```

### 速率限制响应

```
HTTP 429 Too Many Requests
Retry-After: 60
{
  "code": 429,
  "message": "请求过于频繁，请在 60 秒后重试",
  "data": null
}
```

### 统一错误响应格式

```
{
  "code": -1,
  "message": "Internal server error",
  "data": null,
  "request_id": "req_abc123"
}
```

## 8. UI/UX 设计

### 错误边界页面

```
┌──────────────────────────────────┐
│                                  │
│         ⚠️ 页面出错了            │
│                                  │
│   请尝试刷新页面，或联系管理员    │
│   Request ID: req_abc123         │
│                                  │
│        [ 刷新页面 ]              │
│                                  │
└──────────────────────────────────┘
```

### AI 降级提示

- Global360 卡片内显示："AI 服务暂时不可用，请稍后重试 [重试]"
- Daily Report 卡片内显示："报告生成失败，点击刷新重试 [刷新]"
- AI Chat 页面显示："AI 助手暂时离线，请稍后重试"

### API 错误 Toast

- 网络错误：Toast "网络连接失败，请检查网络" （红色，5s）
- 服务器错误：Toast "服务器繁忙，请稍后重试" + request_id （红色，5s）
- 权限错误：Toast "您没有权限执行此操作" （橙色，3s）

## 9. 测试策略

### 单元测试

| 模块 | 测试内容 | 预估用例数 |
|------|---------|-----------|
| 速率限制 | 超限返回 429，正常放行 | 4 |
| 异常处理器 | 业务异常 → 422，系统异常 → 500 | 3 |
| 健康检查 | DB 正常/异常，Redis 正常/异常 | 4 |
| JWT | 过期 token 拒绝，黑名单 token 拒绝 | 3 |
| 前端 ErrorBoundary | 子组件崩溃 → 显示错误页面 | 2 |
| 前端 API 拦截 | 401→跳转，500→提示 | 4 |

### 集成测试

- Docker Compose 完整启动 → 健康检查全部 OK
- 数据库备份 → 恢复 → 数据一致性验证

### 安全检查清单

- [ ] CORS origins 非 `*`
- [ ] 密码不记录到日志
- [ ] SQL 查询全部参数化
- [ ] 无硬编码密钥
- [ ] HTTPS 重定向
- [ ] 安全头全部就位
- [ ] pip-audit / npm audit 无 Critical

---

## 实施阶段

| 阶段 | 内容 | 预估工作量 |
|------|------|-----------|
| **S1 — 安全** | F1-F5 速率限制、安全头、CORS、依赖扫描 | 2h |
| **S2 — 稳定性** | F6-F9 错误处理、降级、Error Boundary | 2h |
| **S3 — 可观测性** | F10-F13 健康检查、日志、请求追踪 | 1.5h |
| **S4 — 性能** | F14-F17 包体积、连接池、缓存 | 1.5h |
| **S5 — 运维** | F18-F20 Docker 优化、备份、配置文档 | 1h |
| **S6 — 测试** | 补充测试 + 安全检查清单 | 1.5h |
| **总计** | | **~10h** |

---

> 状态: draft | 创建: 2026-05-11 | 关联: Phase 1-7 功能代码
