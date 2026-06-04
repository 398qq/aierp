# ADR 005: AI orchestration — trigger / orchestration / execution

- **Status**: Accepted
- **Date**: 2026-06-04
- **Author**: stage 2 of v6 design audit

## Context and Problem Statement

Pre-v6, AI orchestration lived in 3 large single-file services:

- `app/services/nlp_query_service.py` — 542 lines, 6 domain
  contexts, 1 LLM call
- `app/services/sales_ai_pipeline.py` — 156 lines, 2 fire-and-forget
  enrichment tasks, 2 advisory flow validations
- `app/services/orchestration/{global,customer,product}_orchestrator.py`
  — 386 / 281 / 282 lines each, mixing event subscribers,
  decision logic, and AI tool calls

The audit (§1.5) called out the problem: "13 个 `*_intel_service.py`
+ AI 编排层 1,000 行单文件里三个全混". Translation: three
responsibilities were mixed in the same file — the **trigger**
(what fires the AI), the **orchestration** (which AI agent /
tool to use), and the **execution** (actually call the LLM).

Concretely, in `nlp_query_service.py`:

- The trigger was the API caller invoking `natural_language_query`
- The orchestration was the heuristic "if 1 domain detected, build
  full context for that domain + summary for the rest" (lines
  411-426)
- The execution was the 6 `_build_*_context` SQL functions plus the
  `ai_client.chat_structured` call

All three in one file. Changing the heuristic required reading 542
lines. Adding a 7th domain required editing the SQL, the builder
registry, the detection patterns, and the orchestration — all in
the same file.

## Decision Drivers

- AI failures must not block user requests (graceful degradation
  is non-negotiable for the "ask anything" chat feature)
- The LLM client (`app/services/ai/client.py`) is a single
  dependency, so the execution layer is uniform
- Detection is pure-Python (no I/O) and can be unit-tested without
  a database
- SQL context building is the largest part (~440 lines) and is
  the most likely to change as the ERP schema evolves
- The orchestration heuristic (when to build full vs summary
  context) is the most likely to change as we tune the LLM
  prompt

## Considered Options

### A. Leave it alone

The 542-line file works. Don't refactor for refactor's sake.

**Pros**: zero risk, zero churn
**Cons**:
- The audit explicitly flagged this as a structural debt
- A new domain (e.g. "marketing campaigns") requires editing 3
  places in one file, not 3 places in 3 files
- A new heuristic rule (e.g. "if the query is in English, only
  build finance context") requires reading the orchestration
  block to know where to add it

### B. **Three-layer split (chosen)**

For each AI service, split into:

- **Trigger** (the API caller invokes this)
- **Orchestration** (decides which contexts / agents / tools)
- **Execution** (does the SQL, the LLM call, the side effect)

For `nlp_query_service.py` specifically, the result is a
4-file package:

```
app/services/nlp_query/
├── __init__.py     # public API re-export (1 function)
├── detection.py    # pure-Python keyword scoring
├── context.py      # SQL context builders (6 full + 6 summary)
└── service.py      # orchestration (the rule) + LLM call wrapper
```

The `__init__.py` re-exports the single public function
`natural_language_query`, so the caller
(`app/api/v1/ai/nlp_ai.py`) imports the same name it always did.

`sales_ai_pipeline.py` was already well-organized at 156 lines
(3 sections, public API clear), so it was left as-is.

The 3 `app/services/orchestration/*_orchestrator.py` files were
not split in stage 2 (out of scope; they have a similar 3-layer
shape and would benefit from the same treatment in a follow-up
ADR — see below).

**Pros**:
- Adding a 7th domain: edit `detection.py` (1 line), edit
  `context.py` (1 builder + 1 summary), done
- Changing the orchestration rule: edit `service.py` only
- Detection is now a pure function, unit-testable in microseconds
  without a DB
- Execution (SQL + LLM) is isolated from orchestration (heuristic)
  so either can be tuned or replaced without touching the other

**Cons**:
- 4 files instead of 1
- A new contributor has to learn the package layout
- The `__init__.py` re-export adds one indirection

### C. Generic orchestration framework

Build a `class Orchestrator` with `register_trigger`,
`register_decision`, `register_executor` and a config-driven
flow.

**Pros**: maximum flexibility
**Cons**:
- 3-4 weeks of framework work for 3 services that don't need it
- The framework becomes a dependency of every AI service; we
  inherit its bugs
- 13 `*_intel_service.py` files have varied shapes; a generic
  framework would either be too rigid (forces 1 shape) or too
  flexible (becomes a DSL nobody can read)

## Decision Outcome

Chose **B** for `nlp_query_service.py`. The split is concrete:

- `detection.py` — 43 lines, pure-Python keyword matching
- `context.py` — 339 lines, 6 full + 6 summary SQL builders +
  dispatchers
- `service.py` — 109 lines, the heuristic + the LLM call
- `__init__.py` — 12 lines, public API re-export

The caller (`app/api/v1/ai/nlp_ai.py`) updates one import line.
Public surface (`natural_language_query(db, query)`) is unchanged.

`sales_ai_pipeline.py` was not refactored because it was already
156 lines, already 3-section-organized (trigger hooks, bg
enrichment, flow validation), and the audit's "537 lines" figure
was a stale snapshot from an earlier round.

The 3 `app/services/orchestration/*_orchestrator.py` files are
**not** split in stage 2; that's a follow-up ADR (see below).

## Consequences

**Positive**

- `nlp_query` package: 4 files, each with one job
- The orchestration heuristic is now in one place (50 lines
  in `service.py`), so a reviewer can read it in 30 seconds
- The SQL is in one place (300+ lines in `context.py`), so a
  schema change is one file edit
- The detection is now unit-testable without a DB
- Caller API: 1 import line change, no behavior change

**Negative / Known Limitations**

- 4 files instead of 1 in this package
- The 3 `*_orchestrator.py` files in `app/services/orchestration/`
  have the same problem and were not refactored; they remain on
  the "next pass" list
- The 13 `*_intel_service.py` files (brand_intel, customer_intel,
  supplier_intel, …) similarly have 3-layer shapes but were not
  touched in stage 2

## Follow-up

- v6.1: write a 3-layer split ADR for the
  `app/services/orchestration/` files. Pattern is identical to
  this one; can be a 1-2 day follow-up.
- v6.2: `*_intel_service.py` family — same pattern. Total
  ~10-15 days of work, but each service is independent so it
  can be parallelized across PRs.
- v6.3: if AI orchestration grows further, consider a
  `app/services/ai/orchestration/` package that subsumes all
  the per-bounded-context orchestrators. Not before v6.2.
