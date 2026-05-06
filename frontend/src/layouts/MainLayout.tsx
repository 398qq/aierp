import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, Button, Typography, theme } from "antd";
import {
  DashboardOutlined,
  TeamOutlined,
  ShopOutlined,
  StockOutlined,
  FileTextOutlined,
  DollarOutlined,
  SettingOutlined,
  LogoutOutlined,
  RobotOutlined,
  CarOutlined,
  SnippetsOutlined,
  FilterOutlined,
  BarChartOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../store/auth";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const { token } = theme.useToken();

  const menuKeys = ["/", "/customers", "/sales", "/products", "/inventory", "/ai-chat", "/settings"];
  const selectedKey = menuKeys
    .filter((k) => location.pathname === k || (k !== "/" && location.pathname.startsWith(k + "/")))
    .sort((a, b) => b.length - a.length)[0] || location.pathname;

  const menuItems = [
    { key: "/", icon: <DashboardOutlined />, label: "仪表板" },
    { key: "/customers", icon: <TeamOutlined />, label: "客户管理" },
    { key: "/products", icon: <ShopOutlined />, label: "产品管理" },
    { key: "/inventory", icon: <StockOutlined />, label: "库存管理" },
    {
      key: "/sales", icon: <DollarOutlined />, label: "销售管理",
      children: [
        { key: "/sales/opportunities", icon: <FileTextOutlined />, label: "销售Pipeline" },
        { key: "/sales/funnel", icon: <FilterOutlined />, label: "销售漏斗" },
        { key: "/sales/stats", icon: <BarChartOutlined />, label: "销售统计" },
        { key: "/sales/quotations", icon: <SnippetsOutlined />, label: "报价单" },
        { key: "/sales/orders", icon: <DollarOutlined />, label: "销售订单" },
        { key: "/sales/delivery-notes", icon: <CarOutlined />, label: "送货单" },
      ],
    },
    { key: "/ai-chat", icon: <RobotOutlined />, label: "AI 助手" },
    { key: "/settings", icon: <SettingOutlined />, label: "设置" },
  ];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} theme="dark">
        <div style={{ padding: 16, textAlign: "center" }}>
          <Text strong style={{ color: token.colorWhite, fontSize: collapsed ? 14 : 18 }}>
            {collapsed ? "AI" : "AIERP"}
          </Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: token.colorBgContainer, padding: "0 24px", display: "flex", justifyContent: "flex-end", alignItems: "center" }}>
          <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>
            退出
          </Button>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: token.colorBgContainer, borderRadius: 8, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
