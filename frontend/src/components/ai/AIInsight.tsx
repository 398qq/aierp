import { useEffect, useState } from "react";
import { Card, Descriptions, Spin, Tag, Typography, theme } from "antd";
import {
  PieChartOutlined,
  AlertOutlined,
  BulbOutlined,
} from "@ant-design/icons";
import { getRFMAnalysis, getChurnRisk, getFollowUpSuggestion } from "../../api";
import type { RFMAnalysis, ChurnRisk } from "../../types";

const { Text, Paragraph } = Typography;

interface Props {
  customerId: number;
}

function scoreColor(s: number) {
  if (s >= 4) return "green";
  if (s >= 3) return "blue";
  if (s >= 2) return "orange";
  return "red";
}

export default function AIInsight({ customerId }: Props) {
  const [rfm, setRfm] = useState<RFMAnalysis | null>(null);
  const [churn, setChurn] = useState<ChurnRisk | null>(null);
  const [suggestion, setSuggestion] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const { token } = theme.useToken();

  useEffect(() => {
    let cancelled = false;
    async function fetch() {
      try {
        const [rfmRes, churnRes, sugRes] = await Promise.all([
          getRFMAnalysis(customerId),
          getChurnRisk(customerId),
          getFollowUpSuggestion(customerId),
        ]);
        if (cancelled) return;
        setRfm(rfmRes.data.data as RFMAnalysis);
        setChurn(churnRes.data.data as ChurnRisk);
        setSuggestion(sugRes.data.data as Record<string, unknown>);
      } catch {
        // silently fail
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetch();
    return () => { cancelled = true; };
  }, [customerId]);

  if (loading) return <Spin />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {rfm && (
        <Card
          size="small"
          title={<><PieChartOutlined /> RFM 客户分析</>}
          style={{ borderLeft: `3px solid ${token.colorPrimary}` }}
        >
          <Descriptions column={3} size="small">
            <Descriptions.Item label="最近购买(R)">
              <Tag color={scoreColor(rfm.r_score)}>{rfm.r_score}/5</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="频率(F)">
              <Tag color={scoreColor(rfm.f_score)}>{rfm.f_score}/5</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="金额(M)">
              <Tag color={scoreColor(rfm.m_score)}>{rfm.m_score}/5</Tag>
            </Descriptions.Item>
          </Descriptions>
          <Tag color={rfm.tier === "流失风险" ? "red" : "blue"} style={{ marginTop: 8 }}>
            {rfm.tier}
          </Tag>
          <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
            {rfm.suggestion}
          </Paragraph>
        </Card>
      )}

      {churn && (
        <Card
          size="small"
          title={<><AlertOutlined /> 流失风险评估</>}
          style={{ borderLeft: `3px solid ${churn.risk_level === "高" ? "red" : "orange"}` }}
        >
          <Text strong style={{ fontSize: 24, color: churn.risk_score > 70 ? "red" : "inherit" }}>
            {churn.risk_score}%
          </Text>
          <Tag color={churn.risk_level === "高" ? "red" : churn.risk_level === "中" ? "orange" : "green"}>
            {churn.risk_level}风险
          </Tag>
          {churn.factors.map((f, i) => (
            <Tag key={i} style={{ marginTop: 4 }}>{f}</Tag>
          ))}
          <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
            {churn.recommendation}
          </Paragraph>
        </Card>
      )}

      {suggestion && (
        <Card
          size="small"
          title={<><BulbOutlined /> AI 跟进建议</>}
          style={{ borderLeft: `3px solid ${token.colorSuccess}` }}
        >
          {(suggestion.topic as string) && (
            <Paragraph strong>{suggestion.topic as string}</Paragraph>
          )}
          {(suggestion.recommended_products as string[])?.length > 0 && (
            <Paragraph type="secondary">
              推荐产品：{(suggestion.recommended_products as string[]).join("、")}
            </Paragraph>
          )}
          {(suggestion.risk_points as string[])?.length > 0 && (
            <Paragraph type="warning">
              风险提示：{(suggestion.risk_points as string[]).join("；")}
            </Paragraph>
          )}
        </Card>
      )}
    </div>
  );
}
