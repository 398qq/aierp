# ADR 002: Event bus — in-process pub/sub with after-commit dispatch

- **Status**: Accepted
- **Date**: 2026-05-22
- **Author**: v3 perf report

## Context and Problem Statement

Several cross-cutting concerns need to react to writes:

- Cache invalidation: a sales-order write should bust the
  `sales_orders` cache family
- Notifications: a high-risk opportunity should notify the manager
- AI pipeline: a quotation save triggers `after_quotation_save` for
  AI enrichment
- Audit: a state transition should log who did what

Without a bus, every endpoint handler would need to call each
subscriber manually. Adding a 4th subscriber means editing 30+
handlers. We need **decoupled event-driven fan-out**.

## Decision Drivers

- Subscribers are in-process (no Kafka / RabbitMQ / Redis-Streams
  overhead)
- All subscribers must run **after the database commit**, never
  before (otherwise they could observe uncommitted data)
- A subscriber failure must not block the original request — and
  must not cause the entire fan-out to fail
- Some subscribers are sync (cache bust), some async (notifications
  via background task)

## Considered Options

### A. Direct function calls (no bus)

Each handler explicitly calls `cache_bump_version`,
`create_notification`, `after_quotation_save`, …

**Pros**: zero indirection
**Cons**: 4+ subscribers × 30+ handlers = 120+ call sites; adding a
5th subscriber = 30+ file edits

### B. Message queue (Kafka / Redis-Streams)

External event log, durable, replayable.

**Pros**: durable, scales, decoupled
**Cons**: 50ms+ latency per event, new infrastructure, ops burden,
overkill for in-process fan-out

### C. **In-process event bus with deferred dispatch (chosen)**

A simple `EventBus` class with `subscribe(event_type, handler)` and
`publish(event)` semantics. Subscribers are registered at module
import time. The bus tracks events on a Unit of Work (UoW);
**events are dispatched only after the UoW commits** — never before.

Three subscription idioms supported:

```python
@bus.subscribe                       # auto-detect from type hint
@bus.subscribe(EventType.X)          # explicit
bus.subscribe(EventType.X, handler)  # imperative (for tests)
```

`publish` is also a context manager for tests that don't go through
the UoW (e.g. unit-testing a domain aggregate in isolation).

**Pros**:
- Adding a subscriber is a single function + `@bus.subscribe` (one
  file edit, not 30+)
- After-commit dispatch is automatic and enforced by the UoW
- Subscriber exceptions are caught and logged, not re-raised, so
  one bad subscriber can't poison the rest
- Zero new infrastructure

**Cons**:
- In-process only — does not survive worker restart
- No replay / no event log
- Subscribers must be idempotent (a subscriber might fire twice if
  both the UoW and an explicit publish path exist)

## Decision Outcome

Chose **C** because all current subscribers are in-process (cache,
notifications, AI enrichment, audit). The UoW-after-commit guarantee
is non-negotiable and a simple in-process bus enforces it cleanly.

The bus lives in `app/core/event_bus.py`. The UoW lives in
`app/application/uow.py`. The 4 current event types:

| Event | Subscribers | Sync / Async |
|---|---|---|
| `CustomerSaved` | `cache_bump_version("customers")`, `audit_log` | sync |
| `SalesOrderSaved` | `cache_bump_version("sales_orders")`, `after_order_save` AI hook | sync + async |
| `QuotationSaved` | `cache_bump_version("sales_quotations")`, `after_quotation_save` AI hook | sync + async |
| `OpportunitySaved` | `cache_bump_version("sales_opportunities")`, `after_opportunity_save` AI hook | sync + async |

The 4 main UoW-using flows are: `confirm_order`, `cancel_order`,
`convert_quotation`, `three_way_match` (and the new ones in stage 2).

## Consequences

**Positive**

- Adding a subscriber is 1 file, ~10 lines (e.g. a hypothetical
  `SalesOrderSaved → email sales team`)
- Subscriber failures don't break the user request
- The UoW-after-commit rule is tested in `tests/test_uow.py`
  (covered by the use-case tests added in stage 2)

**Negative / Known Limitations**

- Subscribers must be idempotent (no deduplication; if a subscriber
  retries due to a network blip, it could fire twice)
- No event log means debugging "why didn't the cache bust?" requires
  a Redis MONITOR side-channel
- Migrating to a real message queue later is a breaking change for
  subscribers; in-process callers have to be wrapped

## Follow-up

- v6.1: add a structured-event-log recorder for postmortems (write
  the event JSON to a local file before dispatch, with TTL on the
  file)
- v7: if we ever run multi-machine, swap the in-process bus for
  Redis Streams behind the same `EventBus` interface (subscribers
  don't change)
