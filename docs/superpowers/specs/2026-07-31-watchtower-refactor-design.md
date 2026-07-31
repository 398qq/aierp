# Watchtower Dashboard Refactor — Design Spec

**Status**: Approved (brainstorming complete, sections §1–§5 confirmed)
**Date**: 2026-07-31
**Scope**: Same behavior, same API shape, same UI. Internal cleanup + perf + Pro v6 + tokens + tests.

---

## §1 架构总览

### Backend

```
backend/app/api/v1/ai/
  watchtower.py (~50 行, 2 endpoint, 薄路由)
    ├─ /ai/watchtower/scan   → _shared.watchtower_cached_scan
    └─ /ai/daily-report      → _shared.watchtower_cached_report

backend/app/services/
  watchtower_service.py (~150 行, 6 函数)
    ├─ scan_churn_risk(db, lookback, prev_lookback)
    ├─ scan_order_drop(db, lookback, prev_lookback)
    ├─ scan_low_stock(db)
    ├─ scan_out_of_stock(db)
    ├─ generate_ai_summary(anomalies, total_alerts)
    └─ _persist_customer_alerts(db, anomalies, now)  ← unchanged

backend/app/api/v1/ai/_shared.py (new)
    ├─ watchtower_cached_scan(db, days_back)
    │   ├─ cache_get_versioned("watchtower:scan", key)
    │   ├─ asyncio.gather(4 scan_*)
    │   ├─ await generate_ai_summary(...)
    │   ├─ await _persist_customer_alerts(...)
    │   └─ cache_set_versioned(..., 300)
    └─ watchtower_cached_report(db)
        ├─ cache_get_versioned("watchtower:report", key)
        └─ cache_set_versioned(..., 600)
```

### Frontend

```
frontend/src/pages/dashboard/
  WatchtowerDashboard.tsx (~80 行, 纯组合)
    └─ <ModuleShell>                    // @/ui, existing
       ├─ <ScanHeader/>
       ├─ <KpiCards/>
       ├─ <AiSummary/>
       ├─ {top_actions.length && <TopActions/>}
       └─ <AnomalyTable/>

  components/  (new)
    ScanHeader.tsx       + ScanHeader.module.css
    KpiCards.tsx         + KpiCards.module.css
    AiSummary.tsx        + AiSummary.module.css
    TopActions.tsx       + TopActions.module.css
    AnomalyTable.tsx     + AnomalyTable.module.css

  WatchtowerDashboard.module.css  (new, 壳布局)

  types/watchtower.ts  (new)
    AnomalyRow, WatchtowerScanResponse

  // 注: dashboard.css (597 行) 是 pages/dashboard/index.tsx (Sales Dashboard 主页面) 用的,
  // 不是 Watchtower 的. 原始 WatchtowerDashboard.tsx 没有 import 任何 CSS.
  // 此次不动 dashboard.css.
```

### Out of scope (explicit)

- `backend/app/api/v1/dashboard.py` (Sales Dashboard — 6 endpoint, 另一套)
- `pages/sales/SalesDashboard.tsx` + its css
- `pages/dashboard/` 之外的任何页面
- 新增 / 删除 response fields
- 加 / 减 KPI 卡片 / section
- 重设计信息架构 / 视觉布局
- 改 `app/services/ai/prompts.py::watchtower_prompt`
- 改 RBAC / 权限
- 加新端点（只重构现有 2 个）

---

## §2 Backend

### 2.1 拆函数契约

```python
async def scan_churn_risk(
    db: AsyncSession, lookback: datetime, prev_lookback: datetime
) -> list[dict]:
    """Customers active in [prev_lookback, lookback) but silent in [lookback, now).
    Returns: [{customer_id, name, level, industry, signal}], max 20.
    """

async def scan_order_drop(
    db: AsyncSession, lookback: datetime, prev_lookback: datetime
) -> list[dict]:
    """Per-customer order count prev vs recent; drop >50% with prev>=3.
    Returns: [{customer_id, name, prev_orders, recent_orders, drop_pct}], max 20.
    """

async def scan_low_stock(db: AsyncSession) -> list[dict]:
    """Inventory 0 < qty <= safety_stock. Returns 20 rows: product_id, product_name, brand, qty, safety.
    """

async def scan_out_of_stock(db: AsyncSession) -> list[dict]:
    """Inventory qty <= 0. Returns 20 rows: product_id, product_name, brand.
    """

async def generate_ai_summary(anomalies: dict, total_alerts: int) -> dict:
    """Build alert_text from anomalies, call ai_client.chat_structured.
    On AI failure returns {severity: '正常', summary: 'AI分析暂不可用', top_actions: [], risk_areas: []}.
    """

async def _persist_customer_alerts(
    db: AsyncSession, anomalies: dict, now: datetime
) -> int:
    """Unchanged from current implementation. Returns events written.
    """
```

### 2.2 并行编排 + 缓存

`backend/app/api/v1/ai/_shared.py::watchtower_cached_scan(db, days_back)`:

```python
async def watchtower_cached_scan(db: AsyncSession, days_back: int) -> dict:
    key = _cache_key(endpoint="scan", days_back=days_back)
    try:
        cached = await cache_get_versioned("watchtower:scan", key)
        if cached is not None:
            return json.loads(cached)
    except (json.JSONDecodeError, TypeError):
        # bad cache, fall through to recompute
        pass

    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=days_back)
    prev_lookback = lookback - timedelta(days=days_back)

    # 4 scans in parallel; any exception is captured, domain returns []
    results = await asyncio.gather(
        scan_churn_risk(db, lookback, prev_lookback),
        scan_order_drop(db, lookback, prev_lookback),
        scan_low_stock(db),
        scan_out_of_stock(db),
        return_exceptions=True,
    )
    anomalies = {}
    for key_name, result in zip(
        ["churn_risk", "order_drop", "low_stock", "out_of_stock"], results
    ):
        if isinstance(result, Exception):
            logger.warning(f"watchtower.scan.{key_name} failed: {result}")
            anomalies[key_name] = []
        else:
            anomalies[key_name] = result

    total_alerts = sum(len(v) for v in anomalies.values())
    ai = await generate_ai_summary(anomalies, total_alerts)
    persisted = await _persist_customer_alerts(db, anomalies, now)

    result = {
        "scanned_at": now.isoformat(),
        "total_alerts": total_alerts,
        "severity": ai.get("severity", "正常"),
        "summary": ai.get("summary", ""),
        "top_actions": ai.get("top_actions", []),
        "risk_areas": ai.get("risk_areas", []),
        "alerts_persisted": persisted,
        "anomalies": anomalies,
    }

    await cache_set_versioned(
        "watchtower:scan", key,
        json.dumps(result, default=str),
        DASHBOARD_SCAN_CACHE_TTL,  # 300
    )
    return result
```

**`failed_domains` 仅写日志，不进入 response**（保持"同行为"约束：API shape 100% 不变）。监控走 logger / 后续 alerting。

### 2.3 cache_bump_version 触发点

| 写点 | 文件 | 新增 1 行 |
|---|---|---|
| Customer CRUD | `app/api/v1/customers/*.py` | `await cache_bump_version("watchtower:scan")` |
| Sales order create/update | `app/api/v1/sales/orders.py` | `await cache_bump_version("watchtower:scan")` |
| Inventory adjust | `app/api/v1/inventory/*.py` | `await cache_bump_version("watchtower:scan")` |
| Payment create | `app/api/v1/payments/*.py` | `await cache_bump_version("watchtower:scan")` (order_drop 受影响) |

通过 `grep -n "cache_bump_version" backend/app/api/v1/customers/*.py` 等定位现有 pattern，在已有 bump 调用后 append 一行。

### 2.4 daily-report 缓存

```python
DASHBOARD_REPORT_CACHE_TTL = 600  # 10 min
```

`watchtower_cached_report(db)` 包裹现有 `/ai/daily-report` 逻辑。**不在写点 bump**（避免 churn）。跨午夜通过 scheduler job bump：

```python
# app/jobs/scheduler.py
async def bump_watchtower_report_at_midnight() -> None:
    """跨午夜失效 daily report cache. cron: 5 0 * * * (UTC)"""
    await cache_bump_version("watchtower:report")
```

在 `app/jobs/scheduler.py` 的现有 scheduler 注册 entry，加 10 行代码（import + 函数 + scheduler.add_job 调用）。

### 2.5 响应 shape 不变

API contract 不动：
- `GET /ai/watchtower/scan?days_back=N` 返回 keys 跟现状 100% 一致（`scanned_at, total_alerts, severity, summary, top_actions, risk_areas, alerts_persisted, anomalies{churn_risk, order_drop, low_stock, out_of_stock}`）。**严格零新增字段**。失败的域通过 logger 暴露，不进 response。
- `GET /ai/daily-report` 同样 100% 一致。

---

## §3 Frontend

### 3.1 组件树

```
WatchtowerDashboard (page, route entry, ~80 行)
└─ <ModuleShell>                 // @/ui, existing
   ├─ <ScanHeader                 // new
   │    scanned_at={...}
   │    loading={isFetching}
   │    onRefresh={refetch}       />
   ├─ <KpiCards                   // new
   │    totalAlerts={...}
   │    severity={...}
   │    riskAreas={...}
   │    domainDistribution={...}  />
   ├─ <AiSummary                  // new
   │    text={...}                />
   ├─ {top_actions?.length > 0 &&
   │     <TopActions              // new
   │       items={...}            />}
   └─ <AnomalyTable               // new
        rows={allAnomalies}       />
```

### 3.2 数据流

```typescript
import { useApiQuery } from "@/lib/queries";
import { getWatchtowerScan } from "@/api";  // api/ai.ts, no change

const SCAN_LOOKBACK_DAYS = 90;
const query = useApiQuery<WatchtowerScanResponse>(
  ["watchtower", "scan", SCAN_LOOKBACK_DAYS],
  `/ai/watchtower/scan?days_back=${SCAN_LOOKBACK_DAYS}`,
  null,
  { staleTime: 60 * 1000, refetchInterval: false },
);
const { data, isLoading, isFetching, error, refetch } = query;
```

- `staleTime: 60s`：与后端 300s cache 错峰，60s 内重复进入页面用 React Query 缓存不发请求
- `refetchInterval: false`：用户主动点刷新，不轮询
- `isLoading` 首次 / `isFetching` 静默刷新（按钮 spinner 用）

### 3.3 加载 / 错误 / 空态

| 状态 | 处理 |
|---|---|
| `isLoading` 首次 | `<FullPageLoader>` 来自 `@/ui` |
| `error` | `<Alert type="error" message={getApiErrorMessage(error)} action={<Button onClick={refetch}>重试</Button>} />` |
| `data` 加载完但 `total_alerts=0` | `<EmptyState description="未检测到异常，系统运行正常" />` 来自 `@/ui` |
| `severity` 异常 | `<KpiCards>` 内部按 severity 选 StatusTag tone: '紧急' → danger, '需关注' → warning, '正常' → success |

### 3.4 拆分粒度

| Component | Props | State | CSS module |
|---|---|---|---|
| `ScanHeader` | `scanned_at: string; loading: bool; onRefresh: () => void` | 无 | `ScanHeader.module.css` |
| `KpiCards` | `totalAlerts: number; severity: string; riskAreas: string[]; domainDistribution: Array<[string, number]>` | 无 | `KpiCards.module.css` |
| `AiSummary` | `text: string` | 无 | `AiSummary.module.css` |
| `TopActions` | `items: string[]` | 无 | `TopActions.module.css` |
| `AnomalyTable` | `rows: AnomalyRow[]` | 无 | `AnomalyTable.module.css` |

全部 function component, 无 useState/useEffect, 父管 query 子纯展示.

### 3.5 `types/watchtower.ts`

```typescript
export type AnomalyDomain = "churn_risk" | "order_drop" | "low_stock" | "out_of_stock";

export interface AnomalyRow {
  domain: AnomalyDomain;
  domainLabel: string;
  // backend keys, partial — see backend §2.1
  customer_id?: number;
  product_id?: number;
  name?: string;
  signal?: string;
  prev_orders?: number;
  recent_orders?: number;
  drop_pct?: number;
  qty?: number;
  safety?: number;
  brand?: string;
}

export interface WatchtowerScanResponse {
  scanned_at: string;
  total_alerts: number;
  severity: "紧急" | "需关注" | "正常";
  summary: string;
  top_actions: string[];
  risk_areas: string[];
  alerts_persisted: number;
  anomalies: Record<AnomalyDomain, AnomalyRow[]>;
}
```

### 3.6 颜色 / tokens 替换

| 现状 | 目标 |
|---|---|
| `style={{ color: "#ff4d4f" }}` | CSS module class `styles.alert`, 引用 `semantic.danger` |
| `style={{ color: "#52c41a" }}` | CSS module class `styles.ok`, 引用 `semantic.success` |
| `style={{ marginBottom: 16 }}` | 删除, 改 CSS module 布局 (flex / gap) |
| `severityColor` 函数 | 删除, 用 `<StatusTag tone={...}>` prop |
| `<Tag color="red">` | `<StatusTag tone="danger">` |
| magic 颜色字面量 | 全部走 `design-tokens.ts` |

`design-tokens.ts` 已有 `semantic.{success,warning,danger,info,neutral}`（含 `+Bg` 浅色变体）+ `space.*` + `radius.*` + `fontSize.*` —— **足够, 不新增 token, 不引第三方**。CSS module 文件 `import { semantic, space } from "@/design-tokens"` 引用。

### 3.7 文件改动清单

| 文件 | 改动 |
|---|---|
| `pages/dashboard/WatchtowerDashboard.tsx` | 重写 222 → ~80 行 |
| `pages/dashboard/WatchtowerDashboard.module.css` | 新, 壳布局 |
| `pages/dashboard/components/ScanHeader.tsx` | 新 |
| `pages/dashboard/components/ScanHeader.module.css` | 新 |
| `pages/dashboard/components/KpiCards.tsx` | 新 |
| `pages/dashboard/components/KpiCards.module.css` | 新 |
| `pages/dashboard/components/AiSummary.tsx` | 新 |
| `pages/dashboard/components/AiSummary.module.css` | 新 |
| `pages/dashboard/components/TopActions.tsx` | 新 |
| `pages/dashboard/components/TopActions.module.css` | 新 |
| `pages/dashboard/components/AnomalyTable.tsx` | 新 |
| `pages/dashboard/components/AnomalyTable.module.css` | 新 |
| `types/watchtower.ts` | 新 |
| `pages/dashboard/dashboard.css` | **不动**（index.tsx 在用） |
| `pages/dashboard/index.tsx` (Sales Dashboard) | **不动**（显式 out of scope） |
| `api/ai.ts` | 不动 (`getWatchtowerScan` 已在) |

---

## §4 错误处理 + 测试

### 4.1 错误处理

| 层 | 错误 | 处理 |
|---|---|---|
| 后端 scan 4 域 | `asyncio.gather(return_exceptions=True)` | 该域返回 `[]` + `logger.warning`（**不进 response**，保持 API shape 不变） |
| 后端 AI 失败 | `generate_ai_summary` 内部 try/except | fallback `{severity: 正常, summary: 'AI分析暂不可用', top_actions: [], risk_areas: []}` |
| 后端 cache 反序列化 | try/except 包 cache_get | 坏值丢弃, 重新计算 |
| 前端 query error | useApiQuery 暴露 | `<Alert type="error">` + `<Button onClick={refetch}>重试</Button>` |
| 前端 retry | CLAUDE.md "retry 1" 默认 | 不修改 |
| 前端字段缺失 | TS strict + `?? '-'` 兜底 | 集中在 `types/watchtower.ts` 定义 |

### 4.2 Backend pytest (12 个)

`backend/tests/services/test_watchtower_service.py`:
1. `test_scan_churn_risk` — 2 prev + 1 recent → 1 churn
2. `test_scan_churn_risk_empty` — no prev → []
3. `test_scan_order_drop` — prev=10 recent=1 → drop 90%
4. `test_scan_order_drop_below_threshold` — prev=2 → 不入选
5. `test_scan_low_stock` — 0<qty<=safety 入, qty<=0 不入
6. `test_scan_out_of_stock` — qty<=0 入, qty>0 不入
7. `test_generate_ai_summary_no_anomalies` — `anomalies={}` → alert_text='无明显异常'
8. `test_generate_ai_summary_failure` — ai_client 抛 → severity='正常' fallback

`backend/tests/api/v1/ai/test_watchtower.py`:
9. `test_scan_endpoint_shape` — response keys match §2.5
10. `test_scan_endpoint_unauth` — 无 token → 401
11. `test_scan_all_cached_hit` — 第 2 次 0 DB queries
12. `test_scan_all_cached_bump` — 写客户后 → miss
13. `test_daily_report_cached` — 第 2 次 0 DB

### 4.3 Frontend vitest (9 个)

`frontend/src/test/dashboard/`:
1. `WatchtowerDashboard.test.tsx::renders_loading`
2. `WatchtowerDashboard.test.tsx::renders_data`
3. `WatchtowerDashboard.test.tsx::renders_error`
4. `WatchtowerDashboard.test.tsx::renders_empty`
5. `WatchtowerDashboard.test.tsx::refresh_button`
6. `KpiCards.test.tsx::severity_tone` — 紧急 → danger
7. `KpiCards.test.tsx::risk_areas_render`
8. `AnomalyTable.test.tsx::renders_rows`
9. `AnomalyTable.test.tsx::empty_state`

### 4.4 覆盖目标

CLAUDE.md: service 80% / api 70% / utils 90% / 前端组件 60%. `watchtower_service` 拆后单文件 ~150 行, 目标 ≥ 80% line coverage (`make test-backend-cov`).

### 4.5 TDD 顺序

```
1. RED:   test_scan_churn_risk (commit 失败态)
2. GREEN: 实现 scan_churn_risk
3. RED→GREEN: 重复 4 个 scan 函数
4. RED:   test_generate_ai_summary
5. GREEN: 实现 (含 try/except fallback)
6. RED:   test_scan_endpoint_shape / test_scan_endpoint_unauth
7. GREEN: 路由 + _shared.py
8. RED:   test_scan_all_cached_hit / bump
9. GREEN: 实现 cache + bump 写点
10. RED→GREEN: 前端 vitest, 逐 component
11. FINAL: make lint + make test 全绿
```

---

## §5 风险 + 回滚

### 5.1 风险矩阵

| 风险 | 严重度 | 概率 | 缓解 |
|---|---|---|---|
| API shape drift | 高 | 低 | test_scan_endpoint_shape + types/watchtower.ts 双保险 |
| Cache 命中率低, AI 重复打 | 中 | 中 | 300s TTL + 4 个 bump 写点, 监控 X-Cache: HIT 比例 |
| AI summary 漏报 | 中 | 中 | fallback 文案改为 "AI分析暂不可用 (scanned at X)" + UI tooltip |
| 前端 CSS 拆分后视觉回归 | 中 | 中 | diff 重点颜色 / 间距 / 字号; vitest snapshot |
| Scope 蔓延 | 中 | 高 | 不动 dashboard.py / SalesDashboard.tsx / 任何其他页面 |
| 测试假覆盖 | 中 | 中 | 用真 SQLite fixture, 只 mock ai_client |
| TDD 反向 | 中 | 中 | 用 test-driven-development skill, 每节 "RED 先 commit 失败态" |
| /ai/daily-report 跨午夜 cache stale | 低 | 中 | scheduler job bump_watchtower_report_at_midnight, cron 5 0 * * * |

### 5.2 回滚

- **A: CI 红灯** → 修 → push
- **B: 生产报警 (response shape / cache 命中率 0% / AI 翻车)** → `git revert <merge-commit>`, watch 5min, debug → 新 fix PR. **不** `git reset --hard` 强推
- **C: 单个写点 bump 误触发** → 不可能死循环 (bump 仅触发下次 miss 重算, 不会反复 miss), 最坏情况等同未加 cache
- **D: 拆函数后 import 链乱** → 路径单向, 拆函数不改 path, 风险低

### 5.3 监控 / Success criteria

合并后 1 周巡检:

```bash
# 缓存命中率
grep '"X-Cache": "HIT"' logs/api.log | wc -l
grep '"X-Cache": "MISS"' logs/api.log | wc -l

# AI 调用次数 (应下降)
grep 'ai_client.chat_structured' logs/api.log | grep watchtower | wc -l

# Grafana: /ai/watchtower/scan P50/P95 latency
# 目标: P95 ≤ 基线 / 2
```

合并验收:
- [ ] `make lint` 全绿
- [ ] `make test` 全绿 (含 12 backend + 9 frontend 新测)
- [ ] 端到端: 浏览器打开 `/dashboard/watchtower`, 5 个 section 渲染, StatusTag tone 正确, magic color 消失
- [ ] 第 2 次进入 (5min 内) `X-Cache: HIT` header

### 5.4 Out of scope (recap)

✗ `backend/app/api/v1/dashboard.py`
✗ `pages/sales/SalesDashboard.tsx` + css
✗ `pages/dashboard/` 之外任何页面
✗ 新增 / 删除 response fields
✗ 加 / 减 KPI 卡片 / section
✗ 重设计信息架构 / 视觉布局
✗ 改 `app/services/ai/prompts.py::watchtower_prompt`
✗ 改 RBAC / 权限
✗ 加新端点
