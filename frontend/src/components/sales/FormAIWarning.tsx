import { useEffect, useState } from "react";
import { Alert } from "antd";
import { WarningOutlined } from "@ant-design/icons";

interface Props {
  entityType: "opportunity" | "quotation";
  formData: Record<string, unknown>;
}

/** Local heuristic checks for suspicious form data. Fast, no API call needed. */
export default function FormAIWarning({ entityType, formData }: Props) {
  const [warnings, setWarnings] = useState<string[]>([]);

  useEffect(() => {
    const title = formData.title as string | undefined;
    const amount = formData.amount as number | undefined;
    if (!title || title.length < 3) {
      setWarnings([]);
      return;
    }
    const issues: string[] = [];

    if (entityType === "opportunity") {
      if (amount && amount > 1_000_000) issues.push("金额超过100万，请确认是否需要二级审批");
      if (amount && amount < 100) issues.push("金额异常偏低，请检查是否正确");
      const wp = formData.win_probability as number | undefined;
      if (wp !== undefined && wp < 10) issues.push("赢单概率过低，建议评估是否值得跟进");
      if (wp !== undefined && wp > 95) issues.push("赢单概率接近100%，可以尝试推进报价");
    }

    if (entityType === "quotation") {
      if (amount && amount > 5_000_000) issues.push("报价金额超过500万，建议确认利润率");
      if (amount && amount < 50) issues.push("报价金额异常偏低，请检查");
      const status = formData.status as string | undefined;
      if (status === "sent" && !amount) issues.push("已发送报价但缺少金额");
    }

    setWarnings(issues);
  }, [entityType, formData]);

  if (warnings.length === 0) return null;

  return (
    <Alert
      type="warning"
      showIcon
      icon={<WarningOutlined />}
      message="AI 数据检查提示"
      description={
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          {warnings.map((w, i) => <li key={i}>{w}</li>)}
        </ul>
      }
      style={{ marginBottom: 16 }}
      closable
    />
  );
}
