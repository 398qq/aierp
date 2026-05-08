import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, Col, Progress, Row, Statistic, Table, Tag, Typography, Spin, Alert, Button, List } from "antd";
import { PieChartOutlined, TrophyOutlined, CheckCircleOutlined, CloseCircleOutlined, FileTextOutlined } from "@ant-design/icons";
import { getSupplier360 } from "../../api";
import type { Supplier360 as Supplier360Type } from "../../types";

const { Title, Text } = Typography;

export default function Supplier360Page() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<Supplier360Type | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getSupplier360(Number(id))
      .then((r) => setData(r.data.data))
      .catch(() => setError("AI 分析失败，请稍后重试"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} style={{ margin: 24 }} />;
  if (!data) return null;

  const scoreColor = data.overall_score >= 80 ? "#52c41a" : data.overall_score >= 60 ? "#faad14" : "#ff4d4f";
  const tierColor = data.tier === "A" ? "#52c41a" : data.tier === "B" ? "#1677ff" : data.tier === "C" ? "#faad14" : "#ff4d4f";

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>
        <PieChartOutlined /> AI 360 供应商洞察
        <Link to={`/suppliers/${id}`}><Button type="link" style={{ float: "right" }}>返回供应商详情</Button></Link>
      </Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Progress type="circle" percent={data.overall_score} strokeColor={scoreColor} size={120} />
            <div style={{ textAlign: "center", marginTop: 8 }}>
              <Text strong>综合评分</Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card><Statistic title="供应商等级" value={data.tier} valueStyle={{ color: tierColor, fontSize: 28 }} prefix={<TrophyOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic title="PO数量" value={data.po_history_summary?.total_pos || 0} prefix={<FileTextOutlined />} />
            <Text type="secondary">总金额 ¥{(data.po_history_summary?.total_amount || 0).toLocaleString()}</Text>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic title="准时交付率" value={data.po_history_summary?.on_time_rate != null ? `${(data.po_history_summary.on_time_rate * 100).toFixed(0)}%` : "无数据"} />
            <Text type="secondary">平均 {(data.po_history_summary?.avg_delivery_days || 0).toFixed(0)} 天交货</Text>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="综合评估"><Text>{data.assessment}</Text></Card>
        </Col>
        <Col span={12}>
          <Card title="分析摘要"><Text>{data.summary}</Text></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title={<><CheckCircleOutlined style={{ color: "#52c41a" }} /> 关键优势</>}>
            <List size="small" dataSource={data.key_strengths} renderItem={(item) => <List.Item>{item}</List.Item>} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={<><CloseCircleOutlined style={{ color: "#ff4d4f" }} /> 关键劣势</>}>
            <List size="small" dataSource={data.key_weaknesses} renderItem={(item) => <List.Item>{item}</List.Item>} />
          </Card>
        </Col>
      </Row>

      <Card title="改进建议">
        <List size="small" dataSource={data.recommendations} renderItem={(item, i) => <List.Item>{i + 1}. {item}</List.Item>} />
      </Card>
    </div>
  );
}
