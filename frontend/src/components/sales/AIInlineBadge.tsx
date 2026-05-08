import { Tag, Tooltip } from "antd";

interface Props {
  riskLevel?: string;
  flag?: string;
  healthScore?: number;
}

const RISK_COLOR: Record<string, string> = { low: "green", medium: "orange", high: "red" };
const RISK_LABEL: Record<string, string> = { low: "低风险", medium: "中风险", high: "高风险" };

export default function AIInlineBadge({ riskLevel, flag, healthScore }: Props) {
  if (!riskLevel && !flag && healthScore === undefined) return <Tag color="default">—</Tag>;

  const color = riskLevel ? RISK_COLOR[riskLevel] || "default" : "default";
  const label = riskLevel ? RISK_LABEL[riskLevel] || riskLevel : (flag || `健康分:${healthScore}`);

  return (
    <Tooltip title={flag || `${RISK_LABEL[riskLevel || ""] || riskLevel}`}>
      <Tag color={color} style={{ cursor: "default" }}>{label}</Tag>
    </Tooltip>
  );
}
