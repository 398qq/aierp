import { Typography } from "antd";
import styles from "./TopActions.module.css";

const { Text } = Typography;

export interface TopActionsProps {
  items: string[];
}

export function TopActions({ items }: TopActionsProps) {
  if (!items.length) return null;
  return (
    <div className={styles.section}>
      <Text strong>优先行动</Text>
      <ol className={styles.list}>
        {items.map((item, i) => (
          <li key={i}>{`${i + 1}. ${item}`}</li>
        ))}
      </ol>
    </div>
  );
}
