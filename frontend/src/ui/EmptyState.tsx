/** EmptyState — consistent "no data" placeholder.

Replaces the ad-hoc antd `<Empty />` invocations with optional call-
to-action button. Some pages want a more tailored empty state
(illustrative copy, action button) and currently inline 10+ lines
of styling each time.

Usage:
  <EmptyState
    description="暂无报价单"
    actionLabel="创建第一份报价"
    onAction={() => navigate("/quotations/new")}
  />
*/

import { Empty, Button } from "antd";
import { InboxOutlined } from "@ant-design/icons";

export interface EmptyStateProps {
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  /** Smaller variant for inline table cells. */
  compact?: boolean;
}

export function EmptyState({
  description = "暂无数据",
  actionLabel,
  onAction,
  compact = false,
}: EmptyStateProps) {
  return (
    <div
      className={`erp-empty-state${compact ? " erp-empty-state-compact" : ""}`}
      style={compact ? compactStyle : rootStyle}
    >
      <Empty
        image={compact ? Empty.PRESENTED_IMAGE_SIMPLE : <InboxOutlined style={iconStyle} />}
        description={description}
        style={{ margin: 0 }}
      >
        {actionLabel && onAction && (
          <Button type="primary" onClick={onAction}>
            {actionLabel}
          </Button>
        )}
      </Empty>
    </div>
  );
}

const rootStyle = { padding: "48px 0" } as const;
const compactStyle = { padding: "24px 0" } as const;
const iconStyle = { fontSize: 48, color: "var(--ant-color-text-tertiary)" } as const;
