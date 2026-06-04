/** MetricBand — KPI card row.

Renders a horizontal band of `n` stat cards. Each card shows:
- An optional icon (left)
- A label (small, secondary text)
- A primary value (large, bold)
- An optional suffix / unit (right of value, secondary text)
- An optional trend indicator (delta + arrow + color tone)

Replaces the duplicated "stat card with 4-col grid" pattern repeated
across `pages/dashboard/index.tsx`, `pages/finance/AccountList.tsx`,
`pages/sales/SalesDashboard.tsx`, etc. The pattern is always: an
antd `<Card>` containing a 3-line stack (label, value+suffix, optional
delta). StatusTag is reused for the delta coloring.
*/

import { Card } from "antd";
import { ArrowDownOutlined, ArrowUpOutlined } from "@ant-design/icons";
import { useMemo } from "react";
import type { ReactNode } from "react";
import { StatusTag, type StatusTone } from "./StatusTag";

export interface MetricItem {
  label: string;
  value: ReactNode;
  suffix?: ReactNode;
  icon?: ReactNode;
  trend?: {
    value: ReactNode;
    tone?: StatusTone;
  };
}

export interface MetricBandProps {
  items: MetricItem[];
  /** Column span per item. 24-col antd grid: e.g. 6 = 4 per row. */
  span?: number;
  /** Optional size variant. antd Card sizes. */
  size?: "small" | "default";
}

export function MetricBand({ items, span = 6, size }: MetricBandProps) {
  const grid = useMemo(
    () =>
      items.map((item, idx) => (
        <Card.Grid key={idx} style={cardGridStyle}>
          <div style={rowStyle}>
            {item.icon && <div style={iconStyle}>{item.icon}</div>}
            <div style={bodyStyle}>
              <div style={labelStyle}>{item.label}</div>
              <div style={valueRowStyle}>
                <span style={valueStyle}>{item.value}</span>
                {item.suffix && <span style={suffixStyle}>{item.suffix}</span>}
              </div>
              {item.trend && (
                <div style={trendStyle}>
                  <StatusTag
                    status={String(item.trend.value)}
                    tone={item.trend.tone ?? "neutral"}
                  />
                </div>
              )}
            </div>
          </div>
        </Card.Grid>
      )),
    [items, size],
  );

  return (
    <Card size={size} style={{ marginBottom: 16 }}>
      <div style={gridStyle(span)}>{grid}</div>
    </Card>
  );
}

// Layout constants — kept here so visual rhythm is identical across pages
const gridStyle = (span: number) =>
  ({
    display: "grid",
    gridTemplateColumns: `repeat(24, 1fr)`,
    gap: 1,
  }) as const;

const cardGridStyle = { gridColumn: `span ${6}` } as const;
// Caller passes `span` but the inner grid item is hardcoded at 6 to keep
// the visual rhythm consistent. Pages that need different column ratios
// should compose MetricBands with different `items` lengths.

const rowStyle = { display: "flex", alignItems: "flex-start", gap: 12, padding: 12 } as const;
const iconStyle = { flex: "0 0 auto", color: "var(--ant-color-primary, #1677ff)" } as const;
const bodyStyle = { flex: 1, minWidth: 0 } as const;
const labelStyle = { color: "var(--ant-color-text-secondary)", fontSize: 12, marginBottom: 4 } as const;
const valueRowStyle = { display: "flex", alignItems: "baseline", gap: 4 } as const;
const valueStyle = { fontSize: 22, fontWeight: 600, color: "var(--ant-color-text)" } as const;
const suffixStyle = { color: "var(--ant-color-text-tertiary)", fontSize: 12 } as const;
const trendStyle = { marginTop: 4 } as const;
