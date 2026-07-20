import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Alert, Button, Card, Col, Empty, List, Row, Space, Spin, Table, Tag, Typography } from "antd";
import { StatusTag } from "../../ui";
import { fontSize } from "../../design-tokens";
import {
  BarChartOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  RiseOutlined,
  ShoppingCartOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getOpportunities,
  getQuotations,
  getSalesDashboardAlerts,
  getSalesDashboardOverview,
  getSalesDashboardTrends,
  getSalesOrders,
} from "../../api";
import type {
  Opportunity,
  Quotation,
  SalesDashboardAlerts,
  SalesDashboardOverview,
  SalesDashboardTrends,
  SalesOrder,
} from "../../types";
import { MetricBand, SalesModuleShell, SalesQuickActions, SalesStatusTag, money, shortDate, stageLabel } from "./salesUi";

const COLORS = ["#1677ff", "#52c41a", "#faad14", "#ff4d4f", "#722ed1"];
const ALERT_TYPE: Record<string, { color: string; label: string }> = {
  risk_alert: { color: "red", label: "风险" },
  overdue: { color: "orange", label: "逾期" },
  target_warning: { color: "gold", label: "目标" },
  contract_expiry: { color: "purple", label: "合同" },
};

export default function SalesDashboard() {
  const [overview, setOverview] = useState<SalesDashboardOverview | null>(null);
  const [trends, setTrends] = useState<SalesDashboardTrends | null>(null);
  const [alerts, setAlerts] = useState<SalesDashboardAlerts | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadedAt, setLoadedAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now);
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      setLoading(true);
      const failed: string[] = [];
      const results = await Promise.allSettled([
        getSalesDashboardOverview().then(r => { setOverview(r.data.data); return "overview"; }),
        getSalesDashboardTrends(8).then(r => { setTrends(r.data.data); return "trends"; }),
        getSalesDashboardAlerts().then(r => { setAlerts(r.data.data); return "alerts"; }),
        getOpportunities({ page: 1, page_size: 6, status: "active" })
          .then(r => { setOpportunities(r.data.data.list || []); return "opp"; }),
        getQuotations({ page: 1, page_size: 6, status: "draft" })
          .then(r => { setQuotations(r.data.data.list || []); return "quote"; }),
        getSalesOrders({ page: 1, page_size: 6, status: "pending" })
          .then(r => { setOrders(r.data.data.list || []); return "order"; }),
      ]);
      for (const r of results) {
        if (r.status === "rejected") failed.push(r.reason?.message || String(r.reason).slice(0, 60));
      }
      if (failed.length > 0) setError(`工作台加载失败: ${failed.join("; ")}`);
      setLoadedAt(Date.now());
      setLoading(false);
    })();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(timer);
  }, []);

  const funnel = overview?.funnel || [];
  const wonRate = overview
    ? overview.won_opportunities / Math.max(overview.open_opportunities + overview.won_opportunities, 1) * 100
    : 0;
  const orderAmount = useMemo(() => funnel.find((item) => item.stage === "订单")?.amount || 0, [funnel]);
  const actionCount = opportunities.length + quotations.length + orders.length;

  if (loading) {
    return (
      <SalesModuleShell title="销售工作台" subtitle="客户、产品、商机、报价、订单闭环" activeKey="dashboard">
        <Spin style={{ display: "block", margin: "100px auto" }} />
      </SalesModuleShell>
    );
  }

  if (error) {
    return (
      <SalesModuleShell title="销售工作台" subtitle="客户、产品、商机、报价、订单闭环" activeKey="dashboard">
        <Alert type="error" message={error} />
      </SalesModuleShell>
    );
  }

  return (
    <SalesModuleShell
      title="销售工作台"
      subtitle="从客户需求到产品报价、订单执行和风险跟进的统一入口"
      activeKey="dashboard"
      extra={<SalesQuickActions />}
    >
      <MetricBand
        items={[
          { title: "管道金额", value: overview?.total_pipeline || 0, prefix: "¥", precision: 0 },
          { title: "订单金额", value: orderAmount, prefix: "¥", precision: 0 },
          { title: "活跃商机", value: overview?.open_opportunities || 0, suffix: "个", prefix: <ThunderboltOutlined /> },
          { title: "赢单率", value: wonRate, suffix: "%", precision: 1, prefix: <RiseOutlined /> },
          { title: "报价转订单", value: overview?.quote_to_order_rate || 0, suffix: "%", precision: 1 },
          { title: "待处理", value: actionCount, suffix: "项", prefix: <ExclamationCircleOutlined /> },
        ]}
      />

      {loadedAt ? (
        <div style={{ textAlign: "right", marginBottom: 8, fontSize: 12, color: "#9ca3af" }}>
          <span title={new Date(loadedAt).toLocaleString("zh-CN")}>
            更新于 {(() => {
              const diff = Math.floor((now - loadedAt) / 1000);
              if (diff < 60) return "刚刚";
              if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
              if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
              return `${Math.floor(diff / 86400)}天前`;
            })()}
          </span>
        </div>
      ) : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={15}>
          <Card
            size="small"
            title="销售流程漏斗"
            extra={<Button size="small" type="link" icon={<BarChartOutlined />} onClick={() => navigate("/reports/sales")}>分析</Button>}
          >
            {funnel.length ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={funnel} layout="vertical" margin={{ top: 8, right: 28, left: 36, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="stage" />
                  <Tooltip formatter={(v, name) => (name === "amount" ? money(Number(v)) : v) as ReactNode} />
                  <Legend />
                  <Bar dataKey="count" name="数量" radius={[0, 4, 4, 0]}>
                    {funnel.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <Empty description="暂无漏斗数据" />}
          </Card>
        </Col>
        <Col xs={24} xl={9}>
          <Card size="small" title="管道金额结构">
            {funnel.some((item) => item.amount > 0) ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={funnel.filter((item) => item.amount > 0)} dataKey="amount" nameKey="stage" outerRadius={105} label>
                    {funnel.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v) => money(Number(v)) as ReactNode} />
                </PieChart>
              </ResponsiveContainer>
            ) : <Empty description="暂无金额数据" />}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={16}>
          <Card size="small" title="月度趋势">
            {trends?.trends?.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={trends.trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="revenue" name="订单金额" stroke="#1677ff" strokeWidth={2} />
                  <Line type="monotone" dataKey="opportunities" name="新商机" stroke="#52c41a" strokeWidth={2} />
                  <Line type="monotone" dataKey="orders" name="新订单" stroke="#faad14" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : <Empty description="暂无趋势数据" />}
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card size="small" title="风险提醒">
            {alerts?.alerts?.length ? (
              <List
                dataSource={alerts.alerts}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      title={(
                        <Space>
                          <StatusTag tone={ALERT_TYPE[item.type]?.color}>{ALERT_TYPE[item.type]?.label || item.type}</StatusTag>
                          <Typography.Text>{item.title}</Typography.Text>
                        </Space>
                      )}
                      description={item.content || shortDate(item.created_at)}
                    />
                  </List.Item>
                )}
              />
            ) : <Empty description="暂无风险提醒" />}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={8}>
          <Card size="small" className="sales-erp-table-card" title="近期商机" extra={<Button size="small" type="link" onClick={() => navigate("/sales/opportunities")}>全部</Button>}>
            <Table
              rowKey="id"
              size="small"
              bordered
              pagination={false}
              dataSource={opportunities}
              columns={[
                { title: "商机", dataIndex: "title", ellipsis: true, render: (v: string, r) => <a onClick={() => navigate(`/sales/opportunities/${r.id}`)}>{v}</a> },
                { title: "阶段", dataIndex: "stage", width: 78, render: (v: string) => {
                  const stageColors: Record<string, string> = { lead: "default", qualification: "blue", proposal: "purple", negotiation: "orange", closed_won: "green", closed_lost: "red" };
                  return <StatusTag tone={stageColors[v] || "neutral"} style={{ fontSize: 12, lineHeight: "18px", margin: 0 }}>{stageLabel[v] || v || "-"}</StatusTag>;
                }},
                { title: "金额", dataIndex: "amount", width: 90, render: money },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card size="small" className="sales-erp-table-card" title="待报价" extra={<Button size="small" type="link" icon={<FileTextOutlined />} onClick={() => navigate("/sales/quotations")}>处理</Button>}>
            <Table
              rowKey="id"
              size="small"
              bordered
              pagination={false}
              dataSource={quotations}
              columns={[
                { title: "报价", dataIndex: "quotation_no", ellipsis: true, render: (v: string, r) => <a onClick={() => navigate(`/sales/quotations/${r.id}`)}>{v || r.title || `#${r.id}`}</a> },
                { title: "状态", dataIndex: "status", width: 74, render: (v: string) => <SalesStatusTag value={v} /> },
                { title: "金额", dataIndex: "total_amount", width: 90, render: money },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card size="small" className="sales-erp-table-card" title="待确认订单" extra={<Button size="small" type="link" icon={<ShoppingCartOutlined />} onClick={() => navigate("/sales/orders")}>执行</Button>}>
            <Table
              rowKey="id"
              size="small"
              bordered
              pagination={false}
              dataSource={orders}
              columns={[
                { title: "订单", dataIndex: "order_no", ellipsis: true, render: (v: string, r) => <a onClick={() => navigate(`/sales/orders/${r.id}`)}>{v || `#${r.id}`}</a> },
                { title: "交付", dataIndex: "delivery_date", width: 86, render: (v: string | null) => {
                  if (!v) return "-";
                  const diff = Math.ceil((new Date(v).getTime() - Date.now()) / (24 * 60 * 60 * 1000));
                  if (diff < 0) return <StatusTag tone="danger" style={{ fontSize: 12, lineHeight: "18px", margin: 0 }}>逾期{-diff}天</StatusTag>;
                  if (diff <= 7) return <StatusTag tone="warning" style={{ fontSize: 12, lineHeight: "18px", margin: 0 }}>{diff}天内</StatusTag>;
                  return shortDate(v);
                }},
                { title: "金额", dataIndex: "total_amount", width: 90, render: money },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Card size="small" title="销售闭环健康度" style={{ marginTop: 16 }}>
        <Row gutter={[16, 16]}>
          {[
            { label: "商机到报价", value: overview?.opp_to_quote_rate || 0, color: "#1677ff" },
            { label: "报价到订单", value: overview?.quote_to_order_rate || 0, color: "#52c41a" },
            { label: "赢单沉淀", value: wonRate, color: "#722ed1" },
          ].map((item) => (
            <Col key={item.label} xs={24} md={8}>
              <div
                style={{
                  textAlign: "center",
                  padding: "20px 12px",
                  background: "linear-gradient(135deg, #fafafa 0%, #f3f4f6 100%)",
                  borderRadius: 8,
                  border: "1px solid #e5e7eb",
                }}
              >
                <div style={{ fontSize: fontSize.metric, fontWeight: 700, color: item.color, lineHeight: 1.1 }}>
                  {item.value.toFixed(1)}%
                </div>
                <div
                  style={{
                    marginTop: 8,
                    padding: "2px 12px",
                    display: "inline-block",
                    background: item.color + "18",
                    color: item.color,
                    borderRadius: 12,
                    fontSize: 12,
                    fontWeight: 500,
                  }}
                >
                  {item.label}
                </div>
              </div>
            </Col>
          ))}
        </Row>
      </Card>
    </SalesModuleShell>
  );
}
