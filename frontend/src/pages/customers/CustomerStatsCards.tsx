// CustomerStatsCards — top-of-page 4-up KPI grid for the customer workbench.
// Pure presentational; receives all values as props.

import {
  BellOutlined,
  PhoneOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
} from "@ant-design/icons";

interface StatCard {
  title: string;
  value: string | number;
  note: string;
  icon: React.ReactNode;
  variant?: "default" | "warning" | "risk";
}

interface Props {
  total: number;
  statsLoading: boolean;
  filteredCount: number;
  todayReminders: number;
  overdueReminders: number;
  lastRefreshedAt: Date | null;
  levelACount: number;
  topRegion?: { name: string; value: number } | undefined;
  monthlyNewCount: number;
  formatRefreshTime: (value: Date | null) => string;
}

export default function CustomerStatsCards({
  total,
  statsLoading,
  filteredCount,
  todayReminders,
  overdueReminders,
  lastRefreshedAt,
  levelACount,
  topRegion,
  monthlyNewCount,
  formatRefreshTime,
}: Props) {
  const cards: StatCard[] = [
    {
      title: "客户总数",
      value: statsLoading ? "..." : total,
      note: `当前筛选显示 ${filteredCount} 条`,
      icon: <UserOutlined />,
    },
    {
      title: "今日待跟进",
      value: todayReminders,
      note: formatRefreshTime(lastRefreshedAt),
      icon: <PhoneOutlined />,
      variant: todayReminders > 0 ? "warning" : "default",
    },
    {
      title: "超期未跟进",
      value: overdueReminders,
      note: "可一键完成或延期处理",
      icon: <BellOutlined />,
      variant: overdueReminders > 0 ? "risk" : "default",
    },
    {
      title: "高价值客户",
      value: statsLoading ? "..." : levelACount,
      note: topRegion
        ? `主力区域 ${topRegion.name} ${topRegion.value}`
        : `本月新增 ${monthlyNewCount}`,
      icon: <SafetyCertificateOutlined />,
    },
  ];

  return (
    <div className="customer-workbench-grid">
      {cards.map((card) => (
        <div
          key={card.title}
          className={`customer-kpi-card${card.variant && card.variant !== "default" ? ` is-${card.variant}` : ""}`}
        >
          <div className="customer-kpi-title">
            <span>{card.title}</span>
            {card.icon}
          </div>
          <div className="customer-kpi-value">{card.value}</div>
          <div className="customer-kpi-note">{card.note}</div>
        </div>
      ))}
    </div>
  );
}
