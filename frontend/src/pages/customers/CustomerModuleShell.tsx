import { BarChartOutlined, PieChartOutlined, PlusOutlined, TeamOutlined } from "@ant-design/icons";
import { Button, Card, Segmented, Space, Typography } from "antd";
import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";

type CustomerModuleNavKey = "list" | "stats" | "segments";

interface CustomerModuleShellProps {
  title: string;
  subtitle?: string;
  extra?: ReactNode;
  children: ReactNode;
}

const NAV_ITEMS: { key: CustomerModuleNavKey; label: string; path: string }[] = [
  { key: "list", label: "客户列表", path: "/customers" },
  { key: "stats", label: "客户统计", path: "/customers/stats" },
  { key: "segments", label: "客户分群", path: "/customers/segments" },
];

const PATH_TO_KEY: Array<{ prefix: string; key: CustomerModuleNavKey }> = [
  { prefix: "/customers/segments", key: "segments" },
  { prefix: "/customers/stats", key: "stats" },
  { prefix: "/customers", key: "list" },
];

const TITLE_ICON: Record<CustomerModuleNavKey, ReactNode> = {
  list: <TeamOutlined style={{ marginRight: 8 }} />,
  stats: <BarChartOutlined style={{ marginRight: 8 }} />,
  segments: <PieChartOutlined style={{ marginRight: 8 }} />,
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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Card size="small">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {TITLE_ICON[selectedKey]}
              {title}
            </Typography.Title>
            {subtitle && (
              <Typography.Text type="secondary">{subtitle}</Typography.Text>
            )}
          </div>
          <Space wrap>
            {extra}
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/customers/new")}>新建客户</Button>
          </Space>
        </div>
        <Segmented
          style={{ marginTop: 12, maxWidth: 760 }}
          value={selectedKey}
          options={NAV_ITEMS.map((item) => ({ label: item.label, value: item.key }))}
          onChange={(value) => {
            const next = NAV_ITEMS.find((item) => item.key === value);
            if (next) navigate(next.path);
          }}
        />
      </Card>
      {children}
    </div>
  );
}
