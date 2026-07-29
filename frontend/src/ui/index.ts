/** Shared UI component library — the canonical home for reusable primitives.

Before this, every page inlined its own copy of:
- `<Tag color={STATUS_COLORS[v]}>{STATUS_LABELS[v] || v}</Tag>`
- `<Card.Grid>` KPI card rows
- `<Input.Search>` + reset button
- `<Empty>` with action button
- "back button + title + actions" page header
- Per-page error containment (none — any error white-screened)

Each component here is the agreed-upon answer; pages should import
from `./ui` rather than re-implementing. Adding new variants should
mean extending one of these files, not copy-pasting across pages.

Components:
- StatusTag      : antd Tag with semantic tone (success/warning/danger/...)
- MetricBand     : KPI card row (replaces dashboard-style grid)
- SearchBar      : filter input + reset button
- PageHeader     : back button + title + actions
- EmptyState     : empty placeholder with optional CTA
- ErrorBoundary  : React error boundary for page-level containment

Each file is <100 lines so adding a new variant stays tractable.
*/

export { StatusTag } from "./StatusTag";
export type { StatusTagProps, StatusTone } from "./StatusTag";
export { buildIndustryRanking, IndustryRanking } from "./IndustryRanking";
export type { IndustryRankingItem, IndustryRankingProps } from "./IndustryRanking";

export { MetricBand } from "./MetricBand";
export type { MetricBandProps, MetricItem } from "./MetricBand";

export { SearchBar } from "./SearchBar";
export type { SearchBarProps } from "./SearchBar";

export { PageHeader } from "./PageHeader";
export type { PageHeaderProps } from "./PageHeader";

export { EmptyState } from "./EmptyState";
export type { EmptyStateProps } from "./EmptyState";

export { ErrorBoundary } from "./ErrorBoundary";

export { OfflineBanner } from "./OfflineBanner";

export { isChunkLoadError, isOffline } from "./chunkError";

export { FlexBox } from "./FlexBox";

export { useColumnResize } from "./useColumnResize";

export { ModuleShell } from "./ModuleShell";
export type { ModuleShellProps, ModuleNavItem } from "./ModuleShell";

export { UomSelect } from "./UomSelect";
