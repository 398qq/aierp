import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, DatePicker, Select, Spin, Alert, Empty, Typography } from "antd";
import { DollarOutlined, OrderedListOutlined, BarChartOutlined, PieChartOutlined } from "@ant-design/icons";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell, Legend, ResponsiveContainer } from "recharts";
import dayjs from "dayjs";
import { getSalesSummary, getSalesTrend, getStageDistribution, getSalesFunnel } from "../../api";
import type { SalesSummary, TrendPoint, StageDistribution, FunnelStage } from "../../types";

const { Title } = Typography;
const { RangePicker } = DatePicker;

const STAGE_COLORS: Record<string, string> = {
  lead: "#bfbfbf", qualified: "#1677ff", proposal: "#fa8c16", negotiation: "#722ed1", won: "#52c41a", lost: "#ff4d4f",
};

export default function SalesStats() {
  const [summary, setSummary] = useState<SalesSummary | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [distribution, setDistribution] = useState<StageDistribution[]>([]);
  const [funnel, setFunnel] = useState<FunnelStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<string>("monthly");
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);

  const fetch = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { period };
      if (dateRange) {
        params.start_date = dateRange[0];
        params.end_date = dateRange[1];
      }
      const [sumResp, trendResp, distResp, funnelResp] = await Promise.all([
        getSalesSummary(),
        getSalesTrend(params),
        getStageDistribution(),
        getSalesFunnel(),
      ]);
      setSummary(sumResp.data.data as SalesSummary);
      setTrend((trendResp.data.data as TrendPoint[]) || []);
      setDistribution((distResp.data.data as StageDistribution[]) || []);
      setFunnel((funnelResp.data.data as FunnelStage[]) || []);
    } catch (e) {
      setError((e as Error).message || "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetch(); }, [period, dateRange]);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;

  return (
    <div>
      <Title level={4}>销售统计报表</Title>

      {/* Summary Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总订单数" value={summary?.total_orders || 0} prefix={<OrderedListOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="总金额" value={summary?.total_amount || 0} prefix={<DollarOutlined />} precision={2} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="平均订单额" value={summary?.avg_amount || 0} prefix={<BarChartOutlined />} precision={2} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="活跃商机" value={summary?.active_opportunities || 0} prefix={<PieChartOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <div style={{ marginBottom: 16, display: "flex", gap: 12 }}>
        <Select value={period} onChange={setPeriod} style={{ width: 120 }}
          options={[{ value: "monthly", label: "按月" }, { value: "quarterly", label: "按季度" }]} />
        <RangePicker
          onChange={(dates) => {
            if (dates && dates[0] && dates[1]) {
              setDateRange([dates[0].format("YYYY-MM-DD"), dates[1].format("YYYY-MM-DD")]);
            } else {
              setDateRange(null);
            }
          }}
        />
      </div>

      {/* Trend Chart */}
      <Card title="销售趋势" style={{ marginBottom: 16 }}>
        {trend.length ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="order_count" name="订单数" stroke="#1677ff" strokeWidth={2} />
              <Line yAxisId="right" type="monotone" dataKey="total_amount" name="金额" stroke="#52c41a" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        ) : <Empty description="暂无趋势数据" />}
      </Card>

      {/* Stage Distribution + Funnel */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title="商机阶段分布">
            {distribution.length ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={distribution} dataKey="count" nameKey="stage" cx="50%" cy="50%" outerRadius={100} label={({ stage, percentage }) => `${stage} ${percentage}%`}>
                    {distribution.map((d) => (
                      <Cell key={d.stage} fill={STAGE_COLORS[d.stage] || "#ccc"} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : <Empty description="暂无阶段分布数据" />}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="销售漏斗概览">
            {funnel.length ? (
              <div>
                {funnel.map((item) => (
                  <div key={item.stage} style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 13 }}>
                      <span>{item.stage}</span>
                      <span>{item.count} 个 · ¥{(item.amount || 0).toLocaleString()}</span>
                    </div>
                    <div style={{ height: 28, width: `${Math.max((item.count / Math.max(...funnel.map(d => d.count), 1)) * 100, 5)}%`, backgroundColor: STAGE_COLORS[item.stage] || "#ccc", borderRadius: 4 }} />
                  </div>
                ))}
              </div>
            ) : <Empty description="暂无漏斗数据" />}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
