import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Descriptions, Card, Button, Space, Tag, Spin, Alert, Empty, Progress, Typography } from "antd";
import { ArrowLeftOutlined, EditOutlined, BulbOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { getOpportunity, getWinPrediction, getSalesRecommendation } from "../../api";
import type { Opportunity, WinPrediction, SalesRecommendation } from "../../types";

const { Text, Paragraph } = Typography;

const stageColors: Record<string, string> = {
  lead: "default", qualified: "blue", proposal: "orange", negotiation: "purple",
  won: "green", lost: "red",
};

export default function OpportunityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<WinPrediction | null>(null);
  const [recommendation, setRecommendation] = useState<SalesRecommendation | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getOpportunity(Number(id))
      .then((r) => {
        const opp = r.data.data as Opportunity;
        setData(opp);
        // Load AI predictions
        setAiLoading(true);
        Promise.all([
          getWinPrediction(opp.id).then((r) => setPrediction(r.data.data as WinPrediction)).catch(() => {}),
          getSalesRecommendation(opp.customer_id).then((r) => setRecommendation(r.data.data as SalesRecommendation)).catch(() => {}),
        ]).finally(() => setAiLoading(false));
      })
      .catch((e) => setError((e as Error).message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!data) return <Empty description="未找到该机会" />;

  const confidenceColor = prediction?.confidence === "high" ? "#52c41a" : prediction?.confidence === "medium" ? "#faad14" : "#ff4d4f";

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/opportunities")}>返回列表</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/opportunities/${data.id}/edit`)}>编辑</Button>
      </Space>
      <Card title={data.name}>
        <Descriptions column={2}>
          <Descriptions.Item label="客户ID">{data.customer_id}</Descriptions.Item>
          <Descriptions.Item label="阶段"><Tag color={stageColors[data.stage] || "default"}>{data.stage}</Tag></Descriptions.Item>
          <Descriptions.Item label="金额">¥{data.amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="概率">{data.probability}%</Descriptions.Item>
          <Descriptions.Item label="预计成交日期">{data.expected_close_date || "-"}</Descriptions.Item>
          <Descriptions.Item label="实际成交日期">{data.actual_close_date || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{data.notes || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{data.created_at}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Space direction="vertical" size="middle" style={{ width: "100%", marginTop: 16 }}>
        {aiLoading ? (
          <Card><Spin tip="AI 分析中..." /></Card>
        ) : (
          <>
            {prediction && (
              <Card
                title={<span><ThunderboltOutlined /> 成交预测</span>}
                size="small"
              >
                <div style={{ display: "flex", alignItems: "center", gap: 24, marginBottom: 12 }}>
                  <Progress
                    type="circle"
                    percent={prediction.win_probability}
                    size={80}
                    strokeColor={prediction.win_probability >= 70 ? "#52c41a" : prediction.win_probability >= 40 ? "#faad14" : "#ff4d4f"}
                  />
                  <div>
                    <Text strong>置信度：</Text>
                    <Tag color={confidenceColor}>{prediction.confidence}</Tag>
                  </div>
                </div>
                <Paragraph>
                  <Text strong>关键因素：</Text>
                  {prediction.key_factors.map((f, i) => <Tag key={i}>{f}</Tag>)}
                </Paragraph>
                <Paragraph type="secondary">{prediction.recommendation}</Paragraph>
              </Card>
            )}

            {recommendation && (
              <Card
                title={<span><BulbOutlined /> 销售建议</span>}
                size="small"
              >
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="推荐产品">{recommendation.recommended_products?.join("、") || "-"}</Descriptions.Item>
                  <Descriptions.Item label="商机建议">{recommendation.opportunity_suggestion || "-"}</Descriptions.Item>
                  <Descriptions.Item label="交叉销售">{recommendation.cross_sell_opportunities || "-"}</Descriptions.Item>
                  <Descriptions.Item label="优先行动">
                    <Tag color="red">{recommendation.priority_action || "-"}</Tag>
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            )}
          </>
        )}
      </Space>
    </div>
  );
}
