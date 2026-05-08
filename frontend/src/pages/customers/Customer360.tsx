import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, Col, Progress, Row, Statistic, Table, Tag, Typography, Spin, Alert, Button } from "antd";
import { PieChartOutlined, RiseOutlined, SafetyOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { getCustomer360 } from "../../api";
import type { Customer360 as Customer360Type } from "../../types";

const { Title, Text } = Typography;

export default function Customer360Page() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<Customer360Type | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getCustomer360(Number(id))
      .then((r) => setData(r.data.data))
      .catch(() => setError("AI 分析失败，请稍后重试"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} style={{ margin: 24 }} />;
  if (!data) return null;

  const scoreColor = data.customer_360_score >= 80 ? "#52c41a" : data.customer_360_score >= 60 ? "#faad14" : "#ff4d4f";

  const actionColumns = [
    { title: "领域", dataIndex: "domain", width: 80, render: (d: string) => <Tag>{d}</Tag> },
    { title: "行动", dataIndex: "action", ellipsis: true },
    { title: "优先级", dataIndex: "priority", width: 80, render: (p: string) => <Tag color={p === "高" ? "red" : p === "中" ? "orange" : "blue"}>{p}</Tag> },
    { title: "预期影响", dataIndex: "expected_impact", width: 100, ellipsis: true },
  ];

  const insightColumns = [
    { title: "领域", dataIndex: "domain", width: 80, render: (d: string) => <Tag>{d}</Tag> },
    { title: "发现", dataIndex: "finding", ellipsis: true },
    { title: "影响", dataIndex: "impact", width: 120, ellipsis: true },
    { title: "建议行动", dataIndex: "action", ellipsis: true },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>
        <PieChartOutlined /> AI 360 客户洞察
        <Link to={`/customers/${id}`}><Button type="link" style={{ float: "right" }}>返回客户详情</Button></Link>
      </Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Progress type="circle" percent={data.customer_360_score} strokeColor={scoreColor} size={120} />
            <div style={{ textAlign: "center", marginTop: 8 }}>
              <Text strong>综合健康分</Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card><Statistic title="收入健康" value={data.revenue_health} prefix={<RiseOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card><Statistic title="关系健康" value={data.relationship_health} prefix={<ThunderboltOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card><Statistic title="风险健康" value={data.risk_health} prefix={<SafetyOutlined />} /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}><Card title="健康摘要"><Text>{data.health_summary}</Text></Card></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card title="机会评分"><Statistic value={data.opportunity_score} suffix="/ 100" /></Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card title="风险评分"><Statistic value={data.risk_score} suffix="/ 100" valueStyle={{ color: data.risk_score > 50 ? "#ff4d4f" : "#52c41a" }} /></Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card title="下一步最佳行动"><Text strong>{data.next_best_action}</Text></Card>
        </Col>
      </Row>

      <Card title="优先行动" style={{ marginBottom: 24 }}>
        <Table columns={actionColumns} dataSource={data.prioritized_actions} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
      </Card>

      <Card title="跨领域洞察">
        <Table columns={insightColumns} dataSource={data.cross_domain_insights} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
      </Card>
    </div>
  );
}
