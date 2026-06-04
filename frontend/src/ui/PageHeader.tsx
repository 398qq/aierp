/** PageHeader — consistent page title block.

Combines:
- Page title (h3, bold)
- Optional description / subtitle (secondary text)
- Optional back button
- Optional action buttons (right-aligned)

Replaces the ad-hoc `<div><h3>{title}</h3>{description}</div>` plus
the `<Button icon={<ArrowLeftOutlined />}>返回</Button>` patterns
across 30+ pages.
*/

import { Button, Space } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  onBack?: () => void;
  backLabel?: string;
  actions?: ReactNode;
}

export function PageHeader({
  title,
  description,
  onBack,
  backLabel = "返回",
  actions,
}: PageHeaderProps) {
  return (
    <div style={rootStyle}>
      <div style={leftStyle}>
        {onBack && (
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={onBack}
            style={backButtonStyle}
          >
            {backLabel}
          </Button>
        )}
        <div>
          <div style={titleStyle}>{title}</div>
          {description && <div style={descStyle}>{description}</div>}
        </div>
      </div>
      {actions && (
        <Space style={actionsStyle} size="small" wrap>
          {actions}
        </Space>
      )}
    </div>
  );
}

const rootStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: 16,
  gap: 16,
} as const;
const leftStyle = { display: "flex", gap: 12, alignItems: "center" } as const;
const backButtonStyle = { marginRight: 4, paddingLeft: 4 } as const;
const titleStyle = { fontSize: 20, fontWeight: 600, color: "var(--ant-color-text)" } as const;
const descStyle = {
  color: "var(--ant-color-text-secondary)",
  fontSize: 13,
  marginTop: 4,
} as const;
const actionsStyle = { flex: "0 0 auto" } as const;
