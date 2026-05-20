import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Row, Col, Statistic, Table, Tag, Spin, Button, Space, Typography, Alert, List, Progress } from "antd";
import {
  BankOutlined, AlertOutlined, RiseOutlined,
  PieChartOutlined, RightOutlined, ReloadOutlined, CarOutlined, WarningOutlined,
} from "@ant-design/icons";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const { Title, Text } = Typography;

const STATUS_COLORS: Record<string, string> = { active: "#52c41a", inactive: "#faad14", frozen: "#f5222d" };
const LC_COLORS: Record<string, string> = { active: "#52c41a", nrnd: "#faad14", eol: "#f5222d" };
const RISK_COLORS: Record<string, string> = { low: "#52c41a", medium: "#faad14", high: "#f5222d", critical: "#722ed1" };
const STATUS_LABELS: Record<string, string> = { active: "启用", inactive: "停用", frozen: "冻结" };
const LC_LABELS: Record<string, string> = { active: "Active", nrnd: "NRND", eol: "EOL" };
const RISK_LABELS: Record<string, string> = { low: "低", medium: "中", high: "高", critical: "严重" };
const TYPE_LABELS: Record<string, string> = { own_brand: "自有品牌", agency: "代理品牌", oem: "OEM" };

interface BrandStats {
  total: number;
  recent_30d: number;
  eol_nrnd_count: number;
  automotive_count: number;
  high_risk_count: number;
  by_status: { status: string; count: number }[];
  by_level: { level: string; count: number }[];
  by_type: { type: string; count: number }[];
  by_lifecycle: { stage: string; count: number }[];
  by_authorization: { status: string; count: number }[];
  by_category: { category: string; count: number }[];
  by_risk: { level: string; count: number }[];
  top_risk_brands: { id: number; name: string; risk_score: number; risk_level: string; lifecycle_stage: string }[];
}

interface EolAlert {
  brand_id: number;
  brand_name: string;
  lifecycle_stage: string;
  stage_label: string;
  severity: string;
  affected_products: number;
  sales_exposure: number;
  alternative_brands: string[];
  recommended_action: string;
}

const COLORS = ["#1890ff", "#52c41a", "#faad14", "#f5222d", "#722ed1", "#13c2c2", "#eb2f96"];

export default function BrandDashboard() {
  const [stats, setStats] = useState<BrandStats | null>(null);
  const [eolAlerts, setEolAlerts] = useState<EolAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchStats = async () => {
    setLoading(true);
    try {
      const api = await import("../../api");
      const [statsResp, alertsResp] = await Promise.all([
        api.getBrandStats(),
        api.getEolAlerts("warning").catch(() => ({ data: { data: { alerts: [], total_alerts: 0, critical_count: 0, warning_count: 0 } } })),
      ]);
      setStats(statsResp.data.data as unknown as BrandStats);
      const alertsData = alertsResp.data?.data as unknown as { alerts?: EolAlert[]; total_alerts?: number; critical_count?: number; warning_count?: number } | null;
      if (alertsData?.alerts) {
        setEolAlerts(alertsData.alerts.slice(0, 10));
      }
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStats(); }, []);

  if (loading) return <Spin size="large" style={{ display: "block", marginTop: 100 }} />;
  if (!stats) return <Text type="secondary">无法加载品牌统计数据</Text>;

  const s = stats;
  const authorizedCount = s.by_authorization.find(a => a.status === "authorized")?.count ?? 0;
  const highRiskRate = s.total > 0 ? Math.round((s.high_risk_count / s.total) * 100) : 0;
  const eolRate = s.total > 0 ? Math.round((s.eol_nrnd_count / s.total) * 100) : 0;
  const automotiveRate = s.total > 0 ? Math.round((s.automotive_count / s.total) * 100) : 0;

  const riskColumns = [
    { title: "排名", key: "rank", width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    {
      title: "品牌", key: "name", render: (_: unknown, r: { id: number; name: string }) => (
        <a onClick={() => navigate(`/brands/${r.id}`)}>{r.name}</a>
      ),
    },
    {
      title: "风险评分", dataIndex: "risk_score", key: "risk_score", width: 100,
      render: (v: number) => <Progress percent={v} size="small" status={v > 70 ? "exception" : v > 40 ? "normal" : "success"} />,
    },
    {
      title: "风险等级", dataIndex: "risk_level", key: "risk_level", width: 80,
      render: (v: string) => v ? <Tag color={RISK_COLORS[v] || "default"}>{RISK_LABELS[v] || v}</Tag> : "-",
    },
    {
      title: "生命周期", dataIndex: "lifecycle_stage", key: "lifecycle_stage", width: 80,
      render: (v: string) => v ? <Tag color={LC_COLORS[v] || "default"}>{LC_LABELS[v] || v.toUpperCase()}</Tag> : "-",
    },
    {
      title: "操作", key: "action", width: 70,
      render: (_: unknown, r: { id: number }) => (
        <Button size="small" icon={<RightOutlined />} onClick={() => navigate(`/brands/${r.id}`)} />
      ),
    },
  ];

  return (
    <div>
      <style>{`
        .brand-dashboard-head {
          margin-bottom: 16px;
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          align-items: flex-start;
          justify-content: space-between;
        }
        .brand-dashboard-title {
          min-width: 260px;
          flex: 1 1 360px;
        }
        .brand-dashboard-title h4 {
          margin-bottom: 4px;
        }
        .brand-dashboard-actions {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          justify-content: flex-end;
        }
        .brand-health-strip {
          margin-bottom: 16px;
          padding: 12px;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .brand-health-strip .ant-tag {
          margin-inline-end: 4px;
        }
        .brand-kpi-card {
          height: 100%;
          cursor: pointer;
          transition: border-color .16s ease, box-shadow .16s ease, transform .16s ease;
        }
        .brand-kpi-card:hover {
          border-color: #91caff;
          box-shadow: 0 2px 8px rgba(22, 119, 255, .12);
          transform: translateY(-1px);
        }
        .brand-chart-card,
        .brand-table-card {
          height: 100%;
        }
        .brand-chart-card .ant-card-head-title,
        .brand-table-card .ant-card-head-title {
          font-size: 14px;
        }
        .brand-dashboard-empty {
          padding: 20px 8px;
          text-align: center;
        }
        @media (max-width: 768px) {
          .brand-dashboard-actions {
            width: 100%;
            justify-content: flex-start;
          }
        }
      `}</style>

      <div className="brand-dashboard-head">
        <div className="brand-dashboard-title">
          <Title level={4}>
            <BankOutlined style={{ marginRight: 8 }} />
            品牌总览
          </Title>
          <Text type="secondary">跟踪品牌覆盖、生命周期风险、授权结构和重点复核对象</Text>
        </div>
        <div className="brand-dashboard-actions">
          <Button icon={<ReloadOutlined />} loading={loading} onClick={fetchStats}>刷新</Button>
          <Button onClick={() => navigate("/brands?scene=high_risk")}>高风险</Button>
          <Button onClick={() => navigate("/brands?scene=eol_nrnd")}>EOL/NRND</Button>
          <Button type="primary" onClick={() => navigate("/brands")}>全部品牌</Button>
        </div>
      </div>

      <div className="brand-health-strip">
        <Space wrap size={8}>
          <Text strong>当前品牌健康</Text>
          <Tag color={highRiskRate > 20 ? "red" : highRiskRate > 10 ? "orange" : "green"}>高风险占比 {highRiskRate}%</Tag>
          <Tag color={eolRate > 10 ? "red" : eolRate > 0 ? "orange" : "green"}>EOL/NRND {eolRate}%</Tag>
          <Tag color="blue">车规覆盖 {automotiveRate}%</Tag>
          <Tag color="geekblue">已授权 {authorizedCount}</Tag>
        </Space>
      </div>

      {/* EOL Alerts Banner */}
      {s.eol_nrnd_count > 0 && (
        <Alert
          type="warning"
          icon={<AlertOutlined />}
          message={`发现 ${s.eol_nrnd_count} 个 EOL/NRND 品牌风险`}
          description="以下品牌已停产或不推荐新设计，请及时评估替代方案"
          style={{ marginBottom: 16 }}
          action={<Button size="small" onClick={() => navigate("/brands?lifecycle_stage=eol")}>查看全部</Button>}
        />
      )}

      {/* KPI Cards */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={8} xl={4}>
          <Card className="brand-kpi-card" onClick={() => navigate("/brands")}><Statistic title="品牌总数" value={s.total} prefix={<BankOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={8} xl={4}>
          <Card className="brand-kpi-card" onClick={() => navigate("/brands?sort=created_at_desc")}><Statistic title="近30天新增" value={s.recent_30d} prefix={<RiseOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={8} xl={4}>
          <Card className="brand-kpi-card" onClick={() => navigate("/brands?scene=eol_nrnd")}>
            <Statistic
              title="EOL/NRND 风险"
              value={s.eol_nrnd_count}
              prefix={<AlertOutlined />}
              valueStyle={{ color: s.eol_nrnd_count > 0 ? "#f5222d" : undefined }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} xl={4}>
          <Card className="brand-kpi-card" onClick={() => navigate("/brands?scene=automotive")}><Statistic title="车规品牌" value={s.automotive_count} prefix={<CarOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={8} xl={4}>
          <Card className="brand-kpi-card" onClick={() => navigate("/brands?scene=high_risk")}>
            <Statistic
              title="高风险品牌 (>70)"
              value={s.high_risk_count}
              prefix={<WarningOutlined />}
              valueStyle={{ color: s.high_risk_count > 0 ? "#f5222d" : undefined }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} xl={4}>
          <Card className="brand-kpi-card" onClick={() => navigate("/brands")}>
            <Statistic
              title="已授权品牌"
              value={authorizedCount}
              prefix={<PieChartOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={12} xl={6}>
          <Card className="brand-chart-card" title="品牌状态分布" size="small" extra={<Text type="secondary">{s.by_status.reduce((sum, item) => sum + item.count, 0)} 个</Text>}>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={s.by_status} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={60}
                  label={({ status, count }) => `${STATUS_LABELS[status] || status}: ${count}`}
                >
                  {s.by_status.map((entry) => (
                    <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || "#999"} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="brand-chart-card" title="等级分布" size="small">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={s.by_level} dataKey="count" nameKey="level" cx="50%" cy="50%" outerRadius={60}
                  label={({ level, count }) => `${level}级: ${count}`}
                >
                  {s.by_level.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="brand-chart-card" title="生命周期分布" size="small" extra={s.eol_nrnd_count > 0 ? <Tag color="orange">{s.eol_nrnd_count} 风险</Tag> : <Tag color="green">正常</Tag>}>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={s.by_lifecycle}>
                <XAxis dataKey="stage" fontSize={11} tickFormatter={(value) => LC_LABELS[value] || value} />
                <YAxis fontSize={11} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {s.by_lifecycle.map((entry) => (
                    <Cell key={entry.stage} fill={LC_COLORS[entry.stage] || "#1890ff"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="brand-chart-card" title="风险等级分布" size="small" extra={s.high_risk_count > 0 ? <Tag color="red">{s.high_risk_count} 高风险</Tag> : <Tag color="green">低风险</Tag>}>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={s.by_risk} dataKey="count" nameKey="level" cx="50%" cy="50%" outerRadius={60}
                  label={({ level, count }) => `${RISK_LABELS[level] || level}: ${count}`}
                >
                  {s.by_risk.map((entry) => (
                    <Cell key={entry.level} fill={RISK_COLORS[entry.level] || "#999"} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Top Risk Brands + EOL Alerts */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={14}>
          <Card className="brand-table-card" title="TOP 风险品牌" size="small" extra={<Button size="small" onClick={() => navigate("/brands?scene=high_risk")}>查看全部</Button>}>
            {s.top_risk_brands.length > 0 ? (
              <Table rowKey="id" columns={riskColumns} dataSource={s.top_risk_brands} size="small" pagination={false} scroll={{ x: 560 }} />
            ) : (
              <div className="brand-dashboard-empty"><Text type="secondary">暂无高风险品牌</Text></div>
            )}
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card className="brand-table-card" title="EOL / NRND 风险品牌" size="small" extra={<Button size="small" onClick={() => navigate("/brands?scene=eol_nrnd")}>处理风险</Button>}>
            {eolAlerts.length > 0 ? (
              <List
                size="small"
                dataSource={eolAlerts}
                renderItem={(item: EolAlert) => (
                  <List.Item style={{ padding: "4px 0" }}>
                    <List.Item.Meta
                      avatar={<Tag color={item.severity === "critical" ? "red" : "orange"}>{item.lifecycle_stage.toUpperCase()}</Tag>}
                      title={<a onClick={() => navigate(`/brands/${item.brand_id}`)}>{item.brand_name}</a>}
                      description={
                        <span style={{ fontSize: 12 }}>
                          影响 {item.affected_products} 个产品 | 销售暴露 ¥{item.sales_exposure.toLocaleString()}
                          {item.alternative_brands.length > 0 && <span> | 替代: {item.alternative_brands.slice(0, 2).join(", ")}</span>}
                        </span>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <div className="brand-dashboard-empty"><Text type="secondary">暂无 EOL/NRND 风险</Text></div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Category Distribution */}
      <Row gutter={[12, 12]}>
        <Col xs={24} xl={12}>
          <Card className="brand-table-card" title="品牌分类分布 (TOP 10)" size="small">
            <Table
              rowKey="category"
              dataSource={s.by_category.slice(0, 10)}
              size="small"
              pagination={false}
              columns={[
                { title: "分类", dataIndex: "category", key: "category" },
                { title: "品牌数", dataIndex: "count", key: "count", width: 80 },
                {
                  title: "占比",
                  key: "pct",
                  width: 80,
                  render: (_: unknown, r: { count: number }) => `${s.total > 0 ? (r.count / s.total * 100).toFixed(1) : 0}%`,
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card className="brand-chart-card" title="品牌类型分布" size="small">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={s.by_type}>
                <XAxis dataKey="type" fontSize={11} tickFormatter={(value) => TYPE_LABELS[value] || value} />
                <YAxis fontSize={11} />
                <Tooltip />
                <Bar dataKey="count" fill="#1890ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
