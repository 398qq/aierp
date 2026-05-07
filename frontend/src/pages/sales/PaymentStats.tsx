import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Spin, Result, Button } from "antd";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { getPaymentSummary } from "../../api";
import type { PaymentSummary } from "../../types";

const COLORS = ["#52c41a", "#faad14", "#ff4d4f"];

export default function PaymentStats() {
  const [stats, setStats] = useState<PaymentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const resp = await getPaymentSummary();
        setStats(resp.data.data);
      } catch { setError(true); }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;
  if (error) return <Result status="warning" title="加载失败" extra={<Button onClick={() => window.location.reload()}>重试</Button>} />;
  if (!stats) return <Result status="warning" title="暂无数据" />;

  const chartData = [
    { name: "已回款", value: stats.received_total },
    { name: "待回款", value: stats.pending_total },
    { name: "逾期", value: stats.overdue_total },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card><Statistic title="已回款总额" value={stats.received_total} precision={2} prefix="¥" valueStyle={{ color: "#52c41a" }} loading={loading} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="待回款总额" value={stats.pending_total} precision={2} prefix="¥" valueStyle={{ color: "#faad14" }} loading={loading} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="逾期总额" value={stats.overdue_total} precision={2} prefix="¥" valueStyle={{ color: "#ff4d4f" }} loading={loading} /></Card>
        </Col>
      </Row>
      <Card title="回款分布">
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
              {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
