# AIERP 监控手册

**最后更新**: 2026-06-11 (Stage 9)
**适用版本**: master

## 🎯 监控目标

| 类别 | 指标 | 告警阈值 |
|---|---|---|
| **业务** | 订单确认/取消速率 | 取消率 > 30% |
| **业务** | 领域错误率 | > 1/s |
| **业务** | 零订单 (1h) | 1h 无确认 |
| **AI** | 调用 p95 延迟 | > 5s |
| **AI** | 错误率 | > 10% |
| **系统** | 进程 RSS | > 1.5GB |
| **缓存** | 命中率 | < 50% |

## 🏗️ 架构

```
┌─────────────────┐
│  AIERP Backend  │  ──► /metrics/prometheus (15s 间隔)
│  (FastAPI+Uvicorn)
└─────────────────┘
         │
         │ scrape
         ▼
┌─────────────────┐
│   Prometheus    │  ──► 评估 alert rules (7 条)
└─────────────────┘
         │
         │ fire
         ▼
┌─────────────────┐
│  AlertManager   │  ──► 抑制 + 路由
└─────────────────┘
         │
         │ webhook
         ▼
┌─────────────────┐
│  ops-alert.sh   │  ──► Telegram (刘经理)
│  (Telegram Bot)
└─────────────────┘
```

## 📊 三大数据源

### 1. 业务 metrics (Stage 9 Day 2)

所有 `Counter` / `Gauge` / `Histogram` 自动双写到 prometheus_client：

| 名称 | 类型 | 标签 |
|---|---|---|
| `orders_confirmed_total` | Counter | `customer_tier` |
| `orders_cancelled_total` | Counter | `previous_status`, `reason` |
| `inventory_reserved_total` | Counter | `product_category` |
| `inventory_release_failures_total` | Counter | - |
| `inventory_concurrent_conflicts_total` | Counter | - |
| `ai_call_duration_seconds` | Histogram | `agent`, `outcome` |
| `event_dispatch_duration_seconds` | Histogram | `event_type` |
| `domain_events_total` | Counter | `event_type` |
| `domain_errors_total` | Counter | `error_type` |
| `cache_hits_total` | Counter | `family` |
| `cache_misses_total` | Counter | `family` |
| `cache_invalidations_total` | Counter | `family` |
| `cache_hit_ratio` | Gauge | `family` |
| `cache_lookup_duration_seconds` | Histogram | `family`, `outcome` |

### 2. 运行时 metrics (Stage 9 Day 1)

`prometheus_client` 自动注册：

- `process_cpu_seconds_total` - CPU 使用
- `process_resident_memory_bytes` - RSS
- `process_open_fds` - 文件描述符
- `process_start_time_seconds` - 启动时间
- `python_gc_objects_collected_total` - GC 健康
- `python_info` - Python 版本

### 3. 业务 endpoint (Stage 7)

- `GET /sales/lifecycle-metrics` - 跟单全流程指标
  - `avg_time_to_confirm_hours`
  - `cancellation_rate_pct`
  - `stage_conversion_pct`

## 🚀 部署 (dev 本地)

### 启动 Prometheus

```bash
# 装 prometheus
sudo apt install prometheus  # 或 brew install prometheus

# 用我们配置启动
prometheus \
  --config.file=ops/prometheus/prometheus.yml \
  --storage.tsdb.path=./prom-data \
  --web.listen-address=:9090
```

打开 http://localhost:9090

### 启动 AlertManager

```bash
alertmanager \
  --config.file=ops/alertmanager/alertmanager.yml \
  --web.listen-address=:9093
```

打开 http://localhost:9093

### 启动 Backend

```bash
cd backend && source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### 导入 Grafana Dashboard

1. Grafana → Dashboards → Import
2. 上传 `ops/grafana/aierp-business.json`
3. datasource = Prometheus
4. 看到 8 个 panels

## 📈 常用 PromQL

### 订单速率
```promql
sum(rate(orders_confirmed_total[5m])) * 60   # 确认/分钟
sum(rate(orders_cancelled_total[5m])) * 60   # 取消/分钟
```

### 取消率
```promql
sum(rate(orders_cancelled_total[5m]))
  / sum(rate(orders_confirmed_total[5m]))
```

### AI 延迟百分位
```promql
histogram_quantile(0.95, sum(rate(ai_call_duration_seconds_bucket[5m])) by (le))
```

### 缓存命中率
```promql
cache_hit_ratio
```

### 内存增长
```promql
process_resident_memory_bytes
```

## 🔔 告警升级路径

| 严重度 | 重复间隔 | 接收 |
|---|---|---|
| **info** | 1h | Telegram (低优先级) |
| **warning** | 1h | Telegram |
| **critical** | 15m | Telegram (强提醒) |

**抑制规则**: critical 触发时，相同 alertname 的 warning 自动抑制（避免重复噪音）。

## 🧪 验证 / 调试

### 手动触发一个告警

```bash
# 在 backend 容器里跑：让 orders_cancelled > orders_confirmed
# (临时调整 Stage 6 cron / 手动改 DB)
```

### 测试 ops-alert.sh 通知

```bash
TELEGRAM_BOT_TOKEN=<from @BotFather> \
TELEGRAM_CHAT_ID=8103002093 \
  bash scripts/ops-alert.sh
```

## 📝 留 ops 团队 / 未来

- **webhook receiver 服务**: AlertManager → http://localhost:9099/alert 现在没接收端，留 ops 团队实现
- **持久化**: Prometheus TSDB 默认 15 天留盘
- **Grafana 告警**: 现在用 AlertManager，Grafana 10+ 也可设 alert rules (备选)
- **多 backend 实例**: prometheus.yml 现在 hardcode 1 个 target，多副本需 service discovery
- **真实环境部署**: docker-compose 已就绪 (Stage 6 Day 4)，加 prometheus + alertmanager service
- **Loki 日志聚合**: 现在 stdout 日志没聚合，未来可接 Loki + Grafana explore

## 🔗 关联文档

- `OPS.md` - 日常运维 (备份/告警/Docker)
- `STAGE9.md` - Stage 9 总结
- `docs/ARCHITECTURE.md` - 整体架构
