import { Card, Tag, Progress, Typography } from "antd";
import { RiseOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";
import type { OpportunityAI, QuotationAI, SalesOrderAI, DeliveryNoteAI } from "../../types";
import "./SalesAIInsight.css";

const { Text } = Typography;

interface Props {
  aiData: OpportunityAI | QuotationAI | SalesOrderAI | DeliveryNoteAI | null | undefined;
  loading?: boolean;
}

const RISK_COLOR: Record<string, string> = { low: "green", medium: "orange", high: "red" };
const RISK_LABEL: Record<string, string> = { low: "低", medium: "中", high: "高" };
const HEALTH_COLOR = (s: number) => (s >= 80 ? "#52c41a" : s >= 60 ? "#faad14" : "#ff4d4f");

function InsightTagSection({ label, values, color }: { label: string; values: string[]; color: string }) {
  if (values.length === 0) return null;
  return (
    <div className="sales-ai-insight-tag-section">
      <Text type="secondary" className="sales-ai-insight-tag-label">{label}</Text>
      <div className="sales-ai-insight-tags">
        {values.map((value, index) => <Tag key={index} color={color}>{value}</Tag>)}
      </div>
    </div>
  );
}

function InsightTextSection({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="sales-ai-insight-text-section">
      <Text type="secondary" className="sales-ai-insight-section-label">{label}</Text>
      <div className="sales-ai-insight-text-value">{children}</div>
    </div>
  );
}

function InsightListSection({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null;
  return (
    <InsightTextSection label={label}>
      <ul className="sales-ai-insight-list">
        {values.map((value, index) => <li key={index}>{value}</li>)}
      </ul>
    </InsightTextSection>
  );
}

export default function SalesAIInsight({ aiData, loading }: Props) {
  if (loading) return <Card size="small" title="AI 分析" loading />;
  if (!aiData) return <Card size="small" title="AI 分析"><Text type="secondary">AI 不可用</Text></Card>;

  return (
    <Card
      size="small"
      title={<><RiseOutlined /> AI 洞察</>}
      extra={"fallback" in aiData && aiData.fallback ? <Tag color="gold">规则降级</Tag> : null}
      style={{ marginTop: 16 }}
      className="sales-ai-insight"
    >
      {"risk_level" in aiData && (
        <>
          <div className="sales-ai-insight-metrics sales-ai-insight-metrics--two">
            <div className="sales-ai-insight-metric">
              <Text type="secondary" className="sales-ai-insight-metric-label">风险等级</Text>
              <Tag color={RISK_COLOR[(aiData as OpportunityAI).risk_level]}>{(aiData as OpportunityAI).risk_level}</Tag>
            </div>
            <div className="sales-ai-insight-metric">
              <Text type="secondary" className="sales-ai-insight-metric-label">赢单概率</Text>
              <Progress percent={(aiData as OpportunityAI).win_probability} size="small" />
            </div>
          </div>
          {(aiData as OpportunityAI).next_best_action && <InsightTextSection label="下一步">{(aiData as OpportunityAI).next_best_action}</InsightTextSection>}
          <InsightTagSection label="关注点" values={(aiData as OpportunityAI).key_concerns} color="orange" />
        </>
      )}

      {"pricing_health" in aiData && (
        <>
          <div className="sales-ai-insight-metrics sales-ai-insight-metrics--two">
            <div className="sales-ai-insight-metric">
              <Text type="secondary" className="sales-ai-insight-metric-label">定价健康度</Text>
              <Tag color={RISK_COLOR[(aiData as QuotationAI).pricing_health === "good" ? "low" : (aiData as QuotationAI).pricing_health === "fair" ? "medium" : "high"]}>
                {(aiData as QuotationAI).pricing_health}
              </Tag>
            </div>
            <div className="sales-ai-insight-metric">
              <Text type="secondary" className="sales-ai-insight-metric-label">赢单概率</Text>
              <Progress percent={(aiData as QuotationAI).win_probability} size="small" />
            </div>
          </div>
          {(aiData as QuotationAI).margin_assessment && <InsightTextSection label="利润评估">{(aiData as QuotationAI).margin_assessment}</InsightTextSection>}
          <InsightListSection label="改进建议" values={(aiData as QuotationAI).improvement_suggestions} />
        </>
      )}

      {"delivery_risk" in aiData && "health_score" in aiData && (
        <>
          <div className="sales-ai-insight-metrics">
            <div className="sales-ai-insight-metric">
              <Text type="secondary" className="sales-ai-insight-metric-label">健康分</Text>
              <Progress
                percent={(aiData as SalesOrderAI).health_score}
                size="small"
                strokeColor={HEALTH_COLOR((aiData as SalesOrderAI).health_score)}
              />
            </div>
            <div className="sales-ai-insight-metric">
              <Text type="secondary" className="sales-ai-insight-metric-label">交货风险</Text>
              <Tag color={RISK_COLOR[(aiData as SalesOrderAI).delivery_risk]}>{RISK_LABEL[(aiData as SalesOrderAI).delivery_risk]}</Tag>
            </div>
            <div className="sales-ai-insight-metric">
              <Text type="secondary" className="sales-ai-insight-metric-label">回款风险</Text>
              <Tag color={RISK_COLOR[(aiData as SalesOrderAI).payment_risk]}>{RISK_LABEL[(aiData as SalesOrderAI).payment_risk]}</Tag>
            </div>
          </div>
          <InsightTagSection label="标记" values={(aiData as SalesOrderAI).flags} color="orange" />
        </>
      )}

      {"completion_risk" in aiData && !("health_score" in aiData) && (
        <>
          <div className="sales-ai-insight-metrics sales-ai-insight-metrics--two">
            <div className="sales-ai-insight-metric">
              <Text type="secondary" className="sales-ai-insight-metric-label">完成风险</Text>
              <Tag color={RISK_COLOR[(aiData as DeliveryNoteAI).completion_risk]}>{RISK_LABEL[(aiData as DeliveryNoteAI).completion_risk]}</Tag>
            </div>
            <div className="sales-ai-insight-metric">
              <Text type="secondary" className="sales-ai-insight-metric-label">签收延迟概率</Text>
              <Progress percent={(aiData as DeliveryNoteAI).signing_delay_probability} size="small" />
            </div>
          </div>
          <InsightTagSection label="问题" values={(aiData as DeliveryNoteAI).issues} color="red" />
        </>
      )}
    </Card>
  );
}
