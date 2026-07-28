import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Row, Col, Statistic, Tag, Spin, Button, Space, Typography } from "antd";
import { ProTable } from "@ant-design/pro-components";
import {
  ShopOutlined, SafetyCertificateOutlined, RiseOutlined,
  PieChartOutlined, RightOutlined, ReloadOutlined,
} from "@ant-design/icons";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const { Title, Text } = Typography;

const COLORS = ["#1890ff", "#52c41a", "#faad14", "#f5222d", "#722ed1", "#13c2c2", "#eb2f96"];

interface SupplierStats {
  total: number; certified: number; recent_30d: number;
  by_type: { type: string; count: number }[];
  by_region: { region: string; count: number }[];
  by_rating: { rating: string; count: number }[];
  top_suppliers: { id: number; name: string; product_count: number }[];
}

export default function SupplierDashboard() {
  const [stats, setStats] = useState<SupplierStats | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchStats = async () => {
    setLoading(true);
    try {
      const api = await import("../../api");
      const resp = await api.getSupplierStats();
      setStats(resp.data.data as unknown as SupplierStats);
    } catch {
      // fallback to empty
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStats(); }, []);

  if (loading) return <Spin size="large" style={{ display: "block", marginTop: 100 }} />;

  const s = stats;
  if (!s) return <Text type="secondary">无法加载供应商统计数据</Text>;

  const topColumns = [
    { title: "排名", key: "rank", width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    {
      title: "供应商", dataIndex: "name", key: "name",
      render: (v: string, r: { id: number }) => <a onClick={() => navigate(`/suppliers/${r.id}`)}>{v}</a>,
    },
    { title: "关联产品数", dataIndex: "product_count", key: "pc", width: 100 },
    {
      title: "操作", key: "action", width: 80,
      render: (_: unknown, r: { id: number }) => (
        <Button size="small" icon={<RightOutlined />} onClick={() => navigate(`/suppliers/${r.id}`)} />
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <ShopOutlined style={{ marginRight: 8 }} />
          供应商总览
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchStats}>刷新</Button>
          <Button type="primary" onClick={() => navigate("/suppliers")}>全部供应商</Button>
        </Space>
      </div>

      {/* KPI Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card><Statistic title="供应商总数" value={s.total} prefix={<ShopOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="有资质认证" value={s.certified} prefix={<SafetyCertificateOutlined />} suffix={`${s.total > 0 ? Math.round(s.certified / s.total * 100) : 0}%`} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="近30天新增" value={s.recent_30d} prefix={<RiseOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="评级A/B占比" value={`${s.by_rating.filter(r => ["A", "B"].includes(r.rating)).reduce((a, b) => a + b.count, 0)}`} prefix={<PieChartOutlined />} suffix={`${s.total > 0 ? Math.round(s.by_rating.filter(r => ["A", "B"].includes(r.rating)).reduce((a, b) => a + b.count, 0) / s.total * 100) : 0}%`} /></Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card title="供应商类型分布" size="small">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={s.by_type} dataKey="count" nameKey="type" cx="50%" cy="50%" outerRadius={70} label={(entry) => { const e = entry as unknown as { type: string; count: number }; return `${e.type}: ${e.count}`; }}>
                  {s.by_type.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="区域分布" size="small">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={s.by_region}>
                <XAxis dataKey="region" fontSize={11} />
                <YAxis fontSize={11} />
                <Tooltip />
                <Bar dataKey="count" fill="#1890ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="财务评级分布" size="small">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={s.by_rating} dataKey="count" nameKey="rating" cx="50%" cy="50%" outerRadius={70} label={(entry) => { const e = entry as unknown as { rating: string; count: number }; return `${e.rating}: ${e.count}`; }}>
                  {s.by_rating.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Top Suppliers Table */}
      <Card title="Top 供应商（按关联产品数）" size="small">
        <ProTable search={false} options={false} rowKey="id" columns={topColumns as any} dataSource={s.top_suppliers} size="small" pagination={false} />
      </Card>
    </div>
  );
}
