import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Spin, Result, Button, Progress, Tag, Alert, Space } from "antd";
import { ShoppingCartOutlined, DollarOutlined, TeamOutlined, FileTextOutlined, TrophyOutlined, MedicineBoxOutlined } from "@ant-design/icons";
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { getDashboardOverview, getDashboardRealtime, getSalesTrend, analyzePipelineHealth } from "../../api";
import type { DashboardOverview, DashboardRealtime, TrendPoint, PipelineHealthResult } from "../../types";

const COLORS = ["#1890ff", "#52c41a", "#faad14", "#ff4d4f", "#722ed1", "#13c2c2"];

const HEALTH_COLOR: Record<string, string> = {
  "健康": "#52c41a", "一般": "#faad14", "需要关注": "#fa8c16", "严重": "#ff4d4f",
};

export default function SalesDashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [realtime, setRealtime] = useState<DashboardRealtime | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [pipelineHealth, setPipelineHealth] = useState<PipelineHealthResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [aiLoading, setAiLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [ov, rt, tr, ph] = await Promise.all([
          getDashboardOverview(),
          getDashboardRealtime(),
          getSalesTrend({ period: "monthly" }),
          analyzePipelineHealth().catch(() => ({ data: { data: null } })),
        ]);
        setOverview(ov.data.data);
        setRealtime(rt.data.data);
        setTrend(tr.data.data);
        const phData = (ph as { data?: { data?: PipelineHealthResult } })?.data?.data ?? null;
        setPipelineHealth(phData);
      } catch { setError(true); }
      finally { setLoading(false); setAiLoading(false); }
    })();
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;
  if (error) return <Result status="warning" title="加载失败" extra={<Button onClick={() => window.location.reload()}>重试</Button>} />;
  if (!overview || !realtime) return <Result status="warning" title="暂无数据" />;

  return (
    <div>
      {/* AI Pipeline Health Banner */}
      {pipelineHealth && !aiLoading && (
        <Alert
          type={pipelineHealth.health_status === "健康" ? "success" : pipelineHealth.health_status === "严重" ? "error" : "warning"}
          message={
            <Space>
              <MedicineBoxOutlined />
              <span>AI 销售健康度: <strong>{pipelineHealth.health_score}分</strong> — {pipelineHealth.health_status}</span>
              <span style={{ color: "#666" }}>{pipelineHealth.pipeline_assessment}</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
          showIcon={false}
        />
      )}

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={4}><Card><Statistic title="今日订单" value={overview.today_orders} prefix={<ShoppingCartOutlined />} /></Card></Col>
        <Col span={4}><Card><Statistic title="今日销售额" value={overview.today_order_amount} precision={2} prefix="¥" /></Card></Col>
        <Col span={4}><Card><Statistic title="今日商机" value={overview.today_opportunities} prefix={<FileTextOutlined />} /></Card></Col>
        <Col span={4}><Card><Statistic title="活跃商机" value={overview.active_opportunities} prefix={<TrophyOutlined />} /></Card></Col>
        <Col span={4}><Card><Statistic title="已赢单金额" value={overview.won_amount} precision={2} prefix="¥" valueStyle={{ color: "#52c41a" }} /></Card></Col>
        <Col span={4}><Card><Statistic title="客户总数" value={overview.total_customers} prefix={<TeamOutlined />} /></Card></Col>
      </Row>

      {/* AI Health Score */}
      {pipelineHealth && !aiLoading && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card title="AI 管道健康度" size="small">
              <div style={{ textAlign: "center", marginBottom: 12 }}>
                <Progress type="circle" percent={pipelineHealth.health_score} size={100}
                  strokeColor={pipelineHealth.health_score >= 80 ? "#52c41a" : pipelineHealth.health_score >= 50 ? "#faad14" : "#ff4d4f"}
                />
                <Tag color={HEALTH_COLOR[pipelineHealth.health_status] ?? "default"} style={{ marginLeft: 12, fontSize: 14 }}>
                  {pipelineHealth.health_status}
                </Tag>
              </div>
            </Card>
          </Col>
          <Col span={8}>
            <Card title="瓶颈问题" size="small" style={{ height: "100%" }}>
              {pipelineHealth.bottlenecks?.length > 0
                ? pipelineHealth.bottlenecks.map((b, i) => <div key={i} style={{ color: "#ff4d4f", marginBottom: 4 }}>• {b}</div>)
                : <div style={{ color: "#999" }}>暂无瓶颈检测</div>}
            </Card>
          </Col>
          <Col span={8}>
            <Card title="AI 建议" size="small" style={{ height: "100%" }}>
              {pipelineHealth.recommendations?.length > 0
                ? pipelineHealth.recommendations.map((r, i) => <div key={i} style={{ color: "#1890ff", marginBottom: 4 }}>• {r}</div>)
                : <div style={{ color: "#999" }}>暂无优化建议</div>}
            </Card>
          </Col>
        </Row>
      )}

      <Row gutter={24} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="销售趋势">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="total_amount" stroke="#1890ff" fill="#1890ff" fillOpacity={0.3} name="销售额" />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="订单状态分布">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={realtime.order_status} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={100} label>
                  {realtime.order_status.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Row gutter={24}>
        <Col span={12}>
          <Card title="Top 10 客户">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={realtime.top_customers} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="name" width={100} />
                <Tooltip />
                <Bar dataKey="amount" fill="#52c41a" name="销售额" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Top 10 产品">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={realtime.top_products} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="name" width={100} />
                <Tooltip />
                <Bar dataKey="count" fill="#1890ff" name="订单数" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
