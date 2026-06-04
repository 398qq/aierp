# ADR 004: Use case routing for sales business logic

- **Status**: Accepted
- **Date**: 2026-06-03
- **Author**: stage 1 of v6 design audit

## Context and Problem Statement

The audit (§6.1 Q1) raised a direction question: when we split
`sales.py` (952 lines, 9 bounded contexts), where does the **business
logic** go? Three options were on the table:

- **A. Services pattern** (old default): move logic to
  `app/services/sales/{opportunity,quotation,...}.py`; the API
  file becomes a thin 50-100 line adapter
- **B. Use case pattern** (chosen): move logic to
  `app/application/sales/{opportunity,quotation,...}_use_case.py`,
  with `app/application/uow.py` for transaction boundaries
- **C. Hybrid**: aggregate logic in `app/domain/sales/`, cross-
  aggregate orchestration in `app/application/`, simple CRUD in
  `app/services/`

The DDD-skeptic position (A) is that all of this is "just another
services layer with extra steps". The DDD-purist position (C) is
that A is the wrong abstraction and B is only half right.

The deciding factor: `app/api/v1/sales_v2.py` (the "ideal
architecture" demo file) already followed pattern B with 3 use
cases. The use case pattern was a **direction already chosen**;
the question was whether to land it or abandon it.

## Decision Drivers

- Use cases need **transaction boundaries** (multiple repository
  writes, must be atomic)
- Use cases need **after-commit event dispatch** (see ADR 002)
- Some endpoints are pure CRUD and don't need a use case (don't
  over-engineer; a `GET /customers/{id}` should not be a use case)
- The team is 2-3 engineers; an entire BDD-style domain layer
  is overkill, but use cases are a familiar pattern

## Considered Options

### A. Services pattern (default, status quo before v6)

Logic in `app/services/sales/opportunity.py` etc. The API file
becomes a 50-100 line adapter that just calls
`services.opportunity.create(db, data)`.

**Pros**: smallest change to existing code
**Cons**:
- DDD / new architecture never lands. The "ideal" `sales_v2.py`
  is permanently a demo.
- No transaction boundary: each service call is its own
  transaction. Atomic flows ("create order + write audit + bump
  cache") need careful session management by the caller.
- No after-commit event hook: cache busts and notifications have
  to be wired manually at the API layer.

### B. **Use case routing (chosen)**

API file is the thin adapter. Business logic moves to
`app/application/sales/{opportunity,quotation,...}_use_case.py`.
Each use case takes a `UoW` (Unit of Work) as a parameter and
explicitly demarcates the transaction:

```python
async def confirm_order(uow: UoW, order_id: int, actor: Actor) -> Order:
    async with uow:
        order = await uow.orders.get(order_id)
        order.confirm(actor=actor)              # domain mutation
        uow.track_event(OrderConfirmed(...))     # for after-commit
        await uow.commit()                       # bust cache + notify
    return order
```

The use case does **not** know about FastAPI, HTTP, or Pydantic —
it takes domain objects, returns domain objects. The API layer
adapts the request → use case call → response.

**Pros**:
- Transaction boundary is explicit (one place per use case)
- After-commit event dispatch is automatic via the UoW
- The use case is unit-testable with no FastAPI or HTTPX setup
- The `sales_v2.py` ideal architecture becomes reality
- Pure CRUD endpoints stay in the API file — no ceremony for
  a 3-line `GET`

**Cons**:
- More files per endpoint (1 use case file + 1 API file for the
  non-trivial endpoints)
- The "what's a use case" call is judgment: a `GET /customers`
  paginated list is not a use case; a `POST /customers/{id}/merge`
  is. The line is fuzzy and varies per author.

### C. Hybrid

Aggregate root logic in `app/domain/sales/`, cross-aggregate
orchestration in `app/application/`, single-aggregate CRUD in
`app/services/`.

**Pros**: most DDD-correct
**Cons**:
- 3 places to look for a "how does X work" question
- Most endpoints in this codebase are not cross-aggregate; the
  domain layer would be 80% of the code
- The team is 2-3 engineers, not 20; the cognitive cost is real

## Decision Outcome

Chose **B** because the existing `sales_v2.py` already demonstrated
the pattern works for this codebase, and the cost (more files) is
bounded — use cases are only required for flows with non-trivial
business logic. Pure CRUD stays in the API file.

After v6 stage 1 the sales bounded context has 3 use cases:

| Use case | File | Replaces |
|---|---|---|
| `ConfirmOrder` | `app/application/sales/confirm_order.py` | inline `sales.py:300-340` |
| `CancelOrder` | `app/application/sales/cancel_order.py` | inline `sales.py:340-380` |
| `ConvertQuotation` | `app/application/sales/convert_quotation.py` | inline `sales.py:380-440` |

After v6 stage 2 the procurement bounded context has 1 use case
(`three_way_match`), with 18 unit tests covering amount/percent
tolerance, status transitions, and audit trail.

The remaining 80% of endpoints (CRUD, list, simple get-by-id) stay
in the API file. A new "non-trivial" endpoint that has multi-entity
state changes, audit, and event emission should add a use case.

## Consequences

**Positive**

- Transaction boundary is now an `async with uow:` you can read in
  one place
- The UoW's after-commit event dispatch is automatic; no manual
  `cache_bump_version` calls in the use case
- Use case unit tests run without HTTP (no TestClient, no DB
  session lifecycle for the test): pure in-memory or with a
  tiny session fixture
- Domain code is now actually testable in isolation; the audit's
  115 new domain tests in stage 2 would not have been possible
  without this

**Negative / Known Limitations**

- "Is this a use case?" requires judgment. A rule of thumb: if the
  endpoint mutates more than one entity OR emits events OR has
  business rules (e.g. "can't confirm a draft that's already
  cancelled"), it's a use case. If it's a single-row CRUD, no.
- The use case tests don't exercise the HTTP layer end-to-end.
  A `tests/api/v1/sales/test_confirm_order_endpoint.py` integration
  test exists to cover the full stack.
- Adding a use case is more files than adding a function. For
  trivial flows, this is overhead.

## Follow-up

- v6.1: extract a `UseCase` Protocol that all use cases implement
  (single-method `execute(...)`), so a registry can list them
  (for documentation, metrics, and a possible future CLI runner)
- v6.2: stage 1.5 already noted the procurement domain tests; if
  more bounded contexts grow use cases, consider a small
  `app/application/{bounded_context}/__init__.py` that re-exports
  them, so importers can write
  `from app.application.sales import ConfirmOrder`
