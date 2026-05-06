import { Spin, Alert, Empty } from "antd";

interface Props {
  loading: boolean;
  error: string | null;
  data: unknown;
  children: React.ReactNode;
}

export default function LoadingGuard({ loading, error, data, children }: Props) {
  if (loading) return <Spin size="large" style={{ display: "block", margin: "80px auto" }} />;
  if (error) return <Alert type="error" message="加载失败" description={error} showIcon />;
  if (!data || (Array.isArray(data) && data.length === 0))
    return <Empty description="暂无数据" />;
  return <>{children}</>;
}
