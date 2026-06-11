import { BarChartOutlined, HeartOutlined, PieChartOutlined, PlusOutlined, RobotOutlined, TeamOutlined } from "@ant-design/icons";
import { Button, Segmented, Space, Typography } from "antd";
import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";

type CustomerModuleNavKey = "list" | "stats" | "segments" | "intelligence" | "workbench";

interface CustomerModuleShellProps {
  title: string;
  subtitle?: string;
  extra?: ReactNode;
  children: ReactNode;
}

const NAV_ITEMS: { key: CustomerModuleNavKey; label: string; path: string; icon: ReactNode }[] = [
  { key: "list", label: "客户列表", path: "/customers", icon: <TeamOutlined /> },
  { key: "stats", label: "客户统计", path: "/customers/stats", icon: <BarChartOutlined /> },
  { key: "segments", label: "客户分群", path: "/customers/segments", icon: <PieChartOutlined /> },
  { key: "intelligence", label: "智能分析", path: "/customers/intelligence", icon: <HeartOutlined /> },
  { key: "workbench", label: "AI工作队列", path: "/customers/workbench", icon: <RobotOutlined /> },
];

const PATH_TO_KEY: Array<{ prefix: string; key: CustomerModuleNavKey }> = [
  { prefix: "/customers/workbench", key: "workbench" },
  { prefix: "/customers/intelligence", key: "intelligence" },
  { prefix: "/customers/segments", key: "segments" },
  { prefix: "/customers/stats", key: "stats" },
  { prefix: "/customers", key: "list" },
];

const TITLE_ICON: Record<CustomerModuleNavKey, ReactNode> = {
  list: <TeamOutlined />,
  stats: <BarChartOutlined />,
  segments: <PieChartOutlined />,
  intelligence: <HeartOutlined />,
  workbench: <RobotOutlined />,
};

function resolveNavKey(pathname: string): CustomerModuleNavKey {
  for (const item of PATH_TO_KEY) {
    if (pathname === item.prefix || pathname.startsWith(`${item.prefix}/`)) {
      return item.key;
    }
  }
  return "list";
}

export default function CustomerModuleShell({ title, subtitle, extra, children }: CustomerModuleShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const selectedKey = resolveNavKey(location.pathname);
  const selectedNavItem = NAV_ITEMS.find((item) => item.key === selectedKey) || NAV_ITEMS[0];
  const isCreatePage = location.pathname === "/customers/new";

  return (
    <div className="customer-module-shell">

      <div className="customer-module-header">
        <div className="customer-module-heading">
          <div className="customer-module-title-wrap">
            <span className="customer-module-title-icon">{TITLE_ICON[selectedKey]}</span>
            <div>
              <span className="customer-module-eyebrow">客户管理 / {selectedNavItem.label}</span>
              <Typography.Title level={4} style={{ margin: 0, lineHeight: 1.25 }}>
                {title}
              </Typography.Title>
              {subtitle && (
                <Typography.Text type="secondary">{subtitle}</Typography.Text>
              )}
            </div>
          </div>
          <div className="customer-module-actions">
            <Space wrap size={8}>
              {extra}
              {selectedKey !== "intelligence" && (
                <Button icon={<HeartOutlined />} onClick={() => navigate("/customers/intelligence")}>智能分析</Button>
              )}
              {selectedKey !== "workbench" && (
                <Button icon={<RobotOutlined />} onClick={() => navigate("/customers/workbench")}>AI工作队列</Button>
              )}
              {!isCreatePage && (
                <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/customers/new")}>新建客户</Button>
              )}
            </Space>
          </div>
        </div>
        <div className="customer-module-nav">
          <Segmented
            value={selectedKey}
            options={NAV_ITEMS.map((item) => ({
              label: (
                <span className="customer-module-nav-item">
                  {item.icon}
                  <span>{item.label}</span>
                </span>
              ),
              value: item.key,
            }))}
            onChange={(value) => {
              const next = NAV_ITEMS.find((item) => item.key === value);
              if (next) navigate(next.path);
            }}
          />
        </div>
      </div>
      {children}
    </div>
  );
}
