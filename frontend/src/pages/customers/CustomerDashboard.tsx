import { useEffect, useState } from "react";
import { Row, Col, Card, Statistic, Spin, Empty } from "antd";
import { TeamOutlined } from "@ant-design/icons";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from "recharts";
import { getDashboardStats } from "../../api";
import type { DashboardStats } from "../../types";

const COLORS = ["#1677ff", "#52c41a", "#fa8c16", "#eb2f96", "#722ed1", "#13c2c2", "#f5222d", "#faad14", "#a0d911", "#2f54eb"];
const LIGHT_COLORS = ["#e6f4ff", "#f6ffed", "#fff7e6", "#fff0f6", "#f9f0ff", "#e6fffb", "#fff1f0", "#fffbe6", "#fcffe6", "#f0f5ff"];

export default function CustomerDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats().then((r) => setStats(r.data.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin style={{ display: "block", marginTop: 100 }} />;
  if (!stats || stats.total === 0) return <Empty description="暂无客户数据" />;

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={6}>
          <Card><Statistic title="客户总数" value={stats.total} prefix={<TeamOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card><Statistic title="行业种类" value={stats.by_industry.length} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card><Statistic title="A级客户" value={stats.by_level.find((l) => l.name === "A")?.value || 0} valueStyle={{ color: "#cf1322" }} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card><Statistic title="A/B级占比" value={Math.round(((stats.by_level.find((l) => l.name === "A")?.value || 0) + (stats.by_level.find((l) => l.name === "B")?.value || 0)) / stats.total * 100)} suffix="%" /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="行业分布">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={stats.by_industry} cx="50%" cy="50%" outerRadius={100} dataKey="value" label={({ name, value }) => `${name}(${value})`}>
                  {stats.by_industry.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="等级分布">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={stats.by_level}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#1677ff" radius={[4, 4, 0, 0]}>
                  {stats.by_level.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="区域分布">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={stats.by_region} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="name" width={60} />
                <Tooltip />
                <Bar dataKey="value" fill="#52c41a" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="来源渠道">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={stats.by_source} cx="50%" cy="50%" innerRadius={50} outerRadius={100} dataKey="value" label={({ name, value }) => `${name}(${value})`}>
                  {stats.by_source.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Card title="月度新增客户趋势" style={{ marginTop: 16 }}>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={stats.monthly}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Area type="monotone" dataKey="count" stroke="#1677ff" fill="#1677ff" fillOpacity={0.2} />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
