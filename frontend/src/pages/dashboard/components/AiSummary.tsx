import { Typography } from "antd";
import styles from "./AiSummary.module.css";

const { Text } = Typography;

export interface AiSummaryProps {
  text: string;
}

export function AiSummary({ text }: AiSummaryProps) {
  return (
    <div className={styles.section}>
      <Text strong>AI 分析摘要</Text>
      <div className={styles.body}>{text || "暂无 AI 摘要"}</div>
    </div>
  );
}
