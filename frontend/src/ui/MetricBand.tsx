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
        <div key={idx} className="erp-metric-item">
          <div className="erp-metric-row">
            {item.icon && <div className="erp-metric-icon">{item.icon}</div>}
            <div className="erp-metric-body">
              <div className="erp-metric-label">{item.label}</div>
              <div className="erp-metric-value-row">
                <span className="erp-metric-value">{item.value}</span>
                {item.suffix && <span className="erp-metric-suffix">{item.suffix}</span>}
              </div>
              {item.trend && (
                <div className="erp-metric-trend">
                  <StatusTag
                    status={String(item.trend.value)}
                    tone={item.trend.tone ?? "neutral"}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )),
    [items],
  );

  return (
    <Card size={size} className="erp-metric-band">
      <div className="erp-metric-grid" style={{ gridTemplateColumns: `repeat(${Math.max(1, Math.floor(24 / span))}, minmax(0, 1fr))` }}>{grid}</div>
    </Card>
  );
}
