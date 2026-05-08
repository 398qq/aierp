import { useEffect, useState } from "react";
import { Row, Col, Card, Statistic, Typography, Table, Spin, Tag, Timeline, Button, List, Progress, Collapse, Empty, Space, Badge } from "antd";
import {
  TeamOutlined, ThunderboltOutlined, CalendarOutlined, ReloadOutlined, AimOutlined, WarningOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../../store/auth";
import { getDashboardStats, getUpcomingVisits, getRecentActivity, getOverdueFollowUps, orchestrateGlobal360 } from "../../api";
import type { DashboardStats, Visit, CustomerLog, Global360, OverdueFollowUp } from "../../types";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

const { Title, Text } = Typography;
const COLORS = ["#1890ff", "#52c41a", "#faad14", "#ff4d4f", "#722ed1", "#13c2c2"];

export default function Dashboard() {
  const username = useAuthStore((s) => s.username);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [upcomingVisits, setUpcomingVisits] = useState<Visit[]>([]);
  const [recentActivity, setRecentActivity] = useState<CustomerLog[]>([]);
  const [overdue, setOverdue] = useState<OverdueFollowUp[]>([]);
  const [loading, setLoading] = useState(true);
  const [global360, setGlobal360] = useState<Global360 | null>(null);
  const [g360Loading, setG360Loading] = useState(false);

  useEffect(() => {
    Promise.all([
      getDashboardStats(),
      getUpcomingVisits(14),
      getRecentActivity(10),
      getOverdueFollowUps(),
      orchestrateGlobal360().then((r) => setGlobal360(r.data.data)).catch(() => {}),
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
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  return (
    <div>
      <Title level={4}>欢迎回来，{username}</Title>

      <Space wrap style={{ marginBottom: 16 }}>
        <Text type="secondary">AI 问答建议：</Text>
        {["本月销售趋势如何？", "哪些客户有流失风险？", "库存周转率最高的产品？", "逾期付款情况？", "供应商准时交付率排名？"].map((q) => (
          <Tag key={q} color="processing" style={{ cursor: "pointer" }}
            onClick={() => {
              const btn = document.querySelector<HTMLElement>('[class*="floating"]') || document.querySelector('[style*="fixed"][style*="bottom"]');
              if (btn) btn.click();
            }}>
            {q}
          </Tag>
        ))}
      </Space>

      {/* Customer Stats */}
      {stats && (
        <>
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

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={12}>
              <Card title="客户行业分布" size="small">
                {stats.by_industry.length > 0 ? (
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
                {stats.by_level.length > 0 ? (
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

          {stats.monthly.length > 0 && (
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
        </>
      )}

      {/* Overdue FollowUps */}
      {overdue.length > 0 && (
        <Card title={<span><WarningOutlined style={{ marginRight: 8, color: "#cf1322" }} />逾期跟进</span>} size="small" style={{ marginTop: 16 }}>
          <Table
            rowKey="id"
            dataSource={overdue}
            columns={[
              { title: "客户", dataIndex: "customer_name", ellipsis: true },
              { title: "跟进方式", dataIndex: "method", width: 80 },
              { title: "计划时间", dataIndex: "planned_at", width: 100, render: (v: string) => v?.slice(0, 10) },
              { title: "逾期天数", dataIndex: "overdue_days", width: 80, render: (v: number) => <Tag color="red">{v}天</Tag> },
              { title: "负责人", dataIndex: "owner", width: 80 },
            ]}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* Upcoming Visits */}
      {upcomingVisits.length > 0 && (
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
                render: (v: string) => <Tag color={v === "completed" ? "green" : v === "cancelled" ? "red" : "blue"}>{v === "planned" ? "计划中" : v === "completed" ? "已完成" : "已取消"}</Tag>,
              },
            ]}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* Recent Activity */}
      {recentActivity.length > 0 && (
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
                {global360.focus_areas.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <Typography.Text strong style={{ marginRight: 8 }}>重点关注：</Typography.Text>
                    {global360.focus_areas.map((area, i) => (
                      <Tag key={i} color="blue" style={{ marginBottom: 4 }}>{area}</Tag>
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
                            <Tag color={v.includes("高") || v === "high" ? "red" : v.includes("中") || v === "medium" ? "orange" : "blue"}>{v}</Tag>
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
                                <Tag color={r.priority === "高" || r.priority === "high" ? "red" : r.priority === "中" || r.priority === "medium" ? "orange" : "blue"} style={{ marginRight: 8 }}>{r.priority}</Tag>
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
          <div style={{ textAlign: "center", padding: 24 }}><Spin tip="AI 正在分析企业全局数据..." /></div>
        )}
      </Card>
    </div>
  );
}
