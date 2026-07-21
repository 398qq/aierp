import { useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Layout,
  Menu,
  Breadcrumb,
  Button,
  Typography,
  Badge,
  Drawer,
  Input,
  Avatar,
  Tooltip,
  Card,
  Tag,
  Spin,
  Space,
  List,
} from "antd";
import type { MenuProps } from "antd";
import {
  DashboardOutlined,
  TeamOutlined,
  ShopOutlined,
  StockOutlined,
  SettingOutlined,
  LogoutOutlined,
  PieChartOutlined,
  RobotOutlined,
  BellOutlined,
  TagOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  ShoppingCartOutlined,
  CarOutlined,
  FileDoneOutlined,
  DollarOutlined,
  ProfileOutlined,
  AimOutlined,
  WarningOutlined,
  SwapOutlined,
  UploadOutlined,
  IssuesCloseOutlined,
  HeartOutlined,
  TrophyOutlined,
  MenuOutlined,
  SearchOutlined,
  QuestionCircleOutlined,
  FullscreenOutlined,
  UserOutlined,
  HomeOutlined,
  MoreOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../store/auth";
import { getUnreadCount, naturalLanguageQuery } from "../api";
import type { NLPQueryResult } from "../types";
import "../styles/app-shell.css";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

function useIsMobile() {
  const [m, setM] = useState(window.innerWidth < 768);
  useEffect(() => {
    const h = () => setM(window.innerWidth < 768);
    window.addEventListener("resize", h);
    return () => window.removeEventListener("resize", h);
  }, []);
  return m;
}

type MenuEntry = { key: string; label: string };

function flattenMenuItems(items: MenuProps["items"]): MenuEntry[] {
  const result: MenuEntry[] = [];
  for (const item of items || []) {
    if (!item || typeof item !== "object" || !("key" in item)) continue;
    if ("label" in item && typeof item.key === "string" && item.key.startsWith("/") && typeof item.label === "string") {
      result.push({ key: item.key, label: item.label });
    }
    if ("children" in item && Array.isArray(item.children)) {
      result.push(...flattenMenuItems(item.children as MenuProps["items"]));
    }
  }
  return result;
}

export default function MainLayout() {
  const isMobile = useIsMobile();
  const [collapsed, setCollapsed] = useState(isMobile);
  const [unreadCount, setUnreadCount] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const username = useAuthStore((s) => s.username);
  const roles = useAuthStore((s) => s.roles);

  // NLP query drawer state
  const [nlpDrawerOpen, setNlpDrawerOpen] = useState(false);
  const [nlpQuery, setNlpQuery] = useState("");
  const [nlpLoading, setNlpLoading] = useState(false);
  const [nlpResult, setNlpResult] = useState<NLPQueryResult | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const resp = await getUnreadCount();
        setUnreadCount(resp.data.data.count || 0);
      } catch {
        /* ignore */
      }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 60000);
    return () => clearInterval(interval);
  }, []);

  const menuItems: MenuProps["items"] = [
    {
      key: "_domain_overview",
      icon: <DashboardOutlined />,
      label: "经营总览",
      children: [
        { key: "/", icon: <DashboardOutlined />, label: "经营总览" },
        { key: "/dashboard/global360", icon: <PieChartOutlined />, label: "全局360" },
        { key: "/dashboard/watchtower", icon: <WarningOutlined />, label: "全局监控" },
      ],
    },
    {
      key: "_domain_sales",
      icon: <ThunderboltOutlined />,
      label: "客户与销售",
      children: [
        { key: "/customers/stats", icon: <DashboardOutlined />, label: "客户工作台" },
        { key: "/customers", icon: <TeamOutlined />, label: "客户台账" },
        { key: "/customers/follow-ups", icon: <FileTextOutlined />, label: "跟进任务" },
        { key: "/sales/dashboard", icon: <DashboardOutlined />, label: "销售工作台" },
        { key: "/sales/inquiry", icon: <RobotOutlined />, label: "询价回复" },
        { key: "/sales/opportunities", icon: <ThunderboltOutlined />, label: "商机管理" },
        { key: "/sales/quotations", icon: <FileTextOutlined />, label: "报价管理" },
        { key: "/sales/orders", icon: <ShoppingCartOutlined />, label: "销售订单" },
        { key: "/sales/contracts", icon: <ProfileOutlined />, label: "合同管理" },
        { key: "/sales/delivery-notes", icon: <CarOutlined />, label: "发货管理" },
        { key: "/sales/invoices", icon: <FileDoneOutlined />, label: "发票管理" },
        { key: "/sales/payments", icon: <DollarOutlined />, label: "回款管理" },
        { key: "/sales/targets", icon: <AimOutlined />, label: "销售目标" },
      ],
    },
    {
      key: "_domain_procurement",
      icon: <ShoppingCartOutlined />,
      label: "采购与供应链",
      children: [
        { key: "/procurement/dashboard", icon: <DashboardOutlined />, label: "采购工作台" },
        { key: "/sales/purchase-orders", icon: <ShoppingCartOutlined />, label: "采购订单" },
        { key: "/suppliers/stats", icon: <DashboardOutlined />, label: "供应商总览" },
        { key: "/suppliers", icon: <TeamOutlined />, label: "供应商台账" },
        { key: "/suppliers/compare", icon: <SwapOutlined />, label: "供应商对比" },
      ],
    },
    {
      key: "_domain_inventory",
      icon: <StockOutlined />,
      label: "产品与库存",
      children: [
        { key: "/products", icon: <ShopOutlined />, label: "产品台账" },
        { key: "/products/price-import", icon: <UploadOutlined />, label: "价格导入" },
        { key: "/brands", icon: <TagOutlined />, label: "品牌管理" },
        { key: "/inventory", icon: <StockOutlined />, label: "库存总览" },
        { key: "/warehouse/warehouses", icon: <ShopOutlined />, label: "仓库管理" },
        { key: "/warehouse/inventory-ledger", icon: <FileTextOutlined />, label: "库存台账" },
        { key: "/warehouse/inventory-batches", icon: <FileTextOutlined />, label: "批次与 COGS" },
      ],
    },
    {
      key: "_domain_finance",
      icon: <DollarOutlined />,
      label: "财务管理",
      children: [
        { key: "/finance/accounts", icon: <FileTextOutlined />, label: "会计科目" },
        { key: "/finance/journal-entries", icon: <ProfileOutlined />, label: "记账凭证" },
        { key: "/finance/pnl", icon: <PieChartOutlined />, label: "损益表" },
        { key: "/reports/ar", icon: <DollarOutlined />, label: "应收账款" },
        { key: "/reports/ap", icon: <DollarOutlined />, label: "应付账款" },
        { key: "/finance/commissions", icon: <TrophyOutlined />, label: "佣金管理" },
        { key: "/finance/commission-schemes", icon: <SettingOutlined />, label: "提成方案" },
      ],
    },
    {
      key: "_domain_analytics",
      icon: <PieChartOutlined />,
      label: "报表与分析",
      children: [
        { key: "/reports/sales", icon: <PieChartOutlined />, label: "销售报表" },
        { key: "/reports/inventory", icon: <StockOutlined />, label: "库存报表" },
        { key: "/reports/procurement", icon: <ShoppingCartOutlined />, label: "采购报表" },
        { key: "/customers/intelligence", icon: <HeartOutlined />, label: "客户分析" },
      ],
    },
    {
      key: "_domain_collaboration",
      icon: <IssuesCloseOutlined />,
      label: "协作与审批",
      children: [
        { key: "/system/approvals", icon: <FileDoneOutlined />, label: "审批管理" },
        { key: "/system/approval-rules", icon: <ProfileOutlined />, label: "审批规则" },
        { key: "/tickets", icon: <IssuesCloseOutlined />, label: "工单管理" },
        { key: "/notifications", icon: <BellOutlined />, label: "通知中心" },
        { key: "/ai/chat", icon: <RobotOutlined />, label: "AI 助手" },
      ],
    },
    {
      key: "_domain_system",
      icon: <SettingOutlined />,
      label: "系统治理",
      children: [
        { key: "/system/users", icon: <TeamOutlined />, label: "用户管理" },
        { key: "/system/roles", icon: <TeamOutlined />, label: "角色权限" },
        { key: "/system/uoms", icon: <ShopOutlined />, label: "计量单位" },
        { key: "/system/audit-logs", icon: <FileTextOutlined />, label: "审计日志" },
        { key: "/data/import-export", icon: <SwapOutlined />, label: "导入与导出" },
        { key: "/settings", icon: <SettingOutlined />, label: "系统设置" },
      ],
    },
  ];
  const searchableRoutes = flattenMenuItems(menuItems);
  const selectedKey =
    searchableRoutes
      .map((item) => item.key)
      .filter((key) => location.pathname === key || location.pathname.startsWith(`${key}/`))
      .sort((a, b) => b.length - a.length)[0] || location.pathname;
  const currentRoute = searchableRoutes.find((item) => item.key === selectedKey);
  const roleLabel = roles[0] || "业务用户";

  const navigateFromMenu = (key: string) => {
    navigate(key);
    setMobileMenuOpen(false);
  };

  const handleGlobalSearch = (value: string) => {
    const query = value.trim().toLowerCase();
    if (!query) return;
    const matched = searchableRoutes.find((item) =>
      item.label.toLowerCase().includes(query) || item.key.toLowerCase().includes(query),
    );
    if (matched) navigate(matched.key);
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <Layout className="erp-app-shell">
      {!isMobile && <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        breakpoint="lg"
        width={224}
        collapsedWidth={64}
        className="erp-app-sider"
      >
        <div className="erp-app-brand">
          <span className="erp-app-brand-mark">AI</span>
          {!collapsed && <Text strong className="erp-app-brand-name">AIERP</Text>}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigateFromMenu(key)}
          className="erp-app-menu"
        />
      </Sider>}
      <Layout>
        <Header className="erp-app-header">
          <div className="erp-app-header-context">
            {isMobile && <Button type="text" icon={<MenuOutlined />} onClick={() => setMobileMenuOpen(true)} aria-label="打开菜单" />}
            <Breadcrumb
              items={[
                { title: <HomeOutlined />, onClick: () => navigate("/") },
                ...(currentRoute ? [{ title: currentRoute.label }] : []),
              ]}
            />
          </div>
          <Input.Search
            className="erp-global-search"
            prefix={<SearchOutlined />}
            placeholder="搜索菜单或功能"
            allowClear
            onSearch={handleGlobalSearch}
          />
          <div className="erp-app-header-actions">
            <Tooltip title="AI 助手">
              <Button type="text" icon={<RobotOutlined />} onClick={() => setNlpDrawerOpen(true)} aria-label="AI 助手" />
            </Tooltip>
            <Tooltip title="帮助与设置">
              <Button type="text" icon={<QuestionCircleOutlined />} onClick={() => navigate("/settings")} aria-label="帮助与设置" />
            </Tooltip>
            {!isMobile && <Tooltip title="全屏">
              <Button type="text" icon={<FullscreenOutlined />} onClick={() => document.documentElement.requestFullscreen?.()} aria-label="全屏" />
            </Tooltip>}
          <Badge count={unreadCount} size="small">
            <Button
              type="text"
              icon={<BellOutlined />}
              onClick={() => navigate("/notifications")}
            />
          </Badge>
          <Tooltip title={`${username || "用户"} · ${roleLabel}`}>
            <Avatar size={30} icon={<UserOutlined />} />
          </Tooltip>
          {!isMobile && <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>退出</Button>}
          </div>
        </Header>
        <Content className="erp-app-content">
          <Outlet />
        </Content>
      </Layout>
      <Drawer title="全部功能" placement="left" open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} width="86%" className="erp-mobile-menu-drawer">
        <Menu mode="inline" selectedKeys={[selectedKey]} items={menuItems} onClick={({ key }) => navigateFromMenu(key)} />
        <Button danger block icon={<LogoutOutlined />} onClick={handleLogout} className="erp-mobile-logout">退出登录</Button>
      </Drawer>
      {isMobile && <nav className="erp-mobile-bottom-nav" aria-label="移动端主导航">
        <Button type="text" icon={<HomeOutlined />} onClick={() => navigate("/")}>总览</Button>
        <Button type="text" icon={<TeamOutlined />} onClick={() => navigate("/customers")}>客户</Button>
        <Button type="text" icon={<ShoppingCartOutlined />} onClick={() => navigate("/sales/orders")}>订单</Button>
        <Button type="text" icon={<BellOutlined />} onClick={() => navigate("/notifications")}>通知</Button>
        <Button type="text" icon={<MoreOutlined />} onClick={() => setMobileMenuOpen(true)}>更多</Button>
      </nav>}
      <Drawer
        title="AI 问答"
        open={nlpDrawerOpen}
        onClose={() => setNlpDrawerOpen(false)}
        width={isMobile ? "100%" : 480}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="输入您的问题，例如：本月销售额最高的客户是谁？"
              value={nlpQuery}
              onChange={(e) => setNlpQuery(e.target.value)}
              onPressEnter={handleNlpSubmit}
            />
            <Button type="primary" loading={nlpLoading} onClick={handleNlpSubmit}>
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
                        opportunity: "/sales/opportunities",
                        quotation: "/sales/quotations",
                        order: "/sales/orders",
                        invoice: "/sales/invoices",
                        contract: "/sales/contracts",
                        payment: "/sales/payments",
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
                    renderItem={(action) => (
                      <List.Item>
                        <Typography.Text strong>{action.action}</Typography.Text>{" "}
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
                      <Button key={idx} size="small" onClick={() => setNlpQuery(q)}>
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
