import { Empty, Progress, Space, Typography } from "antd";

const { Text } = Typography;

export interface IndustryRankingItem {
  name: string;
  value: number;
}

export interface IndustryRankingProps {
  items: IndustryRankingItem[];
  limit?: number;
  emptyDescription?: string;
  primaryColor?: string;
  secondaryColor?: string;
}

export function buildIndustryRanking(items: IndustryRankingItem[], limit = 8) {
  const normalizedLimit = Math.max(1, Math.trunc(limit));
  const sorted = items
    .filter((item) => Number.isFinite(item.value))
    .map((item) => ({ ...item, value: Math.max(0, item.value) }))
    .sort((left, right) => right.value - left.value);
  const visible = sorted.slice(0, normalizedLimit);
  const remainingValue = sorted.slice(normalizedLimit).reduce((sum, item) => sum + item.value, 0);

  return remainingValue > 0 ? [...visible, { name: "其他", value: remainingValue }] : visible;
}

export function IndustryRanking({
  items,
  limit = 8,
  emptyDescription = "暂无行业数据",
  primaryColor = "#2563eb",
  secondaryColor = "#93c5fd",
}: IndustryRankingProps) {
  const ranking = buildIndustryRanking(items, limit);
  const maximumValue = ranking[0]?.value || 1;

  if (ranking.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyDescription} />;
  }

  return (
    <Space className="erp-industry-ranking" direction="vertical" size={7}>
      {ranking.map((item, index) => (
        <div className="erp-industry-ranking-item" key={`${item.name}-${index}`}>
          <div className="erp-industry-ranking-label">
            <Text ellipsis={{ tooltip: item.name }}>
              {index + 1}. {item.name}
            </Text>
            <Text strong>{item.value}</Text>
          </div>
          <Progress
            aria-label={`${item.name} ${item.value}`}
            percent={Math.round((item.value / maximumValue) * 100)}
            showInfo={false}
            size="small"
            strokeColor={index === 0 ? primaryColor : secondaryColor}
          />
        </div>
      ))}
    </Space>
  );
}
