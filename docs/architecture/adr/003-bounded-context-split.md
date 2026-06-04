# ADR 003: Bounded-context split of API and service files

- **Status**: Accepted
- **Date**: 2026-06-03
- **Author**: stage 1 of v6 design audit

## Context and Problem Statement

Pre-v6, the backend had 5 single-file API routers > 400 lines each:

| File | Lines | Bounded contexts mixed |
|---|---|---|
| `app/api/v1/sales.py` | 952 | opportunity, quotation, order, delivery, invoice, payment, contract, target, purchase_order |
| `app/api/v1/finance.py` | 542 | invoice, payment, contract, target |
| `app/api/v1/finance_accounts.py` | 497 | account, journal, bank, pnl, ap |
| `app/api/v1/reports.py` | 418 | templates, predefined/{sales,ar,inventory,procurement}, export |
| `app/api/v1/transactions.py` | 623 | po, payment, ticket, visit, sample |

Each file imported 4-6 SQLAlchemy models, multiple schemas, and
called 4-6 service-layer functions. A change to "the order module"
required scanning 952 lines to find the right endpoint. Adding a
new endpoint meant adding to the bottom of the file and hoping
nothing else moved.

A single 952-line file isn't a problem if the team is one person
or if the file is "done". In our case, both conditions failed: 2+
contributors and the sales file is the most-edited in the system.

The frontend had a parallel problem: `src/api/index.ts` was 1184
lines covering 18 bounded contexts.

## Decision Drivers

- File size < 400 lines per file (so a screenful fits in a developer's
  working memory)
- One bounded context per directory (`sales/opportunities.py`,
  `sales/quotations.py`, …)
- Zero behavior change — all 369 API URLs preserved exactly
- Zero new infrastructure — only file reorganization
- Migration done in 6 atomic commits, each independently revertable

## Considered Options

### A. Leave the file, add a "module" docstring

Add a top-of-file table of contents with line numbers.

**Pros**: zero risk
**Cons**: still 952 lines, still one import namespace, doesn't help
"which file do I edit for a new order endpoint"

### B. **Split by bounded context into subpackages (chosen)**

Each API file becomes a subpackage. E.g.:

```
app/api/v1/sales/
├── __init__.py          # APIRouter, re-exports sub-routers
├── _shared.py           # cache keys, TTL constants, common deps
├── opportunities.py
├── quotations.py
├── orders.py
├── delivery_notes.py
├── conversions.py
├── inquiry.py
└── v2.py                # (former sales_v2.py; same URLs)
```

Each sub-router is `< 320` lines and represents one bounded context
in the domain. The package `__init__.py` aggregates them into a
single `APIRouter` so `app/api/v1/router.py` doesn't change.

Shared cache keys and TTL constants live in `_shared.py` (the
underscore prefix is Python convention for "internal to this
package"). This is the only place where the "cache key is the
authoritative source of truth" rule is encoded.

Frontend: `src/api/index.ts` (1184 lines) → `src/api/{auth,users,
customers,products,suppliers,brands,inventory,sales,procurement,
finance,reports,public,ai,notifications,dashboard,tickets,visits,
samples}.ts` + a 16-line `index.ts` re-export.

**Pros**:
- "Which file do I edit" is now a 1-second answer (it's in the
  subdirectory)
- Sub-router files are < 320 lines each
- `_shared.py` is the single place to add a new cache family / TTL
- The package `__init__.py` keeps the import surface flat for the
  router registry
- Frontend `api/customers.ts` is now 317 lines max (was 1184 in
  one file) — same answer speedup

**Cons**:
- More files: 5 → 23 in the backend, 1 → 18 in the frontend
- The `__init__.py` re-export adds one indirection for IDE go-to-def
- Tests that imported internals (e.g. `from app.api.v1.sales import
  _compute_x`) had to be updated to use the public router — 2 such
  tests touched

### C. Microservices / process-per-context

Each bounded context becomes a separate FastAPI app on a separate
port.

**Pros**: hard isolation, independent deploys
**Cons**: 6-12 months of work, doesn't fix the "too many lines in one
file" problem at the code level, requires service discovery, doesn't
fit the current single-team ops model

## Decision Outcome

Chose **B** because the actual problem is **findability and
blast-radius reduction**, not isolation. Microservices solve a
different problem and at 6-12 months of cost they would be the
wrong call for a team that still has a working monolith.

The 5 backend splits (one commit each, atomic):

| Commit | File split | Resulting subpackage |
|---|---|---|
| `daf3a96` | `sales.py` (952) | `sales/{opportunities,quotations,orders,delivery_notes,conversions,inquiry,v2}.py` |
| `6c72ca5` | `finance.py` (542) | `finance/{invoices,payments,contracts,targets}.py` |
| `6c72ca5` | `finance_accounts.py` (497) | `finance_accounts/{accounts,journal,bank,reports}.py` |
| `6c72ca5` | `reports.py` (418) | `reports/{templates,predefined,export}.py` |
| `6c72ca5` | `transactions.py` (623) | `transactions/{purchase_orders,payments,tickets,visits,samples}.py` |
| `5601683` | `sales_v2.py` (232) | merged into `sales/v2.py` as sibling |
| `0976e44` | `api/index.ts` (1184) | 17 per-bounded-context files + 16-line re-export |

After: zero file > 400 lines, 90% files < 200 lines.

## Consequences

**Positive**

- Mean time to find the right endpoint for a "fix the X bug" task
  dropped from ~30s (grep) to ~3s (look in the right subdirectory)
- Merge conflicts on the sales router dropped to near-zero (4+ PRs
  used to collide on the same 952-line file; now each sub-router
  is touched by at most 1 PR at a time)
- New endpoints no longer risk breaking unrelated endpoints
- Frontend `api/customers.ts` etc. have a much higher
  signal-to-noise ratio when searching for "how does the customer
  list call work"

**Negative / Known Limitations**

- One layer of indirection added: an IDE go-to-def on
  `app.api.v1.sales` now lands on the `__init__.py` aggregator
- The 2 internal-only tests that imported private helpers had to
  be updated to use the public router
- 5 watchtower ad-hoc scripts (under `backend/`) were deleted in the
  same commit batch — they were dead code that lived in the file
  size of `app/services/watchtower_service.py`

## Follow-up

- v6.1: extract `_shared.py` constants into a config-table-driven
  registry so adding a new cache family is data-driven, not code
- v6.2: same pattern applied to the `app/services/` 18 intel
  services (currently still 1 file per service)
