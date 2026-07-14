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
    <div className="erp-page-header">
      <div className="erp-page-header-main">
        {onBack && (
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={onBack}
            className="erp-page-header-back"
          >
            {backLabel}
          </Button>
        )}
        <div>
          <div className="erp-page-header-title">{title}</div>
          {description && <div className="erp-page-header-description">{description}</div>}
        </div>
      </div>
      {actions && (
        <Space className="erp-page-header-actions" size="small" wrap>
          {actions}
        </Space>
      )}
    </div>
  );
}
