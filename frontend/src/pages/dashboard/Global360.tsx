import { useEffect, useState } from "react";
import { Card, Col, Progress, Row, Statistic, Table, Tag, Typography, Spin, Alert, List } from "antd";
import { PieChartOutlined, RiseOutlined, AimOutlined, WarningOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { orchestrateGlobal360 } from "../../api";
import type { Global360 as Global360Type } from "../../types";

const { Title, Text } = Typography;

export default function Global360Page() {
  const [data, setData] = useState<Global360Type | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    orchestrateGlobal360()
      .then((r) => setData(r.data.data))
      .catch(() => setError("AI 分析失败，请稍后重试"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} style={{ margin: 24 }} />;
  if (!data) return null;

  const scoreColor = (data.enterprise_health_score ?? 0) >= 80 ? "#52c41a" : (data.enterprise_health_score ?? 0) >= 60 ? "#faad14" : "#ff4d4f";

  const opportunityColumns = [
    { title: "领域", dataIndex: "area", width: 80, render: (a: string) => <Tag>{a}</Tag> },
    { title: "描述", dataIndex: "description", ellipsis: true },
    { title: "潜在价值", dataIndex: "potential_value", width: 100, render: (v: number) => v ? `¥${v.toLocaleString()}` : "-" },
    { title: "时间范围", dataIndex: "timeframe", width: 100, render: (t: string) => t || "-" },
  ];

  const riskColumns = [
    { title: "领域", dataIndex: "area", width: 80, render: (a: string) => <Tag>{a}</Tag> },
    { title: "描述", dataIndex: "description", ellipsis: true },
    { title: "严重程度", dataIndex: "severity", width: 80, render: (s: string) => <Tag color={s === "高" ? "red" : s === "中" ? "orange" : "blue"}>{s}</Tag> },
    { title: "缓解措施", dataIndex: "mitigation", width: 120, ellipsis: true },
  ];

  const kpiColumns = [
    { title: "KPI", dataIndex: "kpi", width: 120 },
    { title: "当前值", dataIndex: "current", width: 100 },
    { title: "目标值", dataIndex: "target", width: 100 },
    { title: "状态", dataIndex: "status", width: 80, render: (s: string) => <Tag color={s === "达标" ? "green" : s === "低于" ? "red" : "orange"}>{s}</Tag> },
  ];

  const recoColumns = [
    { title: "领域", dataIndex: "domain", width: 80, render: (d: string) => <Tag>{d}</Tag> },
    { title: "建议", dataIndex: "recommendation", ellipsis: true },
    { title: "优先级", dataIndex: "priority", width: 80, render: (p: string) => <Tag color={p === "高" ? "red" : p === "中" ? "orange" : "blue"}>{p}</Tag> },
    { title: "理由", dataIndex: "rationale", ellipsis: true },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}><PieChartOutlined /> AI 全局企业洞察</Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Progress type="circle" percent={data.enterprise_health_score} strokeColor={scoreColor} size={120} />
            <div style={{ textAlign: "center", marginTop: 8 }}>
              <Text strong>企业健康分</Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={18}>
          <Card title="执行摘要">
            <Text>{data.executive_summary}</Text>
            {data.focus_areas?.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <Text strong>重点关注领域: </Text>
                {data.focus_areas.map((f, i) => <Tag color="blue" key={i}>{f}</Tag>)}
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {data.kpi_health?.length > 0 && (
        <Card title="KPI 健康看板" style={{ marginBottom: 24 }}>
          <Table columns={kpiColumns} dataSource={data.kpi_health} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
        </Card>
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title={<><RiseOutlined /> 顶部机会</>}>
            <Table columns={opportunityColumns} dataSource={data.top_opportunities} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={<><WarningOutlined /> 顶部风险</>}>
            <Table columns={riskColumns} dataSource={data.top_risks} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title={<><ThunderboltOutlined /> 跨领域关联</>}>
            {data.cross_domain_correlations?.length > 0 ? (
              <List size="small" dataSource={data.cross_domain_correlations} renderItem={(item) => (
                <List.Item>
                  <Tag color="purple">{item.domains}</Tag>
                  <Text>{item.finding}</Text>
                  {item.significance && <Tag style={{ marginLeft: 8 }}>{item.significance}</Tag>}
                </List.Item>
              )} />
            ) : <Text type="secondary">暂无跨领域关联数据</Text>}
          </Card>
        </Col>
      </Row>

      <Card title="战略建议">
        <Table columns={recoColumns} dataSource={data.strategic_recommendations} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
      </Card>
    </div>
  );
}
