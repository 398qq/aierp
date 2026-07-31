import { Button, Space, Typography } from "antd";
import { WarningOutlined, ReloadOutlined } from "@ant-design/icons";
import styles from "./ScanHeader.module.css";

const { Title, Text } = Typography;

const safeFormatDate = (d: string | undefined | null): string => {
  if (!d) return "未知时间";
  try {
    const date = new Date(d);
    if (isNaN(date.getTime())) return "无效时间";
    return date.toLocaleString();
  } catch {
    return "无效时间";
  }
};

export interface ScanHeaderProps {
  scanned_at: string;
  loading: boolean;
  onRefresh: () => void;
}

export function ScanHeader({ scanned_at, loading, onRefresh }: ScanHeaderProps) {
  return (
    <div className={styles.header}>
      <Title level={4} className={styles.title}>
        <WarningOutlined /> 全局监控中心
      </Title>
      <Space>
        <Text type="secondary">扫描时间: {safeFormatDate(scanned_at)}</Text>
        <Button
          icon={<ReloadOutlined />}
          onClick={onRefresh}
          loading={loading}
          aria-label="刷新"
          aria-busy={loading}
        >
          刷新
        </Button>
      </Space>
    </div>
  );
}
