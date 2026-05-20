import { useEffect, useState } from "react";
import { Row, Col, Card, Spin, Empty, Typography } from "antd";
import { TeamOutlined } from "@ant-design/icons";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { getDashboardStats } from "../../api";
import type { DashboardStats } from "../../types";
import CustomerModuleShell from "./CustomerModuleShell";

const COLORS = ["#1677ff", "#52c41a", "#fa8c16", "#eb2f96", "#722ed1", "#13c2c2", "#f5222d", "#faad14", "#a0d911", "#2f54eb"];
const { Text } = Typography;

export default function CustomerDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats().then((r) => setStats(r.data.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <CustomerModuleShell title="客户统计" subtitle="客户结构、来源和趋势看板">
        <Spin style={{ display: "block", marginTop: 100 }} />
      </CustomerModuleShell>
    );
  }
  if (!stats || stats.total === 0) {
    return (
      <CustomerModuleShell title="客户统计" subtitle="客户结构、来源和趋势看板">
        <Empty description="暂无客户数据" />
      </CustomerModuleShell>
    );
  }

  const levelA = stats.by_level.find((item) => item.name === "A")?.value || 0;
  const levelB = stats.by_level.find((item) => item.name === "B")?.value || 0;
  const abRatio = Math.round(((levelA + levelB) / stats.total) * 100);
  const topIndustry = stats.by_industry[0];
  const topRegion = stats.by_region[0];
  const latestMonthly = stats.monthly[stats.monthly.length - 1];

  return (
    <CustomerModuleShell title="客户统计" subtitle="客户结构、来源和趋势看板">
      <style>{`
        .customer-dashboard-overview {
          display: grid;
          grid-template-columns: repeat(6, minmax(120px, 1fr));
          gap: 8px;
          padding: 12px;
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-dashboard-metric {
          min-height: 58px;
          padding: 8px 10px;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-dashboard-metric.is-primary {
          background: #e6f4ff;
          border-color: #bae0ff;
        }
        .customer-dashboard-metric.is-risk {
          background: #fff1f0;
          border-color: #ffccc7;
        }
        .customer-dashboard-metric-label {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 18px;
        }
        .customer-dashboard-metric-value {
          margin-top: 4px;
          color: #262626;
          font-size: 20px;
          font-weight: 600;
          line-height: 1.1;
        }
        .customer-dashboard-metric-note {
          color: #8c8c8c;
          font-size: 12px;
        }
        .customer-dashboard-grid {
          margin-top: 12px;
        }
        .customer-dashboard-chart .ant-card-head {
          min-height: 44px;
        }
        .customer-dashboard-chart .ant-card-body {
          padding: 12px;
        }
        @media (max-width: 1200px) {
          .customer-dashboard-overview {
            grid-template-columns: repeat(3, minmax(140px, 1fr));
          }
        }
        @media (max-width: 768px) {
          .customer-dashboard-overview {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }
      `}</style>

      <div className="customer-dashboard-overview">
        <div className="customer-dashboard-metric is-primary">
          <div className="customer-dashboard-metric-label"><TeamOutlined /> 客户总数</div>
          <div className="customer-dashboard-metric-value">{stats.total}</div>
        </div>
        <div className="customer-dashboard-metric">
          <div className="customer-dashboard-metric-label">行业种类</div>
          <div className="customer-dashboard-metric-value">{stats.by_industry.length}</div>
        </div>
        <div className="customer-dashboard-metric is-risk">
          <div className="customer-dashboard-metric-label">A级客户</div>
          <div className="customer-dashboard-metric-value">{levelA}</div>
        </div>
        <div className="customer-dashboard-metric">
          <div className="customer-dashboard-metric-label">A/B级占比</div>
          <div className="customer-dashboard-metric-value">{abRatio}%</div>
        </div>
        <div className="customer-dashboard-metric">
          <div className="customer-dashboard-metric-label">主力区域</div>
          <div className="customer-dashboard-metric-value">{topRegion?.name || "-"}</div>
          {topRegion && <div className="customer-dashboard-metric-note">{topRegion.value} 个客户</div>}
        </div>
        <div className="customer-dashboard-metric">
          <div className="customer-dashboard-metric-label">本月新增</div>
          <div className="customer-dashboard-metric-value">{latestMonthly?.count || 0}</div>
          {latestMonthly && <div className="customer-dashboard-metric-note">{latestMonthly.month}</div>}
        </div>
      </div>

      <Row gutter={[12, 12]} className="customer-dashboard-grid">
        <Col xs={24} lg={12}>
          <Card size="small" className="customer-dashboard-chart" title="行业分布" extra={<Text type="secondary">{topIndustry ? `${topIndustry.name} ${topIndustry.value}` : "-"}</Text>}>
            <ResponsiveContainer width="100%" height={280}>
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
          <Card size="small" className="customer-dashboard-chart" title="等级分布">
            <ResponsiveContainer width="100%" height={280}>
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

      <Row gutter={[12, 12]} className="customer-dashboard-grid">
        <Col xs={24} lg={12}>
          <Card size="small" className="customer-dashboard-chart" title="区域分布">
            <ResponsiveContainer width="100%" height={280}>
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
          <Card size="small" className="customer-dashboard-chart" title="来源渠道">
            <ResponsiveContainer width="100%" height={280}>
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

      <Card size="small" className="customer-dashboard-chart customer-dashboard-grid" title="月度新增客户趋势">
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
    </CustomerModuleShell>
  );
}
