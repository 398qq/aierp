import { useEffect, useMemo, useRef, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Collapse,
  Drawer,
  Empty,
  Flex,
  List,
  Progress,
  Space,
  Spin,
  Switch,
  Tabs,
  Tag,
  Timeline,
  Typography,
} from "antd";
import {
  AimOutlined,
  ArrowRightOutlined,
  CalendarOutlined,
  DollarOutlined,
  ReloadOutlined,
  RobotOutlined,
  SettingOutlined,
  ShopOutlined,
  StockOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { ProTable } from "@ant-design/pro-components";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useNavigate } from "@/router";
import {
  getDailyReport,
  getDashboardStats,
  getKpi,
  getOverdueFollowUps,
  getRecentActivity,
  getUpcomingVisits,
  getWidgets,
  orchestrateGlobal360,
  saveWidgets,
} from "../../api";
import { useAuthStore } from "../../store/auth";
import type {
  CustomerLog,
  DailyReport,
  DashboardStats,
  DashboardWidget,
  Global360,
  KpiData,
  OverdueFollowUp,
  Visit,
} from "../../types";
import { StatusTag } from "../../ui";
import "./dashboard.css";

const { Paragraph, Text, Title } = Typography;
const CHART_COLORS = ["#2563eb", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#64748b"];
const EMPTY_STATS: DashboardStats = {
  total: 0,
  by_industry: [],
  by_level: [],
  by_region: [],
  by_source: [],
  by_type: [],
  monthly: [],
};

const DEFAULT_WIDGETS: Record<string, { title: string; enabled: boolean }> = {
  kpi_overview: { title: "KPI 概览", enabled: true },
  customer_stats: { title: "客户统计", enabled: true },
  industry_chart: { title: "行业与等级分布", enabled: true },
  monthly_trend: { title: "月度新增趋势", enabled: true },
  overdue_followups: { title: "逾期跟进", enabled: true },
  upcoming_visits: { title: "拜访计划", enabled: true },
  recent_activity: { title: "最近动态", enabled: true },
  global_360: { title: "AI 全局诊断", enabled: true },
  daily_report: { title: "每日经营报告", enabled: true },
};

const money = (value: number) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
    notation: Math.abs(value) >= 1000000 ? "compact" : "standard",
  }).format(value || 0);

const shortDate = (value?: string | null) => value?.slice(0, 10) || "-";

function openAiAssistant() {
  const button =
    document.querySelector<HTMLElement>('[class*="floating"]') ||
    document.querySelector<HTMLElement>('button[style*="position: fixed"][style*="bottom"]');
  button?.click();
}

export default function Dashboard() {
  const navigate = useNavigate();
  const username = useAuthStore((state) => state.username);
  const initializedRef = useRef(false);
  const [stats, setStats] = useState<DashboardStats>(EMPTY_STATS);
  const [upcomingVisits, setUpcomingVisits] = useState<Visit[]>([]);
  const [recentActivity, setRecentActivity] = useState<CustomerLog[]>([]);
  const [overdue, setOverdue] = useState<OverdueFollowUp[]>([]);
  const [loading, setLoading] = useState(true);
  const [global360, setGlobal360] = useState<Global360 | null>(null);
  const [g360Loading, setG360Loading] = useState(false);
  const [dailyReport, setDailyReport] = useState<DailyReport | null>(null);
  const [drLoading, setDrLoading] = useState(false);
  const [kpi, setKpi] = useState<KpiData | null>(null);
  const [widgetDrawerOpen, setWidgetDrawerOpen] = useState(false);
  const [widgetSaving, setWidgetSaving] = useState(false);
  const [widgetPrefs, setWidgetPrefs] = useState(DEFAULT_WIDGETS);
  const industryRanking = useMemo(() => {
    const sorted = [...stats.by_industry].sort((a, b) => b.value - a.value);
    const top = sorted.slice(0, 8);
    const rest = sorted.slice(8).reduce((sum, item) => sum + item.value, 0);
    return rest > 0 ? [...top, { name: "其他", value: rest }] : top;
  }, [stats.by_industry]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("dashboard_widgets");
      if (saved) setWidgetPrefs({ ...DEFAULT_WIDGETS, ...JSON.parse(saved) });
    } catch {
      // Keep the defaults when local preferences are malformed.
    }

    getWidgets()
      .then((response) => {
        const widgets = (response.data.data || []) as DashboardWidget[];
        if (!widgets.length) return;
        const preferences = { ...DEFAULT_WIDGETS };
        for (const widget of widgets) {
          if (widget.widget_type && preferences[widget.widget_type]) {
            preferences[widget.widget_type] = {
              ...preferences[widget.widget_type],
              enabled: widget.enabled,
            };
          }
        }
        setWidgetPrefs(preferences);
        localStorage.setItem("dashboard_widgets", JSON.stringify(preferences));
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    Promise.allSettled([
      getDashboardStats(),
      getUpcomingVisits(14),
      getRecentActivity(10),
      getOverdueFollowUps(),
    ])
      .then((results) => {
        if (results[0].status === "fulfilled") setStats(results[0].value.data.data);
        if (results[1].status === "fulfilled") {
          const visitsData = results[1].value.data.data as { list?: Visit[] } | null;
          setUpcomingVisits(visitsData?.list || []);
        }
        if (results[2].status === "fulfilled") {
          setRecentActivity((results[2].value.data.data || []) as CustomerLog[]);
        }
        if (results[3].status === "fulfilled") {
          const overdueData = results[3].value.data.data as {
            total: number;
            items: OverdueFollowUp[];
          } | null;
          setOverdue(overdueData?.items || []);
        }
      })
      .finally(() => setLoading(false));

    getKpi()
      .then((response) => setKpi(response.data.data as KpiData))
      .catch(() => undefined);
    getDailyReport()
      .then((response) => setDailyReport(response.data.data as DailyReport))
      .catch(() => undefined);

    setG360Loading(true);
    orchestrateGlobal360()
      .then((response) => setGlobal360(response.data.data))
      .catch(() => undefined)
      .finally(() => setG360Loading(false));
  }, []);

  const saveWidgetPrefs = async () => {
    setWidgetSaving(true);
    try {
      localStorage.setItem("dashboard_widgets", JSON.stringify(widgetPrefs));
      await saveWidgets(
        Object.entries(widgetPrefs).map(([widgetType, preference]) => ({
          widget_type: widgetType,
          title: preference.title,
          enabled: preference.enabled,
        })),
      );
      setWidgetDrawerOpen(false);
    } finally {
      setWidgetSaving(false);
    }
  };

  const kpiItems = useMemo(
    () =>
      kpi
        ? [
            {
              label: "本月营收",
              value: money(kpi.month_revenue),
              icon: <DollarOutlined />,
              tone: "primary",
              hint: "本月累计",
            },
            {
              label: "应收未收",
              value: money(kpi.outstanding_ar),
              icon: <WarningOutlined />,
              tone: kpi.outstanding_ar > 0 ? "danger" : "success",
              hint: "需持续催收",
            },
            {
              label: "活跃商机",
              value: kpi.open_opportunities.toLocaleString(),
              icon: <ThunderboltOutlined />,
              tone: "info",
              hint: "销售机会",
            },
            {
              label: "待采购订单",
              value: kpi.pending_purchase_orders.toLocaleString(),
              icon: <ShopOutlined />,
              tone: kpi.pending_purchase_orders > 0 ? "warning" : "success",
              hint: "待处理",
            },
            {
              label: "低库存预警",
              value: kpi.low_stock_items.toLocaleString(),
              icon: <StockOutlined />,
              tone: kpi.low_stock_items > 0 ? "danger" : "success",
              hint: "库存风险",
            },
            {
              label: "本月新客户",
              value: kpi.new_customers.toLocaleString(),
              icon: <TeamOutlined />,
              tone: "success",
              hint: `客户总数 ${kpi.total_customers}`,
            },
          ]
        : [],
    [kpi],
  );

  const taskTabs = [
    widgetPrefs.overdue_followups?.enabled !== false
      ? {
          key: "overdue",
          label: (
            <span>
              逾期跟进 <Badge count={overdue.length} size="small" />
            </span>
          ),
          children: overdue.length ? (
            <ProTable
              rowKey="id"
              dataSource={overdue.slice(0, 8)}
              columns={[
                { title: "客户", dataIndex: "customer_name", ellipsis: true },
                { title: "负责人", dataIndex: "owner", width: 88, render: (value: string | null) => value || "-" },
                { title: "计划日期", dataIndex: "planned_at", width: 104, render: shortDate },
                {
                  title: "逾期",
                  dataIndex: "overdue_days",
                  width: 78,
                  render: (value: number) => <StatusTag status={`${value}天`} tone="danger" />,
                },
                {
                  title: "操作",
                  key: "actions",
                  width: 96,
                  render: (_: unknown, record: OverdueFollowUp) => (
                    <Button
                      type="link"
                      size="small"
                      onClick={() => navigate(`/customers/${record.customer_id}/follow-ups?update=${record.id}`)}
                    >
                      更新跟进
                    </Button>
                  ),
                },
              ] as any}
              search={false}
              options={false}
              pagination={false}
              size="small"
            />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无逾期跟进" />
          ),
        }
      : null,
    widgetPrefs.upcoming_visits?.enabled !== false
      ? {
          key: "visits",
          label: (
            <span>
              近期拜访 <Badge count={upcomingVisits.length} size="small" color="#2563eb" />
            </span>
          ),
          children: upcomingVisits.length ? (
            <ProTable
              rowKey="id"
              dataSource={upcomingVisits.slice(0, 8)}
              columns={[
                { title: "拜访主题", dataIndex: "title", ellipsis: true, render: (value: string | null) => value || "客户拜访" },
                { title: "方式", dataIndex: "type", width: 82, render: (value: string | null) => value || "-" },
                { title: "日期", dataIndex: "visit_date", width: 104, render: shortDate },
                {
                  title: "状态",
                  dataIndex: "status",
                  width: 86,
                  render: (value: string) => (
                    <StatusTag
                      status={value || "planned"}
                      tone={value === "completed" ? "success" : value === "cancelled" ? "danger" : "info"}
                      label={value === "completed" ? "已完成" : value === "cancelled" ? "已取消" : "计划中"}
                    />
                  ),
                },
              ] as any}
              search={false}
              options={false}
              pagination={false}
              size="small"
            />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未来14天暂无拜访" />
          ),
        }
      : null,
    widgetPrefs.recent_activity?.enabled !== false
      ? {
          key: "activity",
          label: `最近动态 ${recentActivity.length}`,
          children: recentActivity.length ? (
            <Timeline
              className="dashboard-activity"
              items={recentActivity.slice(0, 7).map((log) => ({
                children: (
                  <div>
                    <Text strong>{log.customer_name || "系统记录"}</Text>
                    <Text type="secondary"> · {log.summary || log.action}</Text>
                    <div className="dashboard-activity-time">
                      {log.created_at?.slice(0, 16).replace("T", " ")}
                      {log.operator ? ` · ${log.operator}` : ""}
                    </div>
                  </div>
                ),
              }))}
            />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无最近动态" />
          ),
        }
      : null,
  ].filter(Boolean) as { key: string; label: React.ReactNode; children: React.ReactNode }[];

  if (loading) {
    return (
      <Flex justify="center" align="center" className="dashboard-loading">
        <Spin size="large" description="正在汇总经营数据..." />
      </Flex>
    );
  }

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero">
        <div>
          <Text className="dashboard-eyebrow">
            {new Intl.DateTimeFormat("zh-CN", {
              month: "long",
              day: "numeric",
              weekday: "long",
            }).format(new Date())}
          </Text>
          <Title level={2}>经营总览</Title>
          <Text type="secondary">欢迎回来，{username}。以下是当前最需要关注的经营信号。</Text>
        </div>
        <Space wrap>
          <Button icon={<RobotOutlined />} onClick={openAiAssistant}>
            AI 经营问答
          </Button>
          <Button icon={<SettingOutlined />} onClick={() => setWidgetDrawerOpen(true)}>
            自定义
          </Button>
          <Button type="primary" icon={<ReloadOutlined />} onClick={() => window.location.reload()}>
            刷新数据
          </Button>
        </Space>
      </section>

      <section className="dashboard-query-bar">
        <span className="dashboard-query-label">
          <RobotOutlined /> 快速提问
        </span>
        <Space wrap size={[8, 8]}>
          {["本月销售趋势", "客户流失风险", "库存周转", "逾期回款", "供应商履约"].map((question) => (
            <Button key={question} size="small" type="text" onClick={openAiAssistant}>
              {question}
            </Button>
          ))}
        </Space>
      </section>

      {widgetPrefs.kpi_overview?.enabled !== false && kpiItems.length > 0 && (
        <section className="dashboard-kpi-grid">
          {kpiItems.map((item) => (
            <Card key={item.label} className={`dashboard-kpi dashboard-kpi-${item.tone}`}>
              <div className="dashboard-kpi-top">
                <span className="dashboard-kpi-icon">{item.icon}</span>
                <Text type="secondary">{item.hint}</Text>
              </div>
              <div className="dashboard-kpi-value">{item.value}</div>
              <Text className="dashboard-kpi-label">{item.label}</Text>
            </Card>
          ))}
        </section>
      )}

      {widgetPrefs.customer_stats?.enabled !== false && (
        <section className="dashboard-pulse">
          <div className="dashboard-section-heading">
            <div>
              <Text strong>运营脉搏</Text>
              <Text type="secondary">客户经营与执行节奏</Text>
            </div>
          </div>
          <div className="dashboard-pulse-items">
            {[
              { label: "客户总数", value: stats.total, color: "#2563eb" },
              { label: "逾期跟进", value: overdue.length, color: overdue.length ? "#ef4444" : "#10b981" },
              { label: "未来14天拜访", value: upcomingVisits.length, color: "#3b82f6" },
              { label: "近期客户动态", value: recentActivity.length, color: "#f59e0b" },
            ].map((item) => (
              <div className="dashboard-pulse-item" key={item.label}>
                <span className="dashboard-pulse-dot" style={{ background: item.color }} />
                <span>
                  <strong>{item.value.toLocaleString()}</strong>
                  <Text type="secondary">{item.label}</Text>
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="dashboard-primary-grid">
        {taskTabs.length > 0 && (
          <Card
            className="dashboard-panel dashboard-task-panel"
            title={
              <div className="dashboard-card-title">
                <span>今日待办</span>
                <Text type="secondary">优先处理异常和客户行动</Text>
              </div>
            }
            extra={
              <Button type="link" onClick={() => navigate("/customers")} icon={<ArrowRightOutlined />}>
                客户中心
              </Button>
            }
          >
            <Tabs items={taskTabs} />
          </Card>
        )}

        {widgetPrefs.daily_report?.enabled !== false && (
          <Card
            className="dashboard-panel dashboard-report-panel"
            title={
              <div className="dashboard-card-title">
                <span>今日经营简报</span>
                <Text type="secondary">{dailyReport?.report_date || "实时摘要"}</Text>
              </div>
            }
            extra={
              <Button
                type="text"
                icon={<ReloadOutlined />}
                loading={drLoading}
                onClick={async () => {
                  setDrLoading(true);
                  try {
                    const response = await getDailyReport();
                    setDailyReport(response.data.data as DailyReport);
                  } finally {
                    setDrLoading(false);
                  }
                }}
              />
            }
          >
            {dailyReport ? (
              <>
                <div className="dashboard-report-mood">
                  <StatusTag
                    status={dailyReport.mood}
                    tone={
                      dailyReport.mood === "良好"
                        ? "success"
                        : dailyReport.mood === "需关注"
                          ? "danger"
                          : "warning"
                    }
                  />
                  <Paragraph>{dailyReport.ai_summary}</Paragraph>
                </div>
                <div className="dashboard-report-metrics">
                  <div><strong>{dailyReport.metrics.orders_today}</strong><Text>今日订单</Text></div>
                  <div><strong>{money(dailyReport.metrics.revenue_today)}</strong><Text>今日营收</Text></div>
                  <div><strong>{dailyReport.metrics.new_customers}</strong><Text>新增客户</Text></div>
                  <div className={dailyReport.metrics.low_stock_items > 0 ? "is-risk" : ""}>
                    <strong>{dailyReport.metrics.low_stock_items}</strong><Text>低库存</Text>
                  </div>
                </div>
                {dailyReport.top_action && (
                  <div className="dashboard-next-action">
                    <AimOutlined />
                    <div>
                      <Text type="secondary">首要行动</Text>
                      <Text strong>{dailyReport.top_action}</Text>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="经营简报暂不可用" />
            )}
          </Card>
        )}
      </section>

      {(widgetPrefs.monthly_trend?.enabled !== false ||
        widgetPrefs.industry_chart?.enabled !== false) && (
        <section>
          <div className="dashboard-section-title">
            <div>
              <Title level={4}>客户增长与结构</Title>
              <Text type="secondary">观察客户新增趋势和组合质量</Text>
            </div>
            <Button type="link" onClick={() => navigate("/customers/stats")}>
              查看客户分析 <ArrowRightOutlined />
            </Button>
          </div>
          <div className="dashboard-chart-grid">
            {widgetPrefs.monthly_trend?.enabled !== false && (
              <Card className="dashboard-panel dashboard-trend-card" title="月度新增客户">
                {stats.monthly.length ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={stats.monthly} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}>
                      <CartesianGrid stroke="#edf0f7" vertical={false} />
                      <XAxis dataKey="month" axisLine={false} tickLine={false} />
                      <YAxis axisLine={false} tickLine={false} allowDecimals={false} />
                      <Tooltip cursor={{ fill: "#f6f5ff" }} />
                      <Bar dataKey="count" name="新增客户" fill="#2563eb" radius={[6, 6, 0, 0]} maxBarSize={42} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无月度趋势" />
                )}
              </Card>
            )}

            {widgetPrefs.industry_chart?.enabled !== false && (
              <>
                <Card className="dashboard-panel" title="行业分布">
                  {industryRanking.length ? (
                    <Space direction="vertical" size={7} style={{ width: "100%" }}>
                      {industryRanking.map((item, index) => (
                        <div key={item.name} style={{ width: "100%" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 2 }}>
                            <Text ellipsis={{ tooltip: item.name }} style={{ maxWidth: "78%" }}>{index + 1}. {item.name}</Text>
                            <Text strong>{item.value}</Text>
                          </div>
                          <Progress percent={Math.round((item.value / (industryRanking[0]?.value || 1)) * 100)} showInfo={false} size="small" strokeColor={index === 0 ? "#2563eb" : "#93c5fd"} />
                        </div>
                      ))}
                    </Space>
                  ) : (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无行业数据" />
                  )}
                </Card>
                <Card className="dashboard-panel" title="客户等级">
                  {stats.by_level.length ? (
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart
                        data={stats.by_level}
                        layout="vertical"
                        margin={{ top: 12, right: 12, left: 2, bottom: 0 }}
                      >
                        <CartesianGrid stroke="#edf0f7" horizontal={false} />
                        <XAxis type="number" axisLine={false} tickLine={false} allowDecimals={false} />
                        <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} width={50} />
                        <Tooltip cursor={{ fill: "#f6f5ff" }} />
                        <Bar dataKey="value" name="客户数" fill="#3b82f6" radius={[0, 6, 6, 0]} maxBarSize={26} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无等级数据" />
                  )}
                </Card>
              </>
            )}
          </div>
        </section>
      )}

      {widgetPrefs.global_360?.enabled !== false && (
        <Card
          className="dashboard-panel dashboard-ai-panel"
          title={
            <div className="dashboard-ai-title">
              <span className="dashboard-ai-icon"><AimOutlined /></span>
              <div>
                <span>AI 全局经营诊断</span>
                <Text type="secondary">跨销售、客户、供应链与财务的综合判断</Text>
              </div>
            </div>
          }
          extra={
            <Button
              icon={<ReloadOutlined />}
              loading={g360Loading}
              onClick={async () => {
                setG360Loading(true);
                try {
                  const response = await orchestrateGlobal360();
                  setGlobal360(response.data.data);
                } finally {
                  setG360Loading(false);
                }
              }}
            >
              重新诊断
            </Button>
          }
        >
          {global360 ? (
            <>
              <div className="dashboard-health-summary">
                <Progress
                  type="circle"
                  percent={global360.enterprise_health_score}
                  size={132}
                  strokeWidth={9}
                  strokeColor={
                    global360.enterprise_health_score >= 80
                      ? "#10b981"
                      : global360.enterprise_health_score >= 60
                        ? "#f59e0b"
                        : "#ef4444"
                  }
                  format={(percent) => (
                    <span className="dashboard-health-score">
                      {percent}
                      <small>健康分</small>
                    </span>
                  )}
                />
                <div className="dashboard-health-copy">
                  <Paragraph>{global360.executive_summary}</Paragraph>
                  <Space wrap>
                    {global360.focus_areas?.map((area) => (
                      <StatusTag key={area} status={area} tone="info" />
                    ))}
                  </Space>
                </div>
                <div className="dashboard-health-counts">
                  <div><strong>{global360.top_opportunities.length}</strong><Text>重点机会</Text></div>
                  <div><strong>{global360.top_risks.length}</strong><Text>主要风险</Text></div>
                  <div><strong>{global360.strategic_recommendations.length}</strong><Text>行动建议</Text></div>
                </div>
              </div>

              <Collapse
                ghost
                className="dashboard-ai-collapse"
                defaultActiveKey={["risks"]}
                items={[
                  global360.top_risks.length
                    ? {
                        key: "risks",
                        label: <Badge status="error" text={`主要风险 (${global360.top_risks.length})`} />,
                        children: (
                          <ProTable
                            rowKey={(record) => `${record.area}-${record.description}`}
                            dataSource={global360.top_risks}
                            columns={[
                              { title: "领域", dataIndex: "area", width: 110 },
                              { title: "风险描述", dataIndex: "description", ellipsis: true },
                              {
                                title: "严重程度",
                                dataIndex: "severity",
                                width: 96,
                                render: (value: string) => (
                                  <StatusTag
                                    status={value}
                                    tone={
                                      value.includes("高") || value === "high"
                                        ? "danger"
                                        : value.includes("中") || value === "medium"
                                          ? "warning"
                                          : "info"
                                    }
                                  />
                                ),
                              },
                              { title: "缓解措施", dataIndex: "mitigation", ellipsis: true },
                            ] as any}
                            search={false}
                            options={false}
                            pagination={false}
                            size="small"
                          />
                        ),
                      }
                    : null,
                  global360.top_opportunities.length
                    ? {
                        key: "opportunities",
                        label: `重点机会 (${global360.top_opportunities.length})`,
                        children: (
                          <ProTable
                            rowKey={(record) => `${record.area}-${record.description}`}
                            dataSource={global360.top_opportunities}
                            columns={[
                              { title: "领域", dataIndex: "area", width: 110 },
                              { title: "机会描述", dataIndex: "description", ellipsis: true },
                              {
                                title: "潜在价值",
                                dataIndex: "potential_value",
                                width: 120,
                                render: (value: number) => money(value),
                              },
                              { title: "时间窗口", dataIndex: "timeframe", width: 110 },
                            ] as any}
                            search={false}
                            options={false}
                            pagination={false}
                            size="small"
                          />
                        ),
                      }
                    : null,
                  global360.strategic_recommendations.length
                    ? {
                        key: "recommendations",
                        label: `行动建议 (${global360.strategic_recommendations.length})`,
                        children: (
                          <List
                            size="small"
                            dataSource={global360.strategic_recommendations}
                            renderItem={(recommendation) => (
                              <List.Item>
                                <List.Item.Meta
                                  title={
                                    <Space wrap>
                                      <StatusTag
                                        status={recommendation.priority}
                                        tone={
                                          recommendation.priority === "高" || recommendation.priority === "high"
                                            ? "danger"
                                            : recommendation.priority === "中" || recommendation.priority === "medium"
                                              ? "warning"
                                              : "info"
                                        }
                                      />
                                      <Tag>{recommendation.domain}</Tag>
                                      <Text strong>{recommendation.recommendation}</Text>
                                    </Space>
                                  }
                                  description={recommendation.rationale}
                                />
                              </List.Item>
                            )}
                          />
                        ),
                      }
                    : null,
                ].filter(Boolean) as { key: string; label: React.ReactNode; children: React.ReactNode }[]}
              />
            </>
          ) : (
            <div className="dashboard-ai-empty">
              {g360Loading ? <Spin description="AI 正在分析企业经营数据..." /> : <Empty description="AI 诊断暂不可用" />}
            </div>
          )}
        </Card>
      )}

      <Drawer
        title="自定义仪表盘"
        open={widgetDrawerOpen}
        onClose={() => {
          try {
            const saved = localStorage.getItem("dashboard_widgets");
            if (saved) setWidgetPrefs({ ...DEFAULT_WIDGETS, ...JSON.parse(saved) });
          } catch {
            setWidgetPrefs(DEFAULT_WIDGETS);
          }
          setWidgetDrawerOpen(false);
        }}
        size="default"
        extra={
          <Button type="primary" loading={widgetSaving} onClick={saveWidgetPrefs}>
            保存
          </Button>
        }
      >
        <div className="dashboard-widget-list">
          {Object.entries(widgetPrefs).map(([key, preference]) => (
            <div className="dashboard-widget-item" key={key}>
              <Text>{preference.title}</Text>
              <Switch
                checked={preference.enabled}
                onChange={(enabled) =>
                  setWidgetPrefs((current) => ({
                    ...current,
                    [key]: { ...current[key], enabled },
                  }))
                }
              />
            </div>
          ))}
        </div>
        <Text type="secondary" className="dashboard-widget-note">
          模块偏好保存后会同步到当前账号。
        </Text>
      </Drawer>
    </div>
  );
}
