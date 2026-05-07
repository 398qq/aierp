import { useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, Button, Typography, theme, Badge, Drawer, Input, Card, Tag, Spin, Space, List } from "antd";
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
  BellOutlined,
  FileProtectOutlined,
  AimOutlined,
  TagOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../store/auth";
import { getUnreadCount, naturalLanguageQuery } from "../api";
import type { NLPQueryResult } from "../types";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const { token } = theme.useToken();

  // NLP query drawer state
  const [nlpDrawerOpen, setNlpDrawerOpen] = useState(false);
  const [nlpQuery, setNlpQuery] = useState("");
  const [nlpLoading, setNlpLoading] = useState(false);
  const [nlpResult, setNlpResult] = useState<NLPQueryResult | null>(null);

  const handleNlpSubmit = async () => {
    if (!nlpQuery.trim()) return;
    setNlpLoading(true);
    setNlpResult(null);
    try {
      const resp = await naturalLanguageQuery(nlpQuery);
      if (resp.data.code === 0) {
        setNlpResult(resp.data.data);
      }
    } catch {
      // ignore
    } finally {
      setNlpLoading(false);
    }
  };

  const menuKeys = ["/", "/customers", "/sales", "/products", "/brands", "/suppliers", "/inventory", "/notifications", "/ai/chat", "/settings"];
  const selectedKey = menuKeys
    .filter((k) => location.pathname === k || (k !== "/" && location.pathname.startsWith(k + "/")))
    .sort((a, b) => b.length - a.length)[0] || location.pathname;

  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const resp = await getUnreadCount();
        setUnreadCount(resp.data.data.count || 0);
      } catch { /* ignore */ }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 60000);
    return () => clearInterval(interval);
  }, []);

  const menuItems = [
    { key: "/", icon: <DashboardOutlined />, label: "仪表板" },
    { key: "/customers", icon: <TeamOutlined />, label: "客户管理" },
    {
      key: "/products", icon: <ShopOutlined />, label: "产品管理",
      children: [
        { key: "/products", icon: <ShopOutlined />, label: "产品列表" },
        { key: "/brands", icon: <TagOutlined />, label: "品牌管理" },
        { key: "/suppliers", icon: <TeamOutlined />, label: "供应商" },
        { key: "/inventory", icon: <StockOutlined />, label: "库存管理" },
      ],
    },
    {
      key: "/sales", icon: <DollarOutlined />, label: "销售管理",
      children: [
        { key: "/sales/opportunities", icon: <FileTextOutlined />, label: "机会列表" },
        { key: "/sales/pipeline", icon: <DashboardOutlined />, label: "Pipeline看板" },
        { key: "/sales/funnel", icon: <FilterOutlined />, label: "销售漏斗" },
        { key: "/sales/stats", icon: <BarChartOutlined />, label: "销售统计" },
        { key: "/sales/dashboard", icon: <DashboardOutlined />, label: "数据看板" },
        { key: "/sales/quotations", icon: <SnippetsOutlined />, label: "报价单" },
        { key: "/sales/orders", icon: <DollarOutlined />, label: "销售订单" },
        { key: "/sales/delivery-notes", icon: <CarOutlined />, label: "送货单" },
        { key: "/sales/payments", icon: <DollarOutlined />, label: "回款管理" },
        { key: "/sales/invoices", icon: <FileProtectOutlined />, label: "发票管理" },
        { key: "/sales/targets", icon: <AimOutlined />, label: "销售目标" },
        { key: "/sales/contracts", icon: <FileTextOutlined />, label: "合同管理" },
      ],
    },
    { key: "/notifications", icon: <BellOutlined />, label: "消息提醒" },
    { key: "/ai/chat", icon: <RobotOutlined />, label: "AI 助手" },
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
        <Header style={{ background: token.colorBgContainer, padding: "0 24px", display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 16 }}>
          <Badge count={unreadCount} size="small">
            <Button type="text" icon={<BellOutlined />} onClick={() => navigate("/notifications")} />
          </Badge>
          <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>
            退出
          </Button>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: token.colorBgContainer, borderRadius: 8, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
      {/* Floating AI Q&A Button */}
      <Button
        type="primary"
        shape="circle"
        size="large"
        icon={<RobotOutlined />}
        onClick={() => setNlpDrawerOpen(true)}
        style={{
          position: "fixed",
          bottom: 24,
          right: 24,
          zIndex: 1000,
          boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        }}
      />
      <Drawer
        title="AI 问答"
        open={nlpDrawerOpen}
        onClose={() => setNlpDrawerOpen(false)}
        width={480}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="输入您的问题，例如：本月销售额最高的客户是谁？"
              value={nlpQuery}
              onChange={(e) => setNlpQuery(e.target.value)}
              onPressEnter={handleNlpSubmit}
            />
            <Button
              type="primary"
              loading={nlpLoading}
              onClick={handleNlpSubmit}
            >
              发送
            </Button>
          </Space.Compact>
          {nlpLoading && (
            <div style={{ textAlign: "center", padding: 24 }}>
              <Spin tip="AI 正在分析..." />
            </div>
          )}
          {nlpResult && (
            <>
              <Card
                size="small"
                title="回答"
                extra={
                  <Tag color={nlpResult.confidence > 0.7 ? "green" : "orange"}>
                    置信度: {(nlpResult.confidence * 100).toFixed(0)}%
                  </Tag>
                }
              >
                <Typography.Paragraph style={{ marginBottom: 0 }}>
                  {nlpResult.answer}
                </Typography.Paragraph>
              </Card>
              {nlpResult.data_summary && (
                <Card size="small" title="数据摘要">
                  <Typography.Paragraph style={{ marginBottom: 0 }}>
                    {nlpResult.data_summary}
                  </Typography.Paragraph>
                </Card>
              )}
              {nlpResult.related_entities && nlpResult.related_entities.length > 0 && (
                <Card size="small" title="相关实体">
                  <Space wrap>
                    {nlpResult.related_entities.map((entity, idx) => {
                      const routeMap: Record<string, string> = {
                        customer: "/customers",
                        product: "/products",
                        order: "/sales/orders",
                        quotation: "/sales/quotations",
                        opportunity: "/sales/opportunities",
                        contract: "/sales/contracts",
                        invoice: "/sales/invoices",
                      };
                      const route = routeMap[entity.type];
                      return (
                        <Tag
                          key={idx}
                          color="blue"
                          style={{ cursor: route ? "pointer" : "default" }}
                          onClick={() => {
                            if (route) {
                              setNlpDrawerOpen(false);
                              navigate(`${route}/${entity.id}`);
                            }
                          }}
                        >
                          {entity.type}: {entity.name}
                        </Tag>
                      );
                    })}
                  </Space>
                </Card>
              )}
              {nlpResult.actions && nlpResult.actions.length > 0 && (
                <Card size="small" title="建议操作">
                  <List
                    size="small"
                    dataSource={nlpResult.actions}
                    renderItem={(action, idx) => (
                      <List.Item>
                        <Typography.Text strong>{action.action}</Typography.Text>
                        {" "}
                        <Tag color="orange">{action.urgency}</Tag>
                      </List.Item>
                    )}
                  />
                </Card>
              )}
              {nlpResult.suggested_followups && nlpResult.suggested_followups.length > 0 && (
                <Card size="small" title="追问建议">
                  <Space wrap>
                    {nlpResult.suggested_followups.map((q, idx) => (
                      <Button
                        key={idx}
                        size="small"
                        onClick={() => setNlpQuery(q)}
                      >
                        {q}
                      </Button>
                    ))}
                  </Space>
                </Card>
              )}
            </>
          )}
        </Space>
      </Drawer>
    </Layout>
  );
}
