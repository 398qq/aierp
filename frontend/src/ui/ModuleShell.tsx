import { Segmented, Space, Typography } from "antd";
import type { ReactNode } from "react";
import { useNavigate } from "react-router";

export interface ModuleNavItem {
  key: string;
  label: string;
  path: string;
  icon?: ReactNode;
}

export interface ModuleShellProps {
  title: ReactNode;
  subtitle?: ReactNode;
  eyebrow?: ReactNode;
  activeKey?: string;
  navItems?: ModuleNavItem[];
  actions?: ReactNode;
  children: ReactNode;
}

export function ModuleShell({ title, subtitle, eyebrow, activeKey, navItems = [], actions, children }: ModuleShellProps) {
  const navigate = useNavigate();
  return (
    <section className="erp-module-shell">
      <header className="erp-module-header">
        <div className="erp-module-heading">
          {eyebrow && <div className="erp-module-eyebrow">{eyebrow}</div>}
          <Typography.Title level={4}>{title}</Typography.Title>
          {subtitle && <Typography.Text type="secondary">{subtitle}</Typography.Text>}
        </div>
        {actions && <Space wrap size={8}>{actions}</Space>}
      </header>
      {navItems.length > 0 && (
        <div className="erp-module-nav">
          <Segmented
            value={activeKey}
            options={navItems.map((item) => ({ value: item.key, label: <span>{item.icon}{item.icon && " "}{item.label}</span> }))}
            onChange={(key) => {
              const next = navItems.find((item) => item.key === key);
              if (next) navigate(next.path);
            }}
          />
        </div>
      )}
      <div className="erp-module-content">{children}</div>
    </section>
  );
}
