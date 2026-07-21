import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Card, Col, Empty, List, Progress, Row, Space, Spin, Typography } from "antd";
import { StatusTag } from "../../ui";
import {
  AlertOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  LineChartOutlined,
  ReloadOutlined,
  RobotOutlined,
  TeamOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getCustomerAIStats, getDashboardStats, getFollowUpReminders } from "../../api";
import type { CustomerAIStats, DashboardStats, FollowUpReminder } from "../../types";
import CustomerModuleShell from "./CustomerModuleShell";
import { useAuthStore } from "@/store/auth";

const COLORS = ["#1677ff", "#52c41a", "#fa8c16", "#eb2f96", "#722ed1", "#13c2c2", "#f5222d", "#faad14", "#2f54eb"];
const { Text } = Typography;

const EMPTY_STATS: DashboardStats = {
  total: 0,
  by_industry: [],
  by_level: [],
  by_region: [],
  by_source: [],
  by_type: [],
  monthly: [],
};

const formatDateTime = (value?: string | null) => value ? value.slice(0, 16).replace("T", " ") : "-";

function getLevelCount(stats: DashboardStats, level: string) {
  return stats.by_level.find((item) => String(item.name).toUpperCase() === level)?.value || 0;
}

export default function CustomerDashboard() {
  const navigate = useNavigate();
  const roles = useAuthStore((state) => state.roles);
  const [stats, setStats] = useState<DashboardStats>(EMPTY_STATS);
  const [aiStats, setAiStats] = useState<CustomerAIStats | null>(null);
  const [reminders, setReminders] = useState<FollowUpReminder[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const [dashboardResult, aiResult, reminderResult] = await Promise.allSettled([
      getDashboardStats(),
      getCustomerAIStats(),
      getFollowUpReminders(),
    ]);

    if (dashboardResult.status === "fulfilled") {
      setStats(dashboardResult.value.data.data || EMPTY_STATS);
    }
    if (aiResult.status === "fulfilled") {
      setAiStats(aiResult.value.data.data as CustomerAIStats);
    }
    if (reminderResult.status === "fulfilled") {
      setReminders((reminderResult.value.data.data?.items || []) as FollowUpReminder[]);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const levelA = getLevelCount(stats, "A");
  const levelB = getLevelCount(stats, "B");
  const abRatio = stats.total ? Math.round(((levelA + levelB) / stats.total) * 100) : 0;
  const latestMonthly = stats.monthly[stats.monthly.length - 1];
  const topIndustry = stats.by_industry[0];
  const topRegion = stats.by_region[0];

  const reminderCounts = useMemo(() => ({
    overdue: reminders.filter((item) => item.due_bucket === "overdue").length,
    today: reminders.filter((item) => item.due_bucket === "today").length,
    upcoming: reminders.filter((item) => item.due_bucket === "upcoming").length,
  }), [reminders]);

  const actionItems = useMemo(() => {
    const items = [
      {
        key: "today",
        title: "今日待跟进",
        value: reminderCounts.today,
        tone: "warning" as const,
        action: "查看任务",
        onClick: () => navigate("/customers"),
      },
      {
        key: "overdue",
        title: "逾期未跟进",
        value: reminderCounts.overdue,
        tone: "danger" as const,
        action: "处理逾期",
        onClick: () => navigate("/customers"),
      },
      {
        key: "stale",
        title: "A类长期未联系",
        value: aiStats?.stale_high_value ?? 0,
        tone: "processing" as const,
        action: "查看智能分析",
        onClick: () => navigate("/customers/intelligence"),
      },
      {
        key: "churn",
        title: "高流失风险",
        value: aiStats?.high_churn_count ?? 0,
        tone: "danger" as const,
        action: "生成建议",
        onClick: () => navigate("/customers/workbench"),
      },
    ];
    return items;
  }, [aiStats, navigate, reminderCounts.overdue, reminderCounts.today]);

  const priorityReminders = useMemo(
    () => reminders
      .filter((item) => item.due_bucket === "overdue" || item.due_bucket === "today")
      .slice(0, 5),
    [reminders],
  );
  const dashboardContext = roles.some((role) => /finance/i.test(role))
    ? { title: "客户财务工作台", subtitle: "信用结构、客户价值与资料风险" }
    : roles.some((role) => /manager|supervisor|admin/i.test(role))
      ? { title: "客户经营工作台", subtitle: "团队客户盘面、跟进风险与重点行动" }
      : { title: "我的客户工作台", subtitle: "个人待跟进、重点客户与下一步行动" };

  if (loading) {
    return (
      <CustomerModuleShell title={dashboardContext.title} subtitle={dashboardContext.subtitle}>
        <Spin style={{ display: "block", marginTop: 100 }} />
      </CustomerModuleShell>
    );
  }

  if (!stats.total) {
    return (
      <CustomerModuleShell title={dashboardContext.title} subtitle={dashboardContext.subtitle}>
        <Empty description="暂无客户数据" />
      </CustomerModuleShell>
    );
  }

  return (
    <CustomerModuleShell
      title={dashboardContext.title}
      subtitle={dashboardContext.subtitle}
      extra={(
        <Space>
          <Button icon={<RobotOutlined />} onClick={() => navigate("/customers/workbench")}>AI工作队列</Button>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
        </Space>
      )}
    >
      <style>{`
        .customer-dashboard-kpis {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 10px;
          margin-bottom: 12px;
        }
        .customer-dashboard-kpi {
          min-height: 88px;
          padding: 12px;
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-dashboard-kpi.is-risk {
          background: #fffafa;
          border-color: #ffccc7;
        }
        .customer-dashboard-kpi.is-warning {
          background: #fffbe6;
          border-color: #ffe58f;
        }
        .customer-dashboard-kpi-title {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 20px;
        }
        .customer-dashboard-kpi-value {
          margin-top: 8px;
          color: #262626;
          font-size: var(--font-size-metric, 24px);
          font-weight: 600;
          line-height: 1;
        }
        .customer-dashboard-kpi-note {
          margin-top: 7px;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 18px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .customer-dashboard-section {
          margin-bottom: 12px;
        }
        .customer-dashboard-card .ant-card-body {
          padding: 12px;
        }
        .customer-dashboard-action-list {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }
        .customer-dashboard-action {
          padding: 10px;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          background: #fafafa;
        }
        .customer-dashboard-action-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          margin-bottom: 8px;
        }
        .customer-dashboard-action-value {
          font-size: 22px;
          font-weight: 600;
          line-height: 1;
        }
        .customer-dashboard-chart .ant-card-head {
          min-height: 44px;
        }
        .customer-dashboard-chart .ant-card-body {
          padding: 12px;
        }
        @media (max-width: 1200px) {
          .customer-dashboard-kpis {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }
        @media (max-width: 768px) {
          .customer-dashboard-kpis,
          .customer-dashboard-action-list {
            grid-template-columns: 1fr;
          }
        }
      `}</style>

      {(reminderCounts.overdue > 0 || (aiStats?.high_churn_count || 0) > 0) && (
        <Alert
          className="customer-dashboard-section"
          type={reminderCounts.overdue > 0 ? "error" : "warning"}
          icon={<AlertOutlined />}
          message={`当前有 ${reminderCounts.overdue} 个逾期跟进，${aiStats?.high_churn_count || 0} 个高流失风险客户`}
          action={<Button size="small" onClick={() => navigate("/customers/workbench")}>进入AI队列</Button>}
          showIcon
        />
      )}

      <div className="customer-dashboard-kpis">
        <div className="customer-dashboard-kpi">
          <div className="customer-dashboard-kpi-title"><span>客户总数</span><TeamOutlined /></div>
          <div className="customer-dashboard-kpi-value">{stats.total}</div>
          <div className="customer-dashboard-kpi-note">A/B级占比 {abRatio}%</div>
        </div>
        <div className="customer-dashboard-kpi">
          <div className="customer-dashboard-kpi-title"><span>A类客户</span><CheckCircleOutlined /></div>
          <div className="customer-dashboard-kpi-value">{levelA}</div>
          <div className="customer-dashboard-kpi-note">B类客户 {levelB}</div>
        </div>
        <div className="customer-dashboard-kpi">
          <div className="customer-dashboard-kpi-title"><span>本月新增</span><LineChartOutlined /></div>
          <div className="customer-dashboard-kpi-value">{latestMonthly?.count || 0}</div>
          <div className="customer-dashboard-kpi-note">{latestMonthly?.month || "暂无月度数据"}</div>
        </div>
        <div className={`customer-dashboard-kpi${reminderCounts.overdue > 0 ? " is-risk" : ""}`}>
          <div className="customer-dashboard-kpi-title"><span>逾期跟进</span><WarningOutlined /></div>
          <div className="customer-dashboard-kpi-value">{reminderCounts.overdue}</div>
          <div className="customer-dashboard-kpi-note">今日待跟进 {reminderCounts.today}</div>
        </div>
        <div className={`customer-dashboard-kpi${(aiStats?.high_churn_count || 0) > 0 ? " is-warning" : ""}`}>
          <div className="customer-dashboard-kpi-title"><span>AI风险客户</span><RobotOutlined /></div>
          <div className="customer-dashboard-kpi-value">{aiStats?.high_churn_count ?? "-"}</div>
          <div className="customer-dashboard-kpi-note">AI覆盖率 {aiStats ? `${aiStats.ai_coverage_pct}%` : "未加载"}</div>
        </div>
      </div>

      <Row gutter={[12, 12]} className="customer-dashboard-section">
        <Col xs={24} xl={14}>
          <Card size="small" className="customer-dashboard-card" title="风险与行动">
            <div className="customer-dashboard-action-list">
              {actionItems.map((item) => (
                <div className="customer-dashboard-action" key={item.key}>
                  <div className="customer-dashboard-action-head">
                    <Text type="secondary">{item.title}</Text>
                    <StatusTag status={String(item.value)} tone={item.tone} />
                  </div>
                  <div className="customer-dashboard-action-value">{item.value}</div>
                  <Button size="small" type="link" style={{ padding: 0, marginTop: 8 }} onClick={item.onClick}>
                    {item.action}
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card size="small" className="customer-dashboard-card" title="优先跟进">
            {priorityReminders.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无紧急跟进" />
            ) : (
              <List
                size="small"
                dataSource={priorityReminders}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button key="detail" size="small" type="link" onClick={() => navigate(`/customers/${item.customer_id}`)}>
                        查看
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={(
                        <Space wrap size={6}>
                          <Text strong>{item.customer_name}</Text>
                          <StatusTag
                            status={item.due_bucket === "overdue" ? `逾期 ${item.overdue_days} 天` : "今日"}
                            tone={item.due_bucket === "overdue" ? "danger" : "warning"}
                          />
                        </Space>
                      )}
                      description={(
                        <Space size={8} wrap>
                          <ClockCircleOutlined />
                          <span>{formatDateTime(item.planned_at)}</span>
                          {item.owner && <span>负责人 {item.owner}</span>}
                        </Space>
                      )}
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} className="customer-dashboard-section">
        <Col xs={24} xl={8}>
          <Card size="small" className="customer-dashboard-chart" title="客户等级分布">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={stats.by_level}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {stats.by_level.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card size="small" className="customer-dashboard-chart" title="行业分布" extra={<Text type="secondary">{topIndustry ? `${topIndustry.name} ${topIndustry.value}` : "-"}</Text>}>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={stats.by_industry} cx="50%" cy="50%" outerRadius={84} dataKey="value" label={({ name, value }) => `${name} ${value}`}>
                  {stats.by_industry.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card size="small" className="customer-dashboard-chart" title="区域分布" extra={<Text type="secondary">{topRegion ? `${topRegion.name} ${topRegion.value}` : "-"}</Text>}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={stats.by_region} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" allowDecimals={false} />
                <YAxis type="category" dataKey="name" width={64} />
                <Tooltip />
                <Bar dataKey="value" fill="#52c41a" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={15}>
          <Card size="small" className="customer-dashboard-chart" title="月度新增客户趋势">
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={stats.monthly}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Area type="monotone" dataKey="count" stroke="#1677ff" fill="#1677ff" fillOpacity={0.18} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} xl={9}>
          <Card size="small" className="customer-dashboard-card" title="客户质量">
            <Space direction="vertical" size={12} style={{ width: "100%" }}>
              <div>
                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                  <Text type="secondary">AI覆盖率</Text>
                  <Text>{aiStats ? `${aiStats.ai_coverage_pct}%` : "-"}</Text>
                </Space>
                <Progress percent={aiStats?.ai_coverage_pct || 0} size="small" />
              </div>
              <div>
                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                  <Text type="secondary">平均健康度</Text>
                  <Text>{aiStats?.avg_health_score ?? "-"}</Text>
                </Space>
                <Progress
                  percent={aiStats?.avg_health_score || 0}
                  size="small"
                  strokeColor={(aiStats?.avg_health_score || 0) >= 70 ? "#52c41a" : "#faad14"}
                />
              </div>
              <Space wrap>
                <StatusTag status={`从未联系 ${aiStats?.never_contacted ?? "-"}`} tone="warning" />
                <StatusTag status={`沉默高价值 ${aiStats?.stale_high_value ?? "-"}`} tone="processing" />
                <StatusTag status={`活跃30天 ${aiStats?.active_30d ?? "-"}`} tone="info" />
              </Space>
              <Button block icon={<RobotOutlined />} onClick={() => navigate("/customers/intelligence")}>
                查看客户智能分析
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </CustomerModuleShell>
  );
}
