import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Tag, Typography, Spin, Alert, Table, List, Button, Space } from "antd";
import { StatusTag } from "../../ui";
import { erpPagination } from "../../ui/pagination";
import { WarningOutlined, SafetyOutlined, AlertOutlined, ThunderboltOutlined, ReloadOutlined } from "@ant-design/icons";
import { getWatchtowerScan } from "../../api";

const { Title, Text, Paragraph } = Typography;

const domainIcons: Record<string, React.ReactNode> = {
  inventory: <AlertOutlined />,
  finance: <ThunderboltOutlined />,
  sales: <SafetyOutlined />,
  customer: <WarningOutlined />,
};

const domainLabels: Record<string, string> = {
  churn_risk: "客户流失风险",
  order_drop: "订单量下降",
  low_stock: "低库存",
  out_of_stock: "缺货",
};

const SCAN_LOOKBACK_DAYS = 90;
const severityColor = (s: string) => s === "紧急" ? "red" : s === "需关注" ? "orange" : "green";

const safeFormatDate = (d: string | undefined | null): string => {
  if (!d) return "未知时间";
  try {
    const date = new Date(d);
    if (isNaN(date.getTime())) return "无效时间";
    return date.toLocaleString();
  } catch {
    return "无效时间";
  }
};

export default function WatchtowerDashboard() {
  const [data, setData] = useState<{
    scanned_at: string;
    total_alerts: number;
    severity: string;
    summary: string;
    top_actions: string[];
    risk_areas: string[];
    anomalies: Record<string, Record<string, unknown>[]>;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = () => {
    setLoading(true);
    setError("");
    getWatchtowerScan(SCAN_LOOKBACK_DAYS)
      .then((r) => setData(r.data.data))
      .catch(() => setError("监控扫描失败，请稍后重试"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} style={{ margin: 24 }} action={<Button onClick={fetchData}>重试</Button>} />;
  if (!data) return null;

  const anomalyEntries = Object.entries(data.anomalies || {}).filter(([, v]) => v.length > 0);

  const allAnomalies = anomalyEntries.flatMap(([domain, items]) =>
    items.map((item: Record<string, unknown>) => ({
      domain,
      domainLabel: domainLabels[domain] || domain,
      ...item,
    }))
  );

  const anomalyColumns = [
    { title: "领域", dataIndex: "domainLabel", width: 100, render: (d: string) => <StatusTag>{d}</StatusTag> },
    { title: "名称", dataIndex: "name", ellipsis: true, render: (n: unknown) => n || "-" },
    { title: "详情", dataIndex: "signal", ellipsis: true, render: (s: unknown) => s || JSON.stringify(s) || "-" },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <WarningOutlined /> 全局监控中心
        </Title>
        <Space>
          <Text type="secondary">扫描时间: {safeFormatDate(data.scanned_at)}</Text>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
        </Space>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic title="异常总数" value={data.total_alerts} prefix={<AlertOutlined />} valueStyle={{ color: data.total_alerts > 0 ? "#ff4d4f" : "#52c41a" }} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic title="严重程度" value={data.severity} valueStyle={{ color: severityColor(data.severity) }} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card title="异常领域">
            {data.risk_areas?.length ? data.risk_areas.map((a, i) => <StatusTag tone="danger" key={i}>{a}</StatusTag>) : <StatusTag tone="success">无</StatusTag>}
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card title="领域分布">
            {anomalyEntries.length > 0 ? anomalyEntries.map(([domain, items]) => (
              <StatusTag key={domain} tone={items.length > 5 ? "danger" : "warning"}>
                {domainLabels[domain] || domain}: {items.length}
              </StatusTag>
            )) : <Text type="secondary">暂无异常</Text>}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title="AI 分析摘要"><Paragraph>{data.summary}</Paragraph></Card>
        </Col>
      </Row>

      {data.top_actions?.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col span={24}>
            <Card title="优先行动">
              <List size="small" dataSource={data.top_actions} renderItem={(item, i) => <List.Item>{i + 1}. {item}</List.Item>} />
            </Card>
          </Col>
        </Row>
      )}

      <Card title="异常详情" style={{ marginBottom: 24 }}>
        {allAnomalies.length > 0 ? (
          <Table columns={anomalyColumns} dataSource={allAnomalies} rowKey={(_r, i) => String(i)} pagination={erpPagination()} size="small" />
        ) : (
          <Text type="secondary" style={{ display: "block", textAlign: "center", padding: 40 }}>未检测到异常，系统运行正常</Text>
        )}
      </Card>
    </div>
  );
}
