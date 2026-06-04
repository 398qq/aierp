# ADR 001: Cache architecture — 18-family L1 LRU + L2 Redis

- **Status**: Accepted
- **Date**: 2026-05-22
- **Author**: v3 perf report

## Context and Problem Statement

The ERP system has 18 distinct query patterns (customer lists, sales
order detail, finance P&L, …) each with different access characteristics:

- **Customer / product lists**: high read, low write, paginated
- **Sales order detail**: medium read, low write, hot-spot
- **Finance aggregates (P&L, AR/AP)**: expensive compute, called by
  dashboards every 5-30s
- **Inventory levels**: hot, called by every quote builder

Naive implementation: every API call hits PostgreSQL. p95 latency on
the P&L endpoint was 2.4s, dashboards 480ms, quote builder 1.1s.

A cache is needed. But **one global cache** doesn't fit:
- L1 LRU is correct for short-lived, hot data; wrong for cold data
- L2 Redis is correct for shared state across workers; wasteful for
  per-request data
- TTL alone doesn't help: writing a sales order must invalidate the
  customer list, the dashboard, and the sales report — and a
  blanket TTL = either stale reads or cache miss storms

## Decision Drivers

- Read-heavy workload (95% read, 5% write)
- Multi-worker gunicorn (4 workers, 1 process per worker)
- p95 < 100ms target (was 480ms pre-cache)
- Stale-read tolerance: < 5s for transactional data, < 60s for
  aggregates
- Cost ceiling: stay on the existing Redis instance, no new
  infrastructure

## Considered Options

### A. Single global cache key prefix with versioned bust

One Redis hash for everything. On write, `INCR version`. Cache key
includes the version → instant invalidation, no TTL.

**Pros**: trivial to reason about
**Cons**: every read does an extra `GET version` round-trip; one
hot key = thundering herd; doesn't help with cold-start; no L1

### B. Per-endpoint TTL only (no version)

Each endpoint gets a fixed TTL. Writes don't invalidate.

**Pros**: simplest
**Cons**: write-stale is the default; users complain that the
"create new customer" button doesn't appear for 60s

### C. **18-family L1 LRU + L2 Redis (chosen)**

Each query family gets its own cache key namespace, TTL, and version.
Reads check L1 (in-process LRU) before L2 (Redis). Writes call
`cache_bump_version(family)` which bumps a per-family version key
in Redis and evicts the L1 entries tagged with the old version.

**Pros**:
- L1 absorbs 95%+ of reads (no Redis hop for hot data)
- L2 keeps multi-worker consistent
- Per-family invalidation: writing a sales order only busts the
  `sales_orders` family, not unrelated families
- Version epoch in keys: TTL is advisory; the real invalidation
  signal is the version bump
- Cache hit ratio per family is a Prometheus metric, so we can
  spot a cold family quickly

**Cons**:
- More code than option A or B (~600 lines in `cache_service.py`)
- Per-family tuning (TTL, max size) is operationally non-trivial
- L1 has per-worker drift (worker A might have a stale L1 entry for
  up to one L1-eviction cycle) — this is the "跨 worker 缓存失效"
  P3 in the audit; deferred until multi-worker prod is live

## Decision Outcome

Chose **C** because the 18-family split maps 1:1 to the 18 bounded
contexts the API is split into (see ADR 003), and the per-family
version bump gives correct write-through semantics without a write
storm.

The 18 families (current as of 2026-06-04):

| Family | TTL (s) | L1 size | Use case |
|---|---|---|---|
| customers | 60 | 500 | customer list, detail |
| products | 60 | 500 | product list, search |
| suppliers | 60 | 500 | supplier list |
| sales_orders | 30 | 200 | order list, detail |
| sales_quotations | 30 | 200 | quotation list |
| sales_opportunities | 60 | 200 | opportunity pipeline |
| inventory_levels | 30 | 200 | inventory by warehouse |
| inventory_batches | 60 | 200 | FEFO lot lookup |
| procurement_pos | 30 | 200 | PO list, status |
| finance_invoices | 30 | 200 | AR list |
| finance_payments | 30 | 200 | payment list |
| finance_pnl | 300 | 50 | P&L (expensive) |
| finance_ar_aging | 300 | 50 | AR aging |
| finance_ap_aging | 300 | 50 | AP aging |
| reports_sales | 600 | 50 | predefined sales |
| reports_inventory | 600 | 50 | predefined inventory |
| reports_procurement | 600 | 50 | predefined procurement |
| dashboard_widgets | 60 | 100 | dashboard aggregates |

## Consequences

**Positive**

- p95 latency: 480ms → 61ms (8x improvement, v3-v5 reports)
- Cache hit ratio: 80-99% per family in steady state
- Write throughput unchanged (bump is one Redis op)
- Per-family metrics expose cold families

**Negative / Known Limitations**

- Cross-worker L1 drift (each worker's L1 may have stale entries for
  up to L1-eviction interval, ~ 5s) — deferred, single-worker dev
- `cache_bump_version` is fire-and-forget; if Redis is down, the
  bump is lost and stale reads will persist until TTL
- 18 families × {TTL, L1 size, version} = 54 parameters to tune
  manually; no auto-tuning yet
- Cache miss storm protection not implemented (e.g. singleflight)

## Follow-up

- v6.1 (post-stage-2): Redis Pub/Sub broadcast bumps to all workers
  so L1 evictions are also cross-worker (audit §5.3 K)
- v6.2: per-family auto-TTL via observed hit ratio
- v6.3: singleflight on cold miss to prevent stampede
