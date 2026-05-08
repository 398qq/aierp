import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Table, Tag, Progress, Spin, Alert, Empty } from "antd";
import {
  ThunderboltOutlined, FileTextOutlined, ShoppingCartOutlined,
  CarOutlined, WarningOutlined, RiseOutlined, FallOutlined,
} from "@ant-design/icons";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, LineChart, Line,
  Legend, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import { getSalesDashboardOverview, getSalesDashboardTrends, getSalesDashboardAlerts } from "../../api";
import type { SalesDashboardOverview, SalesDashboardTrends, SalesDashboardAlerts } from "../../types";

const FUNNEL_COLORS = ["#1677ff", "#52c41a", "#faad14", "#ff4d4f"];
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [o, t, a] = await Promise.all([
          getSalesDashboardOverview(),
          getSalesDashboardTrends(),
          getSalesDashboardAlerts(),
        ]);
        setOverview(o.data.data);
        setTrends(t.data.data);
        setAlerts(a.data.data);
      } catch {
        setError("加载失败");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;

  const funnel = overview?.funnel || [];
  const maxCount = Math.max(...funnel.map((f) => f.count), 1);
  const winRate = overview ? (overview.won_opportunities / Math.max(overview.open_opportunities + overview.won_opportunities, 1) * 100) : 0;

  return (
    <div>
      {/* KPI Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card size="small">
            <Statistic title="总管道金额" value={overview?.total_pipeline || 0} prefix="¥" precision={0} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="进行中商机" value={overview?.open_opportunities || 0} suffix="个" />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="赢单率" value={winRate} suffix="%" precision={1} />
            <Progress percent={winRate} size="small" strokeColor={winRate >= 30 ? "#52c41a" : "#faad14"} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="报价→订单" value={overview?.quote_to_order_rate || 0} suffix="%" precision={1} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="商机→报价" value={overview?.opp_to_quote_rate || 0} suffix="%" precision={1} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="AI 告警" value={alerts?.alerts.length || 0} suffix="条"
              valueStyle={{ color: alerts?.alerts.length ? "#ff4d4f" : undefined }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {/* Sales Funnel */}
        <Col span={12}>
          <Card title="销售漏斗" bodyStyle={{ padding: 16 }}>
            {funnel.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={funnel} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="stage" />
                  <Tooltip formatter={(v: number) => v.toLocaleString()} />
                  <Bar dataKey="count" name="数量" radius={[0, 4, 4, 0]}>
                    {funnel.map((_, i) => <Cell key={i} fill={FUNNEL_COLORS[i % FUNNEL_COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <Empty description="暂无数据" />}

            {/* Conversion arrows */}
            <div style={{ display: "flex", justifyContent: "space-around", marginTop: 12, padding: "0 40px" }}>
              {funnel.slice(0, -1).map((f, i) => {
                const next = funnel[i + 1];
                const rate = f.count > 0 ? (next.count / f.count * 100) : 0;
                return (
                  <div key={i} style={{ textAlign: "center" }}>
                    <Tag color={rate >= 50 ? "green" : rate >= 25 ? "orange" : "red"}>
                      {rate.toFixed(0)}% 转化
                    </Tag>
                  </div>
                );
              })}
            </div>
          </Card>
        </Col>

        {/* Pipeline Amount Pie */}
        <Col span={12}>
          <Card title="管道金额分布" bodyStyle={{ padding: 16 }}>
            {funnel.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={funnel.filter((f) => f.amount > 0)}
                    dataKey="amount"
                    nameKey="stage"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ stage, amount }) => `${stage} ¥${(amount / 10000).toFixed(0)}万`}
                  >
                    {funnel.filter((f) => f.amount > 0).map((_, i) => (
                      <Cell key={i} fill={FUNNEL_COLORS[i % FUNNEL_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => `¥${v.toLocaleString()}`} />
                </PieChart>
              </ResponsiveContainer>
            ) : <Empty description="暂无数据" />}
          </Card>
        </Col>
      </Row>

      {/* Monthly Revenue Trend */}
      <Card title="月度趋势" style={{ marginBottom: 16 }} bodyStyle={{ padding: 16 }}>
        {trends?.trends?.length ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={trends.trends} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="revenue" name="营收 (¥)" stroke="#1677ff" strokeWidth={2} />
              <Line yAxisId="right" type="monotone" dataKey="opportunities" name="新商机" stroke="#52c41a" strokeWidth={2} />
              <Line yAxisId="right" type="monotone" dataKey="orders" name="新订单" stroke="#faad14" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        ) : <Empty description="暂无数据" />}
      </Card>

      {/* AI Alerts */}
      <Card
        title={<span><WarningOutlined style={{ color: "#ff4d4f", marginRight: 8 }} />AI 智能告警</span>}
      >
        {alerts?.alerts?.length ? (
          <Table
            rowKey="id"
            dataSource={alerts.alerts}
            pagination={false}
            size="small"
            columns={[
              {
                title: "类型", dataIndex: "type", width: 80,
                render: (v: string) => <Tag color={ALERT_TYPE[v]?.color}>{ALERT_TYPE[v]?.label || v}</Tag>,
              },
              { title: "标题", dataIndex: "title", ellipsis: true },
              { title: "内容", dataIndex: "content", ellipsis: true, render: (v: string | null) => v || "-" },
              {
                title: "时间", dataIndex: "created_at", width: 160,
                render: (v: string | null) => v ? new Date(v).toLocaleString() : "-",
              },
            ]}
          />
        ) : <Empty description="暂无告警，一切正常" />}
      </Card>
    </div>
  );
}
