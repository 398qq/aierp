import { AppstoreOutlined, BarChartOutlined, DownOutlined, FileTextOutlined, HeartOutlined, PieChartOutlined, PlusOutlined, RobotOutlined, TeamOutlined } from "@ant-design/icons";
import { Button, Dropdown, Segmented, Space, Typography } from "antd";
import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import "./customer-module.css";

type CustomerModuleNavKey = "home" | "list" | "followups" | "analytics";

interface CustomerModuleShellProps {
  title: string;
  subtitle?: string;
  extra?: ReactNode;
  children: ReactNode;
}

const NAV_ITEMS: { key: CustomerModuleNavKey; label: string; path: string; icon: ReactNode }[] = [
  { key: "home", label: "工作台", path: "/customers/stats", icon: <AppstoreOutlined /> },
  { key: "list", label: "客户台账", path: "/customers", icon: <TeamOutlined /> },
  { key: "followups", label: "跟进任务", path: "/customers/follow-ups", icon: <FileTextOutlined /> },
  { key: "analytics", label: "分析中心", path: "/customers/intelligence", icon: <BarChartOutlined /> },
];

const PATH_TO_KEY: Array<{ prefix: string; key: CustomerModuleNavKey }> = [
  { prefix: "/customers/workbench", key: "analytics" },
  { prefix: "/customers/intelligence", key: "analytics" },
  { prefix: "/customers/segments", key: "analytics" },
  { prefix: "/customers/follow-ups", key: "followups" },
  { prefix: "/customers/stats", key: "home" },
  { prefix: "/customers", key: "list" },
];

const TITLE_ICON: Record<CustomerModuleNavKey, ReactNode> = {
  home: <AppstoreOutlined />,
  list: <TeamOutlined />,
  followups: <FileTextOutlined />,
  analytics: <BarChartOutlined />,
};

const ANALYTICS_ITEMS = [
  { key: "/customers/intelligence", label: "智能分析", icon: <HeartOutlined /> },
  { key: "/customers/segments", label: "客户分群", icon: <PieChartOutlined /> },
  { key: "/customers/workbench", label: "AI 工作队列", icon: <RobotOutlined /> },
];

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
  const roles = useAuthStore((state) => state.roles);
  const selectedKey = resolveNavKey(location.pathname);
  const selectedNavItem = NAV_ITEMS.find((item) => item.key === selectedKey) || NAV_ITEMS[0];
  const isCreatePage = location.pathname === "/customers/new";
  const roleLabel = roles.some((role) => /admin/i.test(role))
    ? "管理员视图"
    : roles.some((role) => /finance/i.test(role))
      ? "财务视图"
      : roles.some((role) => /manager|supervisor/i.test(role))
        ? "主管视图"
        : "业务视图";

  return (
    <div className="customer-module-shell">

      <div className="customer-module-header">
        <div className="customer-module-heading">
          <div className="customer-module-title-wrap">
            <span className="customer-module-title-icon">{TITLE_ICON[selectedKey]}</span>
            <div>
              <span className="customer-module-eyebrow">客户管理 · {roleLabel} / {selectedNavItem.label}</span>
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
          {selectedKey === "analytics" && (
            <Dropdown
              menu={{ items: ANALYTICS_ITEMS, selectedKeys: [location.pathname], onClick: ({ key }) => navigate(key) }}
            >
              <Button className="customer-analysis-menu">
                {ANALYTICS_ITEMS.find((item) => location.pathname.startsWith(item.key))?.label || "分析工具"}
                <DownOutlined />
              </Button>
            </Dropdown>
          )}
        </div>
      </div>
      {children}
    </div>
  );
}
