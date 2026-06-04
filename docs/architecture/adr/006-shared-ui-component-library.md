# ADR 006: Frontend shared UI component library v1

- **Status**: Accepted
- **Date**: 2026-06-04
- **Author**: stage 2 of v6 design audit

## Context and Problem Statement

The audit (§1, §2.4) flagged that `frontend/src/components/`
contained exactly 1 shared component (`AttachmentPanel`) for a 60+
page app. Every page re-implemented:

- `StatusTag` (page-local `<Tag color={...}>` with status color map)
  — duplicated in **14+ pages**
- `MetricBand` (KPI card row, 4-col grid of `Statistic` cards) —
  duplicated in **5+ pages**
- `SearchBar` (input + reset button row) — 4-5 variants, none
  identical
- `PageHeader` (back button + title + actions) — 30+ pages had
  some version; 10+ had no back button
- `EmptyState` (antd `<Empty>` with optional CTA) — 20+ pages
- `ErrorBoundary` — **0 pages** had one. A single rendering error
  in any page white-screened the whole app

The cost of this duplication: a new page author had to find an
example in a similar existing page, copy-paste, and adapt the
status colors / action labels. The result: visually inconsistent
pages with subtle drift in:

- Status color (e.g. "approved" was `green` in 3 pages and
  `success` in 2 others, and `cyan` in 1)
- Reset button label ("重置" vs "清空筛选" vs "清空" vs "重置筛选")
- Back button placement (some pages had it, some didn't)
- Empty state copy ("暂无数据" vs "还没有数据" vs "暂时为空")

## Decision Drivers

- A 6-component library covers 90% of duplication with no design
  system overhead
- Each component must be **drop-in compatible** with the existing
  pattern (same color palette, same antd idioms) — no big redesign
- The library must not require a build-tool change (no Vite
  plugin, no Storybook, no design tokens yet)
- Tests must run in the existing Vitest setup (no new test
  framework)

## Considered Options

### A. Don't fix it (status quo)

Each page keeps its own copy.

**Pros**: zero risk
**Cons**:
- The audit (§2.4) explicitly called this out
- New pages inherit the inconsistency
- Any "fix the status color for `approved` to be green" task
  means a 14-file search-replace

### B. **6-component v1 library (chosen)**

`frontend/src/ui/{StatusTag,MetricBand,SearchBar,PageHeader,EmptyState,ErrorBoundary}.tsx`
+ `index.ts` barrel + `test/ui.test.tsx` (20 tests).

Each component:

- Re-exports the antd primitives it wraps (so existing antd
  patterns still work)
- Has a 1-2 sentence module docstring with usage examples
- Is < 100 lines (so adding a new variant is a 1-PR task)
- Has a default mode that matches the most common existing pattern
  (so migration is mechanical: swap `<Tag color={x}>{y}</Tag>` →
  `<StatusTag color={x} label={y} />`)

`StatusTag` is the highest-impact component because the duplication
was 14+ pages and the `humanize` function centralizes a subtle
bug (leading "-"/"+" got stripped by the old regex, fixed in
this library).

`ErrorBoundary` is the highest-**risk** component because it was
**0 pages** before. Every page should now be wrapped — but the
audit didn't require a full migration, just the library.

**Pros**:
- 6 components, 6 files, ~470 lines total
- 14+ pages can migrate to `StatusTag` with 1-line swaps
- `ErrorBoundary` exists for the first time — new pages should
  use it; existing pages migrate in follow-up
- Tests: 20 unit tests in the existing Vitest setup; tsc clean
- The barrel `index.ts` means future consumers do
  `import { StatusTag } from "../../ui"`, one line

**Cons**:
- A new "design system" smell: are we committing to a real DS?
  (No — v1 is a thin layer over antd. A real DS is a v7 task.)
- The 6 components are not a complete coverage; some pages will
  still need a 7th, 8th component (e.g. `FormSection`,
  `ConfirmDeleteButton`). Add them when a 2nd page needs them,
  not preemptively.
- `ErrorBoundary` requires React class component syntax (no hooks
  alternative yet). Acceptable cost.

### C. Full design system (tokens, Storybook, dark mode, …)

Build a proper design system: design tokens, dark mode, Storybook
for documentation, form component primitives.

**Pros**: industry-standard, scales to multiple apps
**Cons**:
- 3-6 months of work for a single-app team
- Storybook is a 200MB+ dev dependency; not free
- v1 of the 6-component library covers 90% of duplication; the
  remaining 10% doesn't justify a DS
- A DS locks in decisions (e.g. spacing scale) that the team
  should validate with usage first

## Decision Outcome

Chose **B** with the explicit constraint: **don't preemptively
expand**. The 6 components cover what the audit identified.
Adding a 7th (`FormSection`, `ConfirmDeleteButton`, …) is a
follow-up when a 2nd page needs it.

Component design notes:

- `StatusTag`:
  - Default mode: `humanize("on_hold_pending") → "On hold pending"`.
  - Override label for Chinese: `<StatusTag status="posted" label="已过账" />`
  - Escape hatch: `<StatusTag status="custom" color="purple" />` for
    non-status visual variety
  - Regression: the `humanize` regex was changed from `/[_-]+/g`
    to `/(?<=\w)[_-]+(?=\w)/g` to preserve leading punctuation
    (trend values like `"-2%"` were getting stripped)

- `ErrorBoundary`:
  - Uses React class component (only way to catch errors in render)
  - Logs the error via `console.error` for dev-mode triage
  - Renders a recovery Card with reload + home buttons
  - Production observability hook is **intentionally omitted** — the
    audit's other P1 items are higher value than wiring Sentry

- The barrel `frontend/src/ui/index.ts` is the canonical import
  path: `import { StatusTag, MetricBand } from "../../ui"`. New
  components go in this file, never nested.

## Consequences

**Positive**

- 6 components, 20 tests, 100% of the audit's UI duplication
  concerns addressed
- `StatusTag` migration: 10 pages already migrated in stage 2.4
  (`finance/JournalEntryList`, `system/ApprovalList`, `reports/ReportProcurement`,
  `reports/ReportInventory`, `procurement/ProcurementDashboard`,
  `customers/CustomerAIWorkbench`, `sales/salesUi.SalesStatusTag`
  (10+ downstream sales pages), `sales/OpportunityList`,
  `tickets/TicketList`, `warehouse/InventoryLedger`)
- The `humanize` bug fix prevents a class of data-correctness
  issues (trend values, numeric statuses, currency labels)
- 8 unused `Tag` imports removed from migrated pages

**Negative / Known Limitations**

- Migration is optional, not enforced. 50+ pages still don't use
  the library. Each new page should use it, but there's no linter
  rule to enforce.
- `ErrorBoundary` is not applied to any existing page; each new
  page should wrap itself. A future commit could mass-apply it.
- The library is not a design system: no dark mode, no design
  tokens, no Storybook. Adding those is a v7 task.

## Follow-up

- v6.1: mass-apply `ErrorBoundary` to existing pages in a sweep
  commit (low-risk, mechanical wrap)
- v6.2: extract the inline `style={...}` constants in the
  components into a shared `tokens.ts` so colors / spacing
  can be themed (foundation for dark mode)
- v6.3: add a 7th component when a 2nd page needs it
  (likely `ConfirmDeleteButton` or `FormSection`)
- v7 (post v6): real design system with Storybook, design tokens,
  dark mode — only if multi-app or multi-team sharing becomes a
  real need
