import { useEffect, useState } from "react";
import { Card, Col, Progress, Row, Statistic, Table, Tag, Typography, Spin, Alert, List } from "antd";
import { PieChartOutlined, RiseOutlined, AimOutlined, WarningOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { orchestrateGlobal360 } from "../../api";
import type { Global360 as Global360Type } from "../../types";
import { StatusTag } from "../../ui";

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

  // Backend response shape (new in 2026-06):
  //   { scanned_at, data: {raw aggregations}, insights: {ai insights},
  //     ai_available, last_error }
  const insights = data.insights ?? data as any;
  const raw = data.data;

  const scoreColor = (insights.enterprise_health_score ?? 0) >= 80 ? "#52c41a" : (insights.enterprise_health_score ?? 0) >= 60 ? "#faad14" : "#ff4d4f";

  const oportunidadColumns = [
    { title: "领域", dataIndex: "area", width: 80, render: (a: string) => <Tag>{a}</Tag> },
    { title: "描述", dataIndex: "description", ellipsis: true },
    { title: "潜在价值", dataIndex: "potential_value", width: 100, render: (v: number) => v ? `¥${v.toLocaleString()}` : "-" },
    { title: "时间范围", dataIndex: "timeframe", width: 100, render: (t: string) => t || "-" },
  ];

  const riskColumns = [
    { title: "领域", dataIndex: "area", width: 80, render: (a: string) => <Tag>{a}</Tag> },
    { title: "描述", dataIndex: "description", ellipsis: true },
    { title: "严重程度", dataIndex: "severity", width: 80, render: (s: string) => <StatusTag status={s} tone={s === "高" ? "danger" : s === "中" ? "warning" : "info"} /> },
    { title: "缓解措施", dataIndex: "mitigation", width: 120, ellipsis: true },
  ];

  const kpiColumns = [
    { title: "KPI", dataIndex: "kpi", width: 120 },
    { title: "当前值", dataIndex: "current", width: 100 },
    { title: "目标值", dataIndex: "target", width: 100 },
    { title: "状态", dataIndex: "status", width: 80, render: (s: string) => <StatusTag status={s} tone={s === "达标" ? "success" : s === "低于" ? "danger" : "warning"} /> },
  ];

  const recoColumns = [
    { title: "领域", dataIndex: "domain", width: 80, render: (d: string) => <Tag>{d}</Tag> },
    { title: "建议", dataIndex: "recommendation", ellipsis: true },
    { title: "优先级", dataIndex: "priority", width: 80, render: (p: string) => <StatusTag status={p} tone={p === "高" ? "danger" : p === "中" ? "warning" : "info"} /> },
    { title: "理由", dataIndex: "rationale", ellipsis: true },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}><PieChartOutlined /> AI 全局企业洞察</Title>

      {data.ai_available === false && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="AI 智能分析暂不可用 — 以下为基于实时业务数据的启发式分析"
          description={data.last_error ? `AI 报错：${data.last_error.slice(0, 200)}` : undefined}
        />
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Progress type="circle" percent={insights.enterprise_health_score} strokeColor={scoreColor} size={120} />
            <div style={{ textAlign: "center", marginTop: 8 }}>
              <Text strong>企业健康分</Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={18}>
          <Card title="执行摘要">
            <Text>{insights.executive_summary}</Text>
            {insights.focus_areas?.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <Text strong>重点关注领域: </Text>
                {insights.focus_areas.map((f: string, i: number) => <StatusTag status={f} tone="info" key={i} />)}
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {insights.kpi_health?.length > 0 && (
        <Card title="KPI 健康看板" style={{ marginBottom: 24 }}>
          <Table columns={kpiColumns} dataSource={insights.kpi_health} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
        </Card>
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title={<><RiseOutlined /> 顶部机会</>}>
            <Table columns={oportunidadColumns} dataSource={insights.top_opportunities} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={<><WarningOutlined /> 顶部风险</>}>
            <Table columns={riskColumns} dataSource={insights.top_risks} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title={<><ThunderboltOutlined /> 跨领域关联</>}>
            {insights.cross_domain_correlations?.length > 0 ? (
              <List size="small" dataSource={insights.cross_domain_correlations} renderItem={(item: any) => (
                <List.Item>
                  <StatusTag status={item.domains} tone="info" />
                  <Text>{item.finding}</Text>
                  {item.significance && <Tag style={{ marginLeft: 8 }}>{item.significance}</Tag>}
                </List.Item>
              )} />
            ) : <Text type="secondary">暂无跨领域关联数据</Text>}
          </Card>
        </Col>
      </Row>

      <Card title="战略建议">
        <Table columns={recoColumns} dataSource={insights.strategic_recommendations} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
      </Card>

      {raw && (
        <Card title="原始数据快照" style={{ marginTop: 24 }} size="small">
          <pre style={{ fontSize: 12, maxHeight: 320, overflow: "auto" }}>
            {JSON.stringify(raw, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  );
}
