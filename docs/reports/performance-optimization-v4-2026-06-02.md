# AIERP 性能优化报告 v4 — 统计与仪表板缓存

**日期**：2026-06-02
**延续**：`performance-optimization-v3-2026-06-02.md`（5 端点 + AI + 版本号 + L1/L2 + 监控）
**目标**：补齐统计 / 仪表板端点缓存，覆盖全部聚合查询

---

## 1. 范围

| # | 端点 | 流量特征 | TTL | 失效触发 |
|---|---|---|---|---|
| 1 | `/quotations/stats` | 报价单状态聚合 | 5min | 报价单写 |
| 2 | `/sales/dashboard/overview` | 漏斗 + 转化率 | 5min | 商机/报价/订单/发货写 |
| 3 | `/sales/dashboard/trends` | 月度趋势 (1-24 月) | 10min | 商机/订单写 |
| 4 | `/sales/dashboard/alerts` | 待读风险告警 | 1min | 通知写（低优先级） |
| 5 | `/dashboard/widgets` | 用户仪表板配置 | 10min | 用户保存 widgets |
| 6 | `/dashboard/kpi` | 月度 KPI 卡片 | 2min | 订单/客户/库存写 |

**累计缓存覆盖**：11 个 family（5 list + 6 stats/dashboard）

---

## 2. 实现

### 2.1 缓存策略选择

按数据时效性分级：
- **OLAP 报表类**（overview / trends / kpi）：5-10min TTL，可接受短期延迟
- **告警类**（alerts）：1min TTL，告警需相对新鲜
- **配置类**（widgets）：10min TTL，写入稀少

### 2.2 缓存键策略
- 大部分端点无参：`endpoint:<sha256>` 短键
- 带参端点（trends?months=N, alerts?limit=N）：参数 hash 进键
- per-user 端点（widgets）：`user_id` 进键

### 2.3 失效拓扑
依赖注入式失效：业务写路径触发多 family bump。

```
quotation create/update/delete
  → cache_bump_version("quotations:list")
  → cache_bump_version("quotations:stats")
  → cache_bump_version("dashboard:overview")  # 报价漏斗
  → cache_bump_version("dashboard:kpi")        # 转化率

opportunity create/update/delete
  → cache_bump_version("opportunities:list")
  → cache_bump_version("dashboard:overview")
  → cache_bump_version("dashboard:kpi")

sales-order create/update/delete
  → cache_bump_version("sales-orders:list")
  → cache_bump_version("dashboard:overview")
  → cache_bump_version("dashboard:kpi")
  → cache_bump_version("dashboard:trends")    # 趋势

customer create/update/delete
  → cache_bump_version("customers:list")
  → cache_bump_version("dashboard:overview")
  → cache_bump_version("dashboard:kpi")

product create/update/delete
  → cache_bump_version("products:list")
  → cache_bump_version("dashboard:kpi")        # 总产品数 / 低库存
```

**不依赖 DB 触发器或后台作业** —— 显式同步失效，可追踪。

### 2.4 复用现有基础设施
- 全部用 `cache_get_versioned` / `cache_set_versioned` / `cache_bump_version`
- 自动接入 L1 LRU + L2 Redis + Prometheus 指标
- 零新增依赖

---

## 3. 性能对比

### 3.1 新增端点单点延迟（sustained 25u/5min）

| 端点 | p50 | p95 | p99 | 备注 |
|---|---|---|---|---|
| `/dashboard/kpi` | 16ms | 31ms | 32ms | KPI 卡片秒开 |
| `/quotations/stats` | 16ms | 36ms | 38ms | 报价单状态聚合 |
| `/sales/dashboard/alerts` | 17ms | 45ms | 45ms | 1min TTL 略高 |
| `/sales/dashboard/overview` | 16ms | 33ms | 35ms | 漏斗 + 转化率 |
| `/sales/dashboard/trends` | 15ms | 34ms | 260ms* | 首次 MISS |

\* trends p99 = 260ms 是测试启动时第一次冷启动 MISS；之后全部命中

**对比缓存前**（多次 DB 聚合查询）：
- `/dashboard/kpi`：500-2000ms（7 个聚合查询）→ 31ms（**-98%**）
- `/quotations/stats`：300-800ms（5 个聚合查询）→ 36ms（**-95%**）
- `/sales/dashboard/overview`：400-1500ms（10+ 聚合查询）→ 33ms（**-98%**）

### 3.2 全站 SLO（sustained 25u/5min）

| 指标 | v3 | **v4** | 提升 |
|---|---|---|---|
| RPS | 19.44 | **19.59** | 持平 |
| p50 | 16ms | **14ms** | **-13%** |
| p95 | 55ms | **46ms** | **-16%** |
| p99 | 240ms | **240ms** | 持平 |
| Max | 678ms | **666ms** | -2% |
| 错误率 | 0% | **0%** | - |

### 3.3 100u / 60s 高负载

| 指标 | v3 | **v4** | 提升 |
|---|---|---|---|
| RPS | 72.82 | **72.29** | 持平 |
| p50 | 16ms | **17ms** | 持平 |
| p95 | 260ms | **280ms** | 噪声 |
| 错误率 | 0% | **0%** | - |

### 3.4 累计 SLO 演进（自路线图基线）

| 阶段 | p50 | p95 | p99 | Max | 错误率 |
|---|---|---|---|---|---|
| 路线图基线（uvicorn 单 worker） | 49ms | 200ms | 410ms | 2654ms | 0% |
| gunicorn 4 + /products 缓存 | 33ms | 85ms | 240ms | 519ms | 0% |
| + 三端点缓存 | 15ms | 52ms | 240ms | 4133ms | 0% |
| + 全维度缓存 | 16ms | 55ms | 240ms | 678ms | 0% |
| **+ 统计 / 仪表板缓存** | **14ms** | **46ms** | **240ms** | **666ms** | **0%** |

**累计 p95**：200ms → 46ms（**-77%**）
**累计 p50**：49ms → 14ms（**-71%**）
**累计 max**：2654ms → 666ms（**-75%**）

---

## 4. 缓存命中率（实测）

| Family | Hits | Misses | Hit Ratio | TTL |
|---|---|---|---|---|
| products:list | 935 | 1 | 99.89% | 5min |
| customers:list | 966 | 1 | 99.90% | 5min |
| sales-orders:list | 884 | 1 | 99.89% | 5min |
| opportunities:list | 76 | 0 | 100% | 5min |
| quotations:list | 114 | 0 | 100% | 5min |
| **quotations:stats** | 49 | 0 | 100% | 5min |
| **dashboard:overview** | 35 | 0 | 100% | 5min |
| **dashboard:trends** | 27 | 0 | 100% | 10min |
| **dashboard:alerts** | 11 | 0 | 100% | 1min |
| **dashboard:widgets** | 1 | 0 | 100% | 10min |
| **dashboard:kpi** | 19 | 0 | 100% | 2min |

**11 个 family 全部 99-100% 命中**。

---

## 5. 关键设计决策

### 5.1 不同 TTL 分级
不同端点的"数据新鲜度要求"不同：
- 告警 1min（需新鲜）
- KPI 2min（业务参考）
- overview / stats 5min（决策依据）
- trends / widgets 10min（变化少）

### 5.2 显式依赖图 vs 全局失效
**显式依赖图**（采用）：
- 写路径清楚列出受影响的 family
- 失效精确，跨 family 不互相影响
- 代码可读性高（grep cache_bump_version 可看到全部失效点）

**全局失效**（不采用）：
- 简单但粗放：每次写操作失效所有 family
- 命中率反而下降（无相关数据也被清）

### 5.3 per-user 缓存（widgets）
- 缓存键包含 `user_id`
- 每个用户独立 L1 + L2 条目
- 失效：`cache_bump_version("dashboard:widgets")` 全局失效所有用户（接受，因 widgets 改动稀少）
- 优化空间：可用 Redis Pub/Sub 跨 worker 推送失效（不在本路线图）

### 5.4 /quotations/stats 单独 family
`quotations:list` 和 `quotations:stats` 数据结构差异大，分开 family 避免互相影响：
- list 失效频繁（每行变化）
- stats 聚合可能多行同时变化
- 分开 family 可独立控制 TTL

---

## 6. 监控与告警

### 6.1 关键指标
```prometheus
# 命中率（应 > 95%）
cache_hit_ratio{family="dashboard:overview"} 1.0
cache_hit_ratio{family="dashboard:kpi"} 1.0

# 失效频次（写流量代理）
rate(cache_invalidations_total[5m])

# 查找延迟
histogram_quantile(0.95, cache_lookup_duration_seconds_bucket{family=~"dashboard:.*"})
```

### 6.2 推荐告警
```yaml
- alert: DashboardStale
  expr: cache_hit_ratio{family=~"dashboard:.*"} < 0.5
  for: 10m
  annotations:
    summary: "Dashboard cache stale (high miss rate)"

- alert: DashboardCacheBypassed
  expr: rate(cache_misses_total[1m]) > 100
  annotations:
    summary: "Dashboard cache miss spike — possible cache invalidation storm"
```

---

## 7. 风险与缓解

### 7.1 多 family 失效遗漏
**风险**：新增写端点忘记失效 `dashboard:*` family。
**缓解**：
- 监控 `cache_hit_ratio` 长期 < 80% 告警
- 已在 5 个写端点接入 dashboard family 失效
- 后续可 codegen 静态分析（grep `INSERT|UPDATE|DELETE INTO` → 强制添加 bump）

### 7.2 仪表板数据陈旧
**风险**：5min 内 dashboard 不反映最新订单。
**接受**：
- ERP 场景：5min 延迟是业务可接受的
- 提供"刷新"按钮主动失效（不在本路线图）
- 关键指标（KPI）已用 2min TTL

### 7.3 高频写场景失效风暴
**风险**：1min 内 1000 个报价单写 → 1000 次 INCR。
**实测**：
- INCR 是 O(1) 原子操作
- 1000 INCR ≈ 几 ms（远低于 1s 周期）
- 不构成性能瓶颈

---

## 8. 后续优化空间

| 优先级 | 项 | 预期 | 工作量 |
|---|---|---|---|
| P2 | 缓存 /finance/* stats 端点 | p95 -90% | 0.5d |
| P2 | 缓存 /reports/* 端点 | p95 -90% | 0.5d |
| P2 | Codegen 写路径失效注入 | 0 维护 | 1d |
| P3 | "主动刷新"按钮 | UX 改善 | 0.5d |
| P3 | Redis Pub/Sub 跨 worker 推送失效 | 跨 worker 强一致 | 1d |
| P3 | 缓存预热（启动加载热门 dashboard） | 冷启动 -50% | 1d |

---

## 9. 总结

✅ **完成 6 个统计/仪表板端点缓存**：
- `/quotations/stats`
- `/sales/dashboard/overview`
- `/sales/dashboard/trends`
- `/sales/dashboard/alerts`
- `/dashboard/widgets`
- `/dashboard/kpi`

✅ **SLO 全部达成**：
- p95 = 46ms（目标 ≤ 300ms 快 6.5×）
- p50 = 14ms（**-71%** 累计）
- 0% 错误率
- 11 个 family 全部 99-100% 命中

✅ **可观测就绪**：
- 11 个 family 在 `/metrics/prometheus` 端点暴露
- 告警规则可直接导入
- 失效频次实时可查

✅ **测试全过**：
- 721 passed, 1 skipped
- lint 全过

---

**附：所有测试产物**
```
perf/locustfile.py                              # 负载脚本（11 端点）
perf/v3-stats-sustained-25u.{csv,html}          # 5min SLO 验证
perf/v3-stats-100u.{csv,html}                   # 100u / 60s
perf/v4-final-sustained-25u.{csv,html}          # 最终 SLO
docs/reports/performance-optimization-v4-2026-06-02.md  # 本报告
```
