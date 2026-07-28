import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, Col, Progress, Row, Statistic, Tag, Typography, Spin, Alert, Button } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { PieChartOutlined, RiseOutlined, SafetyOutlined, ShopOutlined, AimOutlined, WarningOutlined } from "@ant-design/icons";
import { orchestrateProduct360 } from "../../api";
import type { Product360 as Product360Type } from "../../types";

const { Title, Text } = Typography;

export default function Product360Page() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<Product360Type | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    orchestrateProduct360(Number(id))
      .then((r) => setData(r.data.data))
      .catch(() => setError("AI 分析失败，请稍后重试"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} style={{ margin: 24 }} />;
  if (!data) return null;

  const scoreColor = data.product_360_score >= 80 ? "#52c41a" : data.product_360_score >= 60 ? "#faad14" : "#ff4d4f";

  const actionColumns = [
    { title: "领域", dataIndex: "domain", width: 80, render: (d: string) => <StatusTag>{d}</StatusTag> },
    { title: "行动", dataIndex: "action", ellipsis: true },
    { title: "优先级", dataIndex: "priority", width: 80, render: (p: string) => <StatusTag tone={p === "高" ? "danger" : p === "中" ? "warning" : "info"}>{p}</StatusTag> },
    { title: "预期影响", dataIndex: "expected_impact", width: 100, ellipsis: true },
  ];

  const insightColumns = [
    { title: "领域", dataIndex: "domain", width: 80, render: (d: string) => <StatusTag>{d}</StatusTag> },
    { title: "发现", dataIndex: "finding", ellipsis: true },
    { title: "影响", dataIndex: "impact", width: 120, ellipsis: true },
    { title: "建议行动", dataIndex: "action", ellipsis: true },
  ];

  const growthColor = data.growth_potential === "高" ? "#52c41a" : data.growth_potential === "中" ? "#faad14" : "#ff4d4f";

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>
        <PieChartOutlined /> AI 360 产品洞察
        <Link to={`/products/${id}`}><Button type="link" style={{ float: "right" }}>返回产品详情</Button></Link>
      </Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Progress type="circle" percent={data.product_360_score} strokeColor={scoreColor} size={120} />
            <div style={{ textAlign: "center", marginTop: 8 }}>
              <Text strong>综合健康分</Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card><Statistic title="商业健康" value={data.commercial_health} prefix={<RiseOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card><Statistic title="供应健康" value={data.supply_health} prefix={<ShopOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card><Statistic title="质量健康" value={data.quality_health} prefix={<SafetyOutlined />} /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}><Card title="健康摘要"><Text>{data.health_summary}</Text></Card></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card title="增长潜力"><Statistic value={data.growth_potential} valueStyle={{ color: growthColor }} prefix={<AimOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card title="风险标志">
            {data.risk_flags?.length ? data.risk_flags.map((f, i) => <StatusTag tone="danger" key={i}>{f}</StatusTag>) : <Text type="secondary">无风险标志</Text>}
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card title="下一步最佳行动"><Text strong>{data.next_best_action}</Text></Card>
        </Col>
      </Row>

      <Card title="优先行动" style={{ marginBottom: 24 }}>
        <ProTable search={false} options={false} columns={actionColumns as any} dataSource={data.prioritized_actions} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
      </Card>

      <Card title="跨领域洞察">
        <ProTable search={false} options={false} columns={insightColumns as any} dataSource={data.cross_domain_insights} rowKey={(_r, i) => String(i)} pagination={false} size="small" />
      </Card>
    </div>
  );
}
