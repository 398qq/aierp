import { useEffect, useRef, useState } from "react";
import { Row, Col, Card, Flex, Statistic, Typography, Table, Spin, Tag, Timeline, Button, List, Progress, Collapse, Empty, Space, Badge, Drawer, Switch } from "antd";
import { StatusTag } from "../../ui";
import {
  TeamOutlined, ThunderboltOutlined, CalendarOutlined, ReloadOutlined, AimOutlined, WarningOutlined, SettingOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../../store/auth";
import { getDashboardStats, getUpcomingVisits, getRecentActivity, getOverdueFollowUps, orchestrateGlobal360, getDailyReport, getKpi, getWidgets, saveWidgets } from "../../api";
import type { DashboardStats, DashboardWidget, Visit, CustomerLog, Global360, OverdueFollowUp, DailyReport, KpiData } from "../../types";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

const { Title, Text, Paragraph } = Typography;
const COLORS = ["#1890ff", "#52c41a", "#faad14", "#ff4d4f", "#722ed1", "#13c2c2"];

const EMPTY_STATS: DashboardStats = { total: 0, by_industry: [], by_level: [], by_region: [], by_source: [], by_type: [], monthly: [] };

export default function Dashboard() {
  const username = useAuthStore((s) => s.username);
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
  const initializedRef = useRef(false);

  // Widget visibility customization
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

  const [widgetPrefs, setWidgetPrefs] = useState<Record<string, { title: string; enabled: boolean }>>(() => {
    try {
      const saved = localStorage.getItem("dashboard_widgets");
      if (saved) return { ...DEFAULT_WIDGETS, ...JSON.parse(saved) };
    } catch {}
    return DEFAULT_WIDGETS;
  });
  const [widgetDrawerOpen, setWidgetDrawerOpen] = useState(false);
  const [widgetSaving, setWidgetSaving] = useState(false);

  // Load widget prefs from backend on mount
  useEffect(() => {
    getWidgets().then((r) => {
      const widgets = (r.data.data || []) as DashboardWidget[];
      if (widgets.length > 0) {
        const prefs: Record<string, { title: string; enabled: boolean }> = { ...DEFAULT_WIDGETS };
        for (const w of widgets) {
          if (w.widget_type && prefs[w.widget_type]) {
            prefs[w.widget_type].enabled = w.enabled;
          }
        }
        setWidgetPrefs(prefs);
        localStorage.setItem("dashboard_widgets", JSON.stringify(prefs));
      }
    }).catch(() => {});
  }, []);

  const saveWidgetPrefs = async () => {
    setWidgetSaving(true);
    try {
      localStorage.setItem("dashboard_widgets", JSON.stringify(widgetPrefs));
      const payload = Object.entries(widgetPrefs).map(([type, pref]) => ({
        widget_type: type,
        title: pref.title,
        enabled: pref.enabled,
      }));
      await saveWidgets(payload);
      setWidgetDrawerOpen(false);
    } catch {} finally {
      setWidgetSaving(false);
    }
  };

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    Promise.all([
      getDashboardStats(),
      getUpcomingVisits(14),
      getRecentActivity(10),
      getOverdueFollowUps(),
    ])
      .then(([s, uv, ra, od]) => {
        setStats(s.data.data);
        setUpcomingVisits((uv.data.data || []) as unknown as Visit[]);
        setRecentActivity((ra.data.data || []) as CustomerLog[]);
        const odData = od.data.data as { total: number; items: OverdueFollowUp[] } | null;
        setOverdue(odData?.items || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    getKpi().then((r) => setKpi(r.data.data as KpiData)).catch(() => {});
    getDailyReport().then((r) => setDailyReport(r.data.data as DailyReport)).catch(() => {});

    setG360Loading(true);
    orchestrateGlobal360()
      .then((r) => setGlobal360(r.data.data))
      .catch(() => {})
      .finally(() => setG360Loading(false));
  }, []);

  if (loading) return <Flex justify="center" style={{ marginTop: 120 }}><Spin size="large" /></Flex>;

  return (
    <div>
      <Flex justify="space-between" align="center" wrap gap={8}>
        <Title level={4} style={{ margin: 0 }}>欢迎回来，{username}</Title>
        <Button icon={<SettingOutlined />} onClick={() => setWidgetDrawerOpen(true)}>自定义仪表板</Button>
      </Flex>

      <Space wrap style={{ marginBottom: 16 }}>
        <Text type="secondary">AI 问答建议：</Text>
        {["本月销售趋势如何？", "哪些客户有流失风险？", "库存周转率最高的产品？", "逾期付款情况？", "供应商准时交付率排名？"].map((q) => (
          <StatusTag key={q} status={q} tone="processing" style={{ cursor: "pointer" }}
            onClick={() => {
              const btn = document.querySelector<HTMLElement>('[class*="floating"]') || document.querySelector('[style*="fixed"][style*="bottom"]');
              if (btn) btn.click();
            }}>
            {q}
          </StatusTag>
        ))}
      </Space>

      {/* Phase 7 KPI Overview */}
      {kpi && widgetPrefs.kpi_overview?.enabled !== false && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={8} lg={6}>
            <Card>
              <Statistic title="本月营收" value={kpi.month_revenue} prefix="¥" precision={0} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card>
              <Statistic title="本月新客户" value={kpi.new_customers} prefix={<TeamOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card>
              <Statistic title="活跃商机" value={kpi.open_opportunities} prefix={<ThunderboltOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card>
              <Statistic title="待采购订单" value={kpi.pending_purchase_orders} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card>
              <Statistic title="应收未收" value={kpi.outstanding_ar} prefix="¥" precision={0} valueStyle={{ color: kpi.outstanding_ar > 0 ? "#cf1322" : "#52c41a" }} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card>
              <Statistic title="低库存预警" value={kpi.low_stock_items} valueStyle={{ color: kpi.low_stock_items > 0 ? "#ff4d4f" : "#52c41a" }} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card>
              <Statistic title="产品总数" value={kpi.total_products} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card>
              <Statistic title="客户总数" value={kpi.total_customers} prefix={<TeamOutlined />} />
            </Card>
          </Col>
        </Row>
      )}

      {/* Customer Stats */}
      {stats && widgetPrefs.customer_stats?.enabled !== false && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="客户总数" value={stats.total} prefix={<TeamOutlined />} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="逾期跟进" value={overdue.length} prefix={<WarningOutlined />} valueStyle={{ color: overdue.length > 0 ? "#cf1322" : "#52c41a" }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="即将拜访" value={upcomingVisits.length} prefix={<CalendarOutlined />} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="最近动态" value={recentActivity.length} prefix={<ThunderboltOutlined />} />
            </Card>
          </Col>
        </Row>
      )}

      {/* Charts */}
      {stats && widgetPrefs.industry_chart?.enabled !== false && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="客户行业分布" size="small">
              {(stats.by_industry?.length ?? 0) > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={stats.by_industry} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90}>
                      {stats.by_industry.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : <Empty description="暂无数据" />}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="客户等级分布" size="small">
              {(stats.by_level?.length ?? 0) > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={stats.by_level}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#1890ff" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <Empty description="暂无数据" />}
            </Card>
          </Col>
        </Row>
      )}

      {stats && (stats.monthly?.length ?? 0) > 0 && widgetPrefs.monthly_trend?.enabled !== false && (
        <Card title="月度新增客户趋势" size="small" style={{ marginTop: 16 }}>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stats.monthly}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#52c41a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Overdue FollowUps */}
      {overdue.length > 0 && widgetPrefs.overdue_followups?.enabled !== false && (
        <Card title={<span><WarningOutlined style={{ marginRight: 8, color: "var(--color-error, #cf1322)" }} />逾期跟进</span>} size="small" style={{ marginTop: 16 }}>
          <Table
            rowKey="id"
            dataSource={overdue}
            columns={[
              { title: "客户", dataIndex: "customer_name", ellipsis: true },
              { title: "跟进方式", dataIndex: "method", width: 80 },
              { title: "计划时间", dataIndex: "planned_at", width: 100, render: (v: string) => v?.slice(0, 10) },
              { title: "逾期天数", dataIndex: "overdue_days", width: 80, render: (v: number) => <StatusTag status={`${v}天`} tone="danger" /> },
              { title: "负责人", dataIndex: "owner", width: 80 },
            ]}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* Upcoming Visits */}
      {upcomingVisits.length > 0 && widgetPrefs.upcoming_visits?.enabled !== false && (
        <Card title={<span><CalendarOutlined style={{ marginRight: 8 }} />未来14天拜访计划</span>} size="small" style={{ marginTop: 16 }}>
          <Table
            rowKey="id"
            dataSource={upcomingVisits}
            columns={[
              { title: "客户ID", dataIndex: "customer_id", width: 80 },
              { title: "标题", dataIndex: "title", ellipsis: true },
              { title: "方式", dataIndex: "type", width: 80 },
              { title: "日期", dataIndex: "visit_date", width: 100, render: (v: string) => v?.slice(0, 10) },
              {
                title: "状态", dataIndex: "status", width: 80,
                render: (v: string) => (
                  <StatusTag
                    status={v}
                    tone={v === "completed" ? "success" : v === "cancelled" ? "danger" : "info"}
                    label={v === "planned" ? "计划中" : v === "completed" ? "已完成" : "已取消"}
                  />
                ),
              },
            ]}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* Recent Activity */}
      {recentActivity.length > 0 && widgetPrefs.recent_activity?.enabled !== false && (
        <Card title="最近动态" size="small" style={{ marginTop: 16 }}>
          <Timeline
            items={recentActivity.map((log) => ({
              children: (
                <div>
                  <Typography.Text strong>{log.customer_name}</Typography.Text>
                  <span style={{ marginLeft: 8, fontSize: 12, color: "#888" }}>
                    {log.summary || log.action}
                  </span>
                  <div style={{ fontSize: 11, color: "#bbb" }}>
                    {log.created_at?.slice(0, 19)} {log.operator ? `· ${log.operator}` : ""}
                  </div>
                </div>
              ),
            }))}
          />
        </Card>
      )}

      {/* AI Global 360 */}
      {widgetPrefs.global_360?.enabled !== false && (
      <Card style={{ marginTop: 24 }}
        title={<><AimOutlined style={{ marginRight: 8 }} />AI 全局诊断 (Global 360)</>}
        extra={<Button icon={<ReloadOutlined />} loading={g360Loading} onClick={async () => {
          setG360Loading(true);
          try { const r = await orchestrateGlobal360(); setGlobal360(r.data.data); } catch {}
          finally { setG360Loading(false); }
        }}>重新诊断</Button>}
      >
        {global360 ? (
          <div>
            <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 24 }}>
              <Col xs={24} sm={8} style={{ textAlign: "center" }}>
                <Progress
                  type="circle"
                  percent={global360.enterprise_health_score}
                  strokeColor={
                    global360.enterprise_health_score >= 80 ? "#52c41a" :
                    global360.enterprise_health_score >= 60 ? "#faad14" : "#cf1322"
                  }
                  format={(pct) => (
                    <span style={{ fontSize: 24, fontWeight: 700 }}>
                      {pct}<div style={{ fontSize: 12, fontWeight: 400, color: "#888" }}>健康分</div>
                    </span>
                  )}
                  size={160}
                />
              </Col>
              <Col xs={24} sm={16}>
                <Typography.Paragraph style={{ fontSize: 15, marginBottom: 8, whiteSpace: "pre-wrap" }}>
                  {global360.executive_summary}
                </Typography.Paragraph>
                {global360.focus_areas?.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <Typography.Text strong style={{ marginRight: 8 }}>重点关注：</Typography.Text>
                    {global360.focus_areas.map((area, i) => (
                      <StatusTag key={i} status={area} tone="info" style={{ marginBottom: 4 }} />
                    ))}
                  </div>
                )}
              </Col>
            </Row>

            <Collapse
              size="small"
              defaultActiveKey={["kpi", "opportunities"]}
              items={[
                global360.kpi_health.length > 0 ? {
                  key: "kpi",
                  label: <Badge status={global360.kpi_health.some(k => k.status === "预警" || k.status === "warning" || k.status === "red") ? "error" : "success"} text={`KPI 健康度 (${global360.kpi_health.length})`} />,
                  children: (
                    <Table
                      rowKey="kpi"
                      dataSource={global360.kpi_health}
                      columns={[
                        { title: "指标", dataIndex: "kpi", width: 140 },
                        { title: "当前值", dataIndex: "current", width: 100 },
                        { title: "目标值", dataIndex: "target", width: 100 },
                        {
                          title: "状态", dataIndex: "status", width: 90,
                          render: (v: string) => (
                            <Badge
                              status={
                                v === "优秀" || v === "healthy" || v === "green" ? "success" :
                                v === "关注" || v === "warning" || v === "yellow" ? "warning" :
                                v === "预警" || v === "critical" || v === "red" ? "error" : "default"
                              }
                              text={v}
                            />
                          ),
                        },
                      ]}
                      pagination={false}
                      size="small"
                    />
                  ),
                } : null,

                global360.top_opportunities.length > 0 ? {
                  key: "opportunities",
                  label: <span>最佳商机 ({global360.top_opportunities.length})</span>,
                  children: (
                    <Table
                      rowKey={(_, i) => String(i)}
                      dataSource={global360.top_opportunities}
                      columns={[
                        { title: "领域", dataIndex: "area", width: 100 },
                        { title: "描述", dataIndex: "description", ellipsis: true },
                        {
                          title: "潜在价值", dataIndex: "potential_value", width: 110,
                          render: (v: number) => `¥${v?.toLocaleString() ?? 0}`,
                        },
                        { title: "投入", dataIndex: "effort", width: 70 },
                        { title: "时间窗口", dataIndex: "timeframe", width: 100 },
                      ]}
                      pagination={false}
                      size="small"
                    />
                  ),
                } : null,

                global360.top_risks.length > 0 ? {
                  key: "risks",
                  label: <span style={{ color: "#cf1322" }}>主要风险 ({global360.top_risks.length})</span>,
                  children: (
                    <Table
                      rowKey={(_, i) => String(i)}
                      dataSource={global360.top_risks}
                      columns={[
                        { title: "领域", dataIndex: "area", width: 100 },
                        { title: "描述", dataIndex: "description", ellipsis: true },
                        {
                          title: "严重程度", dataIndex: "severity", width: 90,
                          render: (v: string) => (
                            <StatusTag
                              status={v}
                              tone={v.includes("高") || v === "high" ? "danger" : v.includes("中") || v === "medium" ? "warning" : "info"}
                            />
                          ),
                        },
                        { title: "可能性", dataIndex: "probability", width: 80 },
                        { title: "缓解措施", dataIndex: "mitigation", ellipsis: true },
                      ]}
                      pagination={false}
                      size="small"
                    />
                  ),
                } : null,

                global360.strategic_recommendations.length > 0 ? {
                  key: "recommendations",
                  label: <span>战略建议 ({global360.strategic_recommendations.length})</span>,
                  children: (
                    <List
                      size="small"
                      dataSource={global360.strategic_recommendations}
                      renderItem={(r) => (
                        <List.Item style={{ padding: "6px 0" }}>
                          <List.Item.Meta
                            title={
                              <span>
                                <StatusTag
                                  status={r.priority}
                                  tone={r.priority === "高" || r.priority === "high" ? "danger" : r.priority === "中" || r.priority === "medium" ? "warning" : "info"}
                                  color="default"
                                />
                                <Tag style={{ marginRight: 8 }}>{r.domain}</Tag>
                                <Typography.Text strong>{r.recommendation}</Typography.Text>
                              </span>
                            }
                            description={<Typography.Text type="secondary">{r.rationale}</Typography.Text>}
                          />
                        </List.Item>
                      )}
                    />
                  ),
                } : null,

                global360.cross_domain_correlations?.length > 0 ? {
                  key: "correlations",
                  label: <span>跨域关联 ({global360.cross_domain_correlations.length})</span>,
                  children: (
                    <Table
                      rowKey={(_, i) => String(i)}
                      dataSource={global360.cross_domain_correlations}
                      columns={[
                        { title: "域", dataIndex: "domains", width: 150 },
                        { title: "发现", dataIndex: "finding", ellipsis: true },
                        { title: "显著性", dataIndex: "significance", width: 100 },
                      ]}
                      pagination={false}
                      size="small"
                    />
                  ),
                } : null,
              ].filter(Boolean) as { key: string; label: React.ReactNode; children: React.ReactNode }[]}
            />
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: 24 }}>
            {g360Loading ? <Spin tip="AI 正在分析企业全局数据..." /> : <Empty description="AI 诊断暂不可用，可稍后重试" />}
          </div>
        )}
      </Card>
      )}

      {/* Daily Report */}
      {widgetPrefs.daily_report?.enabled !== false && (
      <Card
        title={<><CalendarOutlined style={{ marginRight: 8 }} />每日经营报告</>}
        size="small"
        style={{ marginTop: 16 }}
        extra={
          <Button icon={<ReloadOutlined />} loading={drLoading} onClick={async () => {
            setDrLoading(true);
            try { const r = await getDailyReport(); setDailyReport(r.data.data as DailyReport); } catch {}
            finally { setDrLoading(false); }
          }}>刷新</Button>
        }
      >
        {dailyReport ? (
          <div>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={18}>
                <Paragraph style={{ fontSize: 14, margin: 0 }}>
                  <StatusTag
                    status={dailyReport.mood}
                    tone={dailyReport.mood === "良好" ? "success" : dailyReport.mood === "需关注" ? "danger" : "warning"}
                  />
                  {dailyReport.ai_summary}
                </Paragraph>
                {dailyReport.top_action && (
                  <Paragraph style={{ marginTop: 8 }}>
                    <Text strong>建议: </Text><Text>{dailyReport.top_action}</Text>
                  </Paragraph>
                )}
              </Col>
              <Col xs={24} sm={6}>
                <Row gutter={[8, 8]}>
                  <Col span={12}><Statistic title="今日订单" value={dailyReport.metrics.orders_today} suffix="单" /></Col>
                  <Col span={12}><Statistic title="今日营收" value={dailyReport.metrics.revenue_today} prefix="¥" precision={0} /></Col>
                  <Col span={12}><Statistic title="新客户" value={dailyReport.metrics.new_customers} /></Col>
                  <Col span={12}><Statistic title="低库存" value={dailyReport.metrics.low_stock_items} valueStyle={{ color: dailyReport.metrics.low_stock_items > 0 ? "#ff4d4f" : undefined }} /></Col>
                </Row>
              </Col>
            </Row>
          </div>
        ) : (
          <Text type="secondary" style={{ display: "block", textAlign: "center", padding: 16 }}>
            点击刷新生成今日经营报告
          </Text>
        )}
      </Card>
      )}

      {/* Widget Customization Drawer */}
      <Drawer
        title="自定义仪表板"
        open={widgetDrawerOpen}
        onClose={() => {
          // Reset to saved state when closing without saving
          try {
            const saved = localStorage.getItem("dashboard_widgets");
            if (saved) setWidgetPrefs({ ...DEFAULT_WIDGETS, ...JSON.parse(saved) });
          } catch {}
          setWidgetDrawerOpen(false);
        }}
        width={360}
        extra={
          <Button type="primary" loading={widgetSaving} onClick={saveWidgetPrefs}>
            保存
          </Button>
        }
      >
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          {Object.entries(widgetPrefs).map(([key, pref]) => (
            <Row key={key} justify="space-between" align="middle">
              <Col>
                <Text>{pref.title}</Text>
              </Col>
              <Col>
                <Switch
                  checked={pref.enabled}
                  onChange={(checked) =>
                    setWidgetPrefs((prev) => ({
                      ...prev,
                      [key]: { ...prev[key], enabled: checked },
                    }))
                  }
                />
              </Col>
            </Row>
          ))}
          <Text type="secondary" style={{ fontSize: 12 }}>
            开启或关闭仪表板上的各个模块，点击保存生效。偏好会同步到您的账号。
          </Text>
        </Space>
      </Drawer>
    </div>
  );
}
