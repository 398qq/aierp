import { useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router";
import { Button, Input, Avatar, Tooltip, Badge, Drawer, Card, Tag, Spin, Space, List, Typography, theme } from "antd";
import {
  DashboardOutlined, TeamOutlined, ShopOutlined, StockOutlined, SettingOutlined,
  LogoutOutlined, PieChartOutlined, RobotOutlined, BellOutlined, TagOutlined,
  ThunderboltOutlined, FileTextOutlined, ShoppingCartOutlined, CarOutlined,
  FileDoneOutlined, DollarOutlined, ProfileOutlined, AimOutlined, WarningOutlined,
  SwapOutlined, UploadOutlined, IssuesCloseOutlined, HeartOutlined, TrophyOutlined,
  SearchOutlined, QuestionCircleOutlined, FullscreenOutlined, UserOutlined, HomeOutlined,
} from "@ant-design/icons";
import { ProLayout } from "@ant-design/pro-components";
import { useAuthStore } from "../store/auth";
import { getUnreadCount, naturalLanguageQuery } from "../api";
import type { NLPQueryResult } from "../types";
import type { MenuDataItem } from "@ant-design/pro-components";
import "../styles/app-shell.css";

const { Text } = Typography;
const { useToken } = theme;

const menuItems: MenuDataItem[] = [
  {
    key: "_domain_overview", icon: <DashboardOutlined />, name: "经营总览",
    children: [
      { key: "/", icon: <DashboardOutlined />, name: "经营总览" },
      { key: "/dashboard/global360", icon: <PieChartOutlined />, name: "全局360" },
      { key: "/dashboard/watchtower", icon: <WarningOutlined />, name: "全局监控" },
    ],
  },
  {
    key: "_domain_sales", icon: <ThunderboltOutlined />, name: "客户与销售",
    children: [
      { key: "/customers/stats", icon: <DashboardOutlined />, name: "客户工作台" },
      { key: "/customers", icon: <TeamOutlined />, name: "客户台账" },
      { key: "/customers/follow-ups", icon: <FileTextOutlined />, name: "跟进任务" },
      { key: "/customers/release-rules", icon: <WarningOutlined />, name: "释放规则" },
      { key: "/customers/assignment-rules", icon: <ThunderboltOutlined />, name: "自动分配规则" },
      { key: "/customers/transfer-requests", icon: <SwapOutlined />, name: "转移审批" },
      { key: "/sales/dashboard", icon: <DashboardOutlined />, name: "销售工作台" },
      { key: "/sales/inquiry", icon: <RobotOutlined />, name: "询价回复" },
      { key: "/sales/opportunities", icon: <ThunderboltOutlined />, name: "商机管理" },
      { key: "/sales/quotations", icon: <FileTextOutlined />, name: "报价管理" },
      { key: "/sales/orders", icon: <ShoppingCartOutlined />, name: "销售订单" },
      { key: "/sales/contracts", icon: <ProfileOutlined />, name: "合同管理" },
      { key: "/sales/delivery-notes", icon: <CarOutlined />, name: "发货管理" },
      { key: "/sales/invoices", icon: <FileDoneOutlined />, name: "发票管理" },
      { key: "/sales/payments", icon: <DollarOutlined />, name: "回款管理" },
      { key: "/sales/targets", icon: <AimOutlined />, name: "销售目标" },
    ],
  },
  {
    key: "_domain_procurement", icon: <ShoppingCartOutlined />, name: "采购与供应链",
    children: [
      { key: "/procurement/dashboard", icon: <DashboardOutlined />, name: "采购工作台" },
      { key: "/sales/purchase-orders", icon: <ShoppingCartOutlined />, name: "采购订单" },
      { key: "/suppliers/stats", icon: <DashboardOutlined />, name: "供应商总览" },
      { key: "/suppliers", icon: <TeamOutlined />, name: "供应商台账" },
      { key: "/suppliers/compare", icon: <SwapOutlined />, name: "供应商对比" },
    ],
  },
  {
    key: "_domain_inventory", icon: <StockOutlined />, name: "产品与库存",
    children: [
      { key: "/products", icon: <ShopOutlined />, name: "产品台账" },
      { key: "/products/price-import", icon: <UploadOutlined />, name: "价格导入" },
      { key: "/brands", icon: <TagOutlined />, name: "品牌管理" },
      { key: "/inventory", icon: <StockOutlined />, name: "库存总览" },
      { key: "/warehouse/warehouses", icon: <ShopOutlined />, name: "仓库管理" },
      { key: "/warehouse/inventory-ledger", icon: <FileTextOutlined />, name: "库存台账" },
      { key: "/warehouse/inventory-batches", icon: <FileTextOutlined />, name: "批次与 COGS" },
    ],
  },
  {
    key: "_domain_finance", icon: <DollarOutlined />, name: "财务管理",
    children: [
      { key: "/finance/accounts", icon: <FileTextOutlined />, name: "会计科目" },
      { key: "/finance/journal-entries", icon: <ProfileOutlined />, name: "记账凭证" },
      { key: "/finance/pnl", icon: <PieChartOutlined />, name: "损益表" },
      { key: "/reports/ar", icon: <DollarOutlined />, name: "应收账款" },
      { key: "/reports/ap", icon: <DollarOutlined />, name: "应付账款" },
      { key: "/finance/commissions", icon: <TrophyOutlined />, name: "佣金管理" },
      { key: "/finance/commission-schemes", icon: <SettingOutlined />, name: "提成方案" },
    ],
  },
  {
    key: "_domain_analytics", icon: <PieChartOutlined />, name: "报表与分析",
    children: [
      { key: "/reports/sales", icon: <PieChartOutlined />, name: "销售报表" },
      { key: "/reports/inventory", icon: <StockOutlined />, name: "库存报表" },
      { key: "/reports/procurement", icon: <ShoppingCartOutlined />, name: "采购报表" },
      { key: "/customers/intelligence", icon: <HeartOutlined />, name: "客户分析" },
    ],
  },
  {
    key: "_domain_collaboration", icon: <IssuesCloseOutlined />, name: "协作与审批",
    children: [
      { key: "/system/approvals", icon: <FileDoneOutlined />, name: "审批管理" },
      { key: "/system/approval-rules", icon: <ProfileOutlined />, name: "审批规则" },
      { key: "/tickets", icon: <IssuesCloseOutlined />, name: "工单管理" },
      { key: "/notifications", icon: <BellOutlined />, name: "通知中心" },
      { key: "/ai/chat", icon: <RobotOutlined />, name: "AI 助手" },
    ],
  },
  {
    key: "_domain_system", icon: <SettingOutlined />, name: "系统治理",
    children: [
      { key: "/system/users", icon: <TeamOutlined />, name: "用户管理" },
      { key: "/system/roles", icon: <TeamOutlined />, name: "角色权限" },
      { key: "/system/uoms", icon: <ShopOutlined />, name: "计量单位" },
      { key: "/system/audit-logs", icon: <FileTextOutlined />, name: "审计日志" },
      { key: "/data/import-export", icon: <SwapOutlined />, name: "导入与导出" },
      { key: "/settings", icon: <SettingOutlined />, name: "系统设置" },
    ],
  },
];

function flattenKeys(items: MenuDataItem[]): { key: string; name: string }[] {
  const r: { key: string; name: string }[] = [];
  for (const item of items) {
    if (typeof item.key === "string" && item.key.startsWith("/")) r.push({ key: item.key, name: item.name as string });
    if (item.children) r.push(...flattenKeys(item.children));
  }
  return r;
}

const searchableRoutes = flattenKeys(menuItems);

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const username = useAuthStore((s) => s.username);
  const roles = useAuthStore((s) => s.roles);
  const { token } = useToken();

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
      if (resp.data.code === 0) setNlpResult(resp.data.data);
    } catch { /* ignore */ }
    finally { setNlpLoading(false); }
  };

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

  const selectedKey =
    searchableRoutes
      .map((item) => item.key)
      .filter((key) => location.pathname === key || location.pathname.startsWith(`${key}/`))
      .sort((a, b) => b.length - a.length)[0] || location.pathname;

  const handleClick = (item: MenuDataItem) => {
    if (item.key && typeof item.key === "string" && !item.key.startsWith("_")) {
      navigate(item.key);
    }
  };

  return (
    <>
      <ProLayout
        collapsed={collapsed}
        onCollapse={setCollapsed}
        menuDataRender={() => menuItems}
        location={{ pathname: selectedKey }}
        logo="https://gw.alipayobjects.com/zos/antfincdn/FLrTNDvlna/antdesign.png"
        title="AIERP"
        onMenuHeaderClick={() => navigate("/")}
        menuItemRender={(item, dom) => (
          <a onClick={() => handleClick(item)}>{dom}</a>
        )}
        headerTitleRender={(logo, title) => (
          <a onClick={() => navigate("/")} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              width: 32, height: 32, borderRadius: 6, background: token.colorPrimary,
              color: "#fff", fontWeight: 700, fontSize: 16,
            }}>AI</span>
            <strong style={{ fontSize: 18 }}>{title}</strong>
          </a>
        )}
        actionsRender={() => [
          <Input.Search key="search" placeholder="搜索菜单" allowClear
            onSearch={(v) => {
              const q = v.trim().toLowerCase();
              if (!q) return;
              const m = searchableRoutes.find(i => i.name.toLowerCase().includes(q) || i.key.toLowerCase().includes(q));
              if (m) navigate(m.key);
            }}
            style={{ width: 200 }}
          />,
          <Tooltip key="ai" title="AI 助手">
            <Button type="text" icon={<RobotOutlined />} onClick={() => setNlpDrawerOpen(true)} />
          </Tooltip>,
          <Badge key="notif" count={unreadCount} size="small">
            <Button type="text" icon={<BellOutlined />} onClick={() => navigate("/notifications")} />
          </Badge>,
          <Tooltip key="user" title={`${username || "用户"} · ${roles[0] || "业务用户"}`}>
            <Avatar size={30} icon={<UserOutlined />} style={{ cursor: "pointer" }} />
          </Tooltip>,
          <Button key="logout" type="text" icon={<LogoutOutlined />} onClick={() => { logout(); navigate("/login"); }}>
            退出
          </Button>,
        ]}
        contentStyle={{ margin: 16, minHeight: "calc(100vh - 64px)" }}
      >
        <Outlet />
      </ProLayout>

      <Drawer title="AI 问答" open={nlpDrawerOpen} onClose={() => setNlpDrawerOpen(false)} width={480}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Space.Compact style={{ width: "100%" }}>
            <Input placeholder="输入您的问题" value={nlpQuery}
              onChange={(e) => setNlpQuery(e.target.value)} onPressEnter={handleNlpSubmit} />
            <Button type="primary" loading={nlpLoading} onClick={handleNlpSubmit}>发送</Button>
          </Space.Compact>
          {nlpLoading && <div style={{ textAlign: "center", padding: 24 }}><Spin tip="AI 正在分析..." /></div>}
          {nlpResult && (
            <>
              <Card size="small" title="回答" extra={<Tag color={nlpResult.confidence > 0.7 ? "green" : "orange"}>{(nlpResult.confidence * 100).toFixed(0)}%</Tag>}>
                <Text>{nlpResult.answer}</Text>
              </Card>
              {nlpResult.data_summary && <Card size="small" title="数据摘要"><Text>{nlpResult.data_summary}</Text></Card>}
              {nlpResult.related_entities?.length > 0 && (
                <Card size="small" title="相关实体">
                  <Space wrap>{nlpResult.related_entities.map((e, i) => (
                    <Tag key={i} color="blue" style={{ cursor: "pointer" }}
                      onClick={() => { setNlpDrawerOpen(false); navigate(`/${e.type}s/${e.id}`); }}>{e.type}: {e.name}</Tag>
                  ))}</Space>
                </Card>
              )}
              {nlpResult.actions?.length > 0 && (
                <Card size="small" title="建议操作">
                  <List size="small" dataSource={nlpResult.actions}
                    renderItem={(a) => <List.Item><Text strong>{a.action}</Text> <Tag color="orange">{a.urgency}</Tag></List.Item>} />
                </Card>
              )}
              {nlpResult.suggested_followups?.length > 0 && (
                <Card size="small" title="追问建议">
                  <Space wrap>{nlpResult.suggested_followups.map((q, i) => (
                    <Button key={i} size="small" onClick={() => setNlpQuery(q)}>{q}</Button>
                  ))}</Space>
                </Card>
              )}
            </>
          )}
        </Space>
      </Drawer>
    </>
  );
}
