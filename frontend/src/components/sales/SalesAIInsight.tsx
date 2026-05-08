import { Card, Descriptions, Tag, Progress, Typography, List } from "antd";
import { SafetyOutlined, RiseOutlined, AlertOutlined } from "@ant-design/icons";
import type { OpportunityAI, QuotationAI, SalesOrderAI, DeliveryNoteAI } from "../../types";

const { Text } = Typography;

interface Props {
  aiData: OpportunityAI | QuotationAI | SalesOrderAI | DeliveryNoteAI | null | undefined;
  loading?: boolean;
}

const RISK_COLOR: Record<string, string> = { low: "green", medium: "orange", high: "red" };
const RISK_LABEL: Record<string, string> = { low: "低", medium: "中", high: "高" };
const HEALTH_COLOR = (s: number) => (s >= 80 ? "#52c41a" : s >= 60 ? "#faad14" : "#ff4d4f");

export default function SalesAIInsight({ aiData, loading }: Props) {
  if (loading) return <Card size="small" title="AI 分析" loading />;
  if (!aiData) return <Card size="small" title="AI 分析"><Text type="secondary">AI 不可用</Text></Card>;

  return (
    <Card size="small" title={<><RiseOutlined /> AI 洞察</>} style={{ marginTop: 16 }}>
      {"risk_level" in aiData && (
        <Descriptions column={2} size="small">
          <Descriptions.Item label="风险等级">
            <Tag color={RISK_COLOR[(aiData as OpportunityAI).risk_level]}>{(aiData as OpportunityAI).risk_level}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="赢单概率">
            <Progress percent={(aiData as OpportunityAI).win_probability} size="small" style={{ width: 120 }} />
          </Descriptions.Item>
          {(aiData as OpportunityAI).next_best_action && (
            <Descriptions.Item label="下一步" span={2}>{(aiData as OpportunityAI).next_best_action}</Descriptions.Item>
          )}
          {(aiData as OpportunityAI).key_concerns.length > 0 && (
            <Descriptions.Item label="关注点" span={2}>
              {(aiData as OpportunityAI).key_concerns.map((c, i) => <Tag key={i} color="orange">{c}</Tag>)}
            </Descriptions.Item>
          )}
        </Descriptions>
      )}

      {"pricing_health" in aiData && (
        <Descriptions column={2} size="small">
          <Descriptions.Item label="定价健康度">
            <Tag color={RISK_COLOR[(aiData as QuotationAI).pricing_health === "good" ? "low" : (aiData as QuotationAI).pricing_health === "fair" ? "medium" : "high"]}>
              {(aiData as QuotationAI).pricing_health}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="赢单概率">
            <Progress percent={(aiData as QuotationAI).win_probability} size="small" style={{ width: 120 }} />
          </Descriptions.Item>
          {(aiData as QuotationAI).margin_assessment && (
            <Descriptions.Item label="利润评估" span={2}>{(aiData as QuotationAI).margin_assessment}</Descriptions.Item>
          )}
          {(aiData as QuotationAI).improvement_suggestions.length > 0 && (
            <Descriptions.Item label="改进建议" span={2}>
              <List size="small" dataSource={(aiData as QuotationAI).improvement_suggestions} renderItem={(s: string) => <List.Item>{s}</List.Item>} />
            </Descriptions.Item>
          )}
        </Descriptions>
      )}

      {"delivery_risk" in aiData && "health_score" in aiData && (
        <Descriptions column={2} size="small">
          <Descriptions.Item label="健康分">
            <Progress percent={(aiData as SalesOrderAI).health_score} size="small" strokeColor={HEALTH_COLOR((aiData as SalesOrderAI).health_score)} style={{ width: 120 }} />
          </Descriptions.Item>
          <Descriptions.Item label="交货风险">
            <Tag color={RISK_COLOR[(aiData as SalesOrderAI).delivery_risk]}>{RISK_LABEL[(aiData as SalesOrderAI).delivery_risk]}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="回款风险">
            <Tag color={RISK_COLOR[(aiData as SalesOrderAI).payment_risk]}>{RISK_LABEL[(aiData as SalesOrderAI).payment_risk]}</Tag>
          </Descriptions.Item>
          {(aiData as SalesOrderAI).flags.length > 0 && (
            <Descriptions.Item label="标记" span={2}>
              {(aiData as SalesOrderAI).flags.map((f, i) => <Tag key={i} color="orange">{f}</Tag>)}
            </Descriptions.Item>
          )}
        </Descriptions>
      )}

      {"completion_risk" in aiData && !("health_score" in aiData) && (
        <Descriptions column={2} size="small">
          <Descriptions.Item label="完成风险">
            <Tag color={RISK_COLOR[(aiData as DeliveryNoteAI).completion_risk]}>{RISK_LABEL[(aiData as DeliveryNoteAI).completion_risk]}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="签收延迟概率">
            <Progress percent={(aiData as DeliveryNoteAI).signing_delay_probability} size="small" style={{ width: 120 }} />
          </Descriptions.Item>
          {(aiData as DeliveryNoteAI).issues.length > 0 && (
            <Descriptions.Item label="问题" span={2}>
              {(aiData as DeliveryNoteAI).issues.map((iss, i) => <Tag key={i} color="red">{iss}</Tag>)}
            </Descriptions.Item>
          )}
        </Descriptions>
      )}
    </Card>
  );
}
