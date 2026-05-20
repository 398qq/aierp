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

  const riskColumns = [
    { title: "排名", key: "rank", width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    {
      title: "品牌", key: "name", render: (_: unknown, r: { id: number; name: string }) => (
        <a onClick={() => navigate(`/brands/${r.id}`)}>{r.name}</a>
      ),
    },
    {
      title: "风险评分", key: "risk_score", width: 100,
      render: (v: number) => <Progress percent={v} size="small" status={v > 70 ? "exception" : v > 40 ? "normal" : "success"} />,
    },
    {
      title: "风险等级", key: "risk_level", width: 80,
      render: (v: string) => v ? <Tag color={RISK_COLORS[v] || "default"}>{v === "low" ? "低" : v === "medium" ? "中" : v === "high" ? "高" : "严重"}</Tag> : "-",
    },
    {
      title: "生命周期", key: "lifecycle_stage", width: 80,
      render: (v: string) => v ? <Tag color={LC_COLORS[v] || "default"}>{v.toUpperCase()}</Tag> : "-",
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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <BankOutlined style={{ marginRight: 8 }} />
          品牌总览
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchStats}>刷新</Button>
          <Button type="primary" onClick={() => navigate("/brands")}>全部品牌</Button>
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
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card><Statistic title="品牌总数" value={s.total} prefix={<BankOutlined />} /></Card>
        </Col>
        <Col span={4}>
          <Card><Statistic title="近30天新增" value={s.recent_30d} prefix={<RiseOutlined />} /></Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="EOL/NRND 风险"
              value={s.eol_nrnd_count}
              prefix={<AlertOutlined />}
              valueStyle={{ color: s.eol_nrnd_count > 0 ? "#f5222d" : undefined }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card><Statistic title="车规品牌" value={s.automotive_count} prefix={<CarOutlined />} /></Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="高风险品牌 (>70)"
              value={s.high_risk_count}
              prefix={<WarningOutlined />}
              valueStyle={{ color: s.high_risk_count > 0 ? "#f5222d" : undefined }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="已授权品牌"
              value={s.by_authorization.find(a => a.status === "authorized")?.count ?? 0}
              prefix={<PieChartOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card title="品牌状态分布" size="small">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={s.by_status} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={60}
                  label={({ status, count }) => `${status === "active" ? "启用" : status === "inactive" ? "停用" : "冻结"}: ${count}`}
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
        <Col span={6}>
          <Card title="等级分布" size="small">
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
        <Col span={6}>
          <Card title="生命周期分布" size="small">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={s.by_lifecycle}>
                <XAxis dataKey="stage" fontSize={11} />
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
        <Col span={6}>
          <Card title="风险等级分布" size="small">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={s.by_risk} dataKey="count" nameKey="level" cx="50%" cy="50%" outerRadius={60}
                  label={({ level, count }) => `${level === "low" ? "低" : level === "medium" ? "中" : level === "high" ? "高" : "严重"}: ${count}`}
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
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={14}>
          <Card title="TOP 风险品牌" size="small">
            {s.top_risk_brands.length > 0 ? (
              <Table rowKey="id" columns={riskColumns} dataSource={s.top_risk_brands} size="small" pagination={false} />
            ) : (
              <Text type="secondary">暂无高风险品牌</Text>
            )}
          </Card>
        </Col>
        <Col span={10}>
          <Card title="EOL / NRND 风险品牌" size="small" style={{ background: "#fff2e8" }}>
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
              <Text type="secondary">暂无 EOL/NRND 风险</Text>
            )}
          </Card>
        </Col>
      </Row>

      {/* Category Distribution */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title="品牌分类分布 (TOP 10)" size="small">
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
        <Col span={12}>
          <Card title="品牌类型分布" size="small">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={s.by_type}>
                <XAxis dataKey="type" fontSize={11} />
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