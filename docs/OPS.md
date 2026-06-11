# 运维手册（Stage 6, 2026-06-11）

## 快速参考

```bash
# 查看所有命令
make help

# 日常开发
make dev              # 起 backend (8080) + frontend (3002)
make dev-backend      # 只 backend
make test            # 跑全部测试
make lint            # lint 检查

# 生产部署
make docker-build   # 构建 Docker 镜像（约5分钟）
make docker-up       # 起服务（http://localhost:80）
make docker-down     # 停服务
make docker-logs    # 看日志

# 生产运维（服务器上跑）
make prod-start     # 起 backend（2 workers，日志 → ./logs/backend.log）
make prod-stop      # 停 backend
make prod-restart   # 重启
make prod-status    # PID / 内存 / CPU / uptime
make prod-logs     # tail -f 日志

# 健康检查
make health-check   # 5 项：backend / DB / 磁盘 / 内存 / 备份

# 备份
make db-backup       # 全量备份（压缩 + 校验，→ ~/date/）
make db-backup-list   # 列出所有备份
make db-backup-clean  # 清理 7+ 天前备份
make db-restore      # 恢复（BACKUP=~/date/aierp_XXX.dump）

# 定时任务（cron）
make ops-alert-cron    # 打印 ops-alert cron 命令（每小时健康检查）
make db-backup-cron    # 打印备份 cron 命令（每天凌晨2点）
```

## 环境变量（生产部署前必设）

```bash
# .env 文件（不要提交到 git）
DATABASE_URL=postgresql+asyncpg://aierp:密码@db:5432/aierp
JWT_SECRET_KEY=你的随机字符串（>=32字符）
SILICONFLOW_API_KEY=（如果有 AI 功能）
TELEGRAM_BOT_TOKEN=（可选，告警用）
```

## Docker 部署

### 1. 构建 + 启动

```bash
make docker-build   # 构建镜像（约5分钟，首次较慢）
make docker-up       # 后台启动全部服务
```

服务地址：
- 前端：http://localhost:80
- 后端：http://localhost:8080
- 数据库：localhost:5432（user/pass: aierp/aierp）

### 2. 监控

```bash
make docker-ps       # 看容器状态
make docker-logs     # tail -f 所有日志
```

### 3. 升级

```bash
make docker-down     # 停旧服务
git pull             # 拉新代码
make docker-build   # 重构建镜像
make docker-up       # 起新服务
```

## 定时任务（cron）

### 备份（每天凌晨 2 点）

```bash
make db-backup-cron
# 输出：
# 0 2 * * * /home/ttdiy/aierp/scripts/backup-pg.sh >> /home/ttdiy/aierp/logs/backup.log 2>&1
# 安装：
(crontab -l 2>/dev/null; cat <(echo '0 2 * * * /home/ttdiy/aierp/scripts/backup-pg.sh >> /home/ttdiy/aierp/logs/backup.log 2>&1')) | crontab -
```

### 运维告警（每小时）

```bash
make ops-alert-cron
# 安装同上
```

## 灾难恢复

### 从备份恢复

```bash
# 1. 查可用备份
make db-backup-list

# 2. 恢复（会 DROP 现有数据！）
make db-restore BACKUP=~/date/aierp_20260601_120000.dump

# 3. 验证
make health-check
```

### 紧急回滚（migration）

```bash
# 看 migration 历史
cd backend && alembic history

# 回滚 1 个 migration
make db-downgrade

# 或直接 stamp 到某个版本
cd backend && alembic stamp 0003_po_logistics_fields
```

## 日志位置

| 日志 | 路径 | 说明 |
|---|---|---|
| Docker backend | `docker compose logs backend` | 容器内 stdout |
| 生产 backend | `./logs/backend.log` | nohup 输出 |
| 备份日志 | `./logs/backup-YYYYMMDD.log` | 每天一个 |
| 运维告警 | `./logs/ops-alert.log` | 每小时检查 |
| alembic | 直接输出 | stdout |

## 监控指标

### /health/live（存活探针）
- 返回 `{"status":"ok"}` 表示进程存活

### /health/ready（就绪探针）
- 检查 DB 连通 + Redis 连通
- 返回 `{"status":"ok"}` 才能接收流量

### /metrics（Prometheus 格式）
- 业务计数器（订单确认数 / 发货数 / 取消数）
- HTTP 请求延迟直方图
- DB 查询延迟

### Telegram 告警（需配置 `TELEGRAM_BOT_TOKEN`）
- backend 挂了
- DB 连不上
- 磁盘 > 80%
- 24 小时无备份
- watchtower 有未读告警

## 已知限制

1. **备份恢复不中断服务**：建议维护窗口内做
2. **Docker 内 uvicorn 2 workers**：够 100 并发，500+ 考虑加 worker 数或加 redis queue
3. **alembic --sql 不能用**：0003 migration 用 inspect()，--sql 模式 mock connection 会爆。用 `alembic upgrade head` 直接升级

## 紧急联系人

| 问题 | 负责 | 联系方式 |
|---|---|---|
| 数据库挂了 | 刘经理 | 微信/电话 |
| Docker 镜像构建失败 | DevOps 团队 | 内部群 |
| API 性能问题 | 刘经理 | 微信 |

## 相关文档

- `docs/ARCHITECTURE.md` — 代码架构
- `docs/ORDER_LIFECYCLE.md` — 跟单状态机
- `docs/CI.md` — CI 流程
- `docs/MIGRATIONS.md` — 数据库迁移规范
- `docs/DEPENDENCY_AUDIT.md` — 依赖 CVE 审计
- `docs/STAGE5.md` — Stage 5 总览
