/** StatusTag — antd `<Tag>` with semantic color presets.

Replaces the ad-hoc `<Tag color={STATUS_COLORS[v]}>` pattern repeated
across 14+ pages. Centralizes the color vocabulary so a new status
state (e.g. `"on_hold"`) doesn't require updating every list page.

Two usage modes:

1. **Semantic color** (recommended): pass `tone="success" | "warning" |
   "danger" | "info" | "neutral"`. Use this when the status is a known
   lifecycle state with a standard meaning.

2. **Raw antd color** (escape hatch): pass `color="orange"`. Use this
   for one-off visual variety (e.g. distinguishing a custom category
   enum). Prefers `tone` for new code.

The optional `label` overrides the displayed text; if omitted the
`status` value is shown verbatim (lowercased, underscored → spaced).
*/

import { Tag } from "antd";
import type { ReactNode } from "react";

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral" | "processing";

const TONE_TO_COLOR: Record<StatusTone, string> = {
  success: "green",
  warning: "orange",
  danger: "red",
  info: "blue",
  neutral: "default",
  processing: "gold",
};

// Only replace separators between word chars; preserves leading "−" /
// "+" / "$" / etc. so trend values like "-2%" don't get corrupted.
const HUMANIZE_RE = /(?<=\w)[_-]+(?=\w)/g;
const humanize = (s: string) =>
  s.replace(HUMANIZE_RE, " ").replace(/^\w/, (c) => c.toUpperCase());

export interface StatusTagProps {
  status: string;
  tone?: StatusTone;
  color?: string;
  label?: ReactNode;
}

export function StatusTag({ status, tone, color, label }: StatusTagProps) {
  const resolved = color ?? (tone ? TONE_TO_COLOR[tone] : "default");
  const text = label ?? humanize(status);
  return <Tag color={resolved}>{text}</Tag>;
}
