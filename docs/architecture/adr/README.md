# ADR Index — AIERP Architecture Decision Records

This directory captures the **why** behind significant architectural
choices. Each ADR is short (≤ 100 lines), dated, and titled after the
decision (not the alternative).

| # | Title | Date | Status |
|---|---|---|---|
| [001](001-cache-architecture.md) | Cache architecture: 18-family L1 LRU + L2 Redis | 2026-05-22 | Accepted |
| [002](002-event-bus-dispatch.md) | Event bus: in-process pub/sub with after-commit dispatch | 2026-05-22 | Accepted |
| [003](003-bounded-context-split.md) | Bounded-context split of API and service files | 2026-06-03 | Accepted |
| [004](004-use-case-routing.md) | Use case routing for sales business logic | 2026-06-03 | Accepted |
| [005](005-ai-orchestration-layering.md) | AI orchestration: trigger / orchestration / execution | 2026-06-04 | Accepted |
| [006](006-shared-ui-component-library.md) | Frontend shared UI component library v1 | 2026-06-04 | Accepted |

## Format

Each ADR follows the MADR (Markdown Any Decision Record) shape:

1. **Context and Problem Statement** — what forced the decision
2. **Decision Drivers** — what we optimized for
3. **Considered Options** — at least 2 alternatives, sometimes 3
4. **Decision Outcome** — what we picked and why
5. **Consequences** — both positive and negative

ADRs are **immutable** once accepted. If a decision is reversed, write
a new ADR that supersedes it (and link from the old one).

## How to add an ADR

```
# pick next 3-digit number
N=<next>
$EDITOR ${N:0:1}${N:1:1}${N:2:1}-short-title.md
# update this index, commit both files in one commit
```

The number is monotonic; never reuse. A new ADR that supersedes an old
one keeps its own new number but the body references the old one.
