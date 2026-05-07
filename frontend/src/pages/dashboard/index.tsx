import { useEffect, useState } from "react";
import { Row, Col, Card, Statistic, Typography, Table, Spin, Tag, Timeline, Button, List, Progress, Collapse, Badge } from "antd";
import {
  TeamOutlined, DollarOutlined, ShoppingCartOutlined, ThunderboltOutlined,
  RiseOutlined, CalendarOutlined, AlertOutlined, ReloadOutlined, AimOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../../store/auth";
import { getDashboardOverview, getDashboardRealtime, getUpcomingVisits, getRecentActivity, scanWatchtower, orchestrateGlobal360 } from "../../api";
import type { DashboardOverview, DashboardRealtime, Visit, CustomerLog, WatchtowerResult, Global360 } from "../../types";

const { Title } = Typography;

export default function Dashboard() {
  const username = useAuthStore((s) => s.username);
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [realtime, setRealtime] = useState<DashboardRealtime | null>(null);
  const [upcomingVisits, setUpcomingVisits] = useState<Visit[]>([]);
  const [recentActivity, setRecentActivity] = useState<CustomerLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [watchtower, setWatchtower] = useState<WatchtowerResult | null>(null);
  const [wtLoading, setWtLoading] = useState(false);
  const [global360, setGlobal360] = useState<Global360 | null>(null);
  const [g360Loading, setG360Loading] = useState(false);

  useEffect(() => {
    Promise.all([
      getDashboardOverview(),
      getDashboardRealtime(),
      getUpcomingVisits(14),
      getRecentActivity(10),
    ])
      .then(([ov, rt, uv, ra]) => {
        setOverview(ov.data.data);
        setRealtime(rt.data.data);
        setUpcomingVisits((uv.data.data || []) as unknown as Visit[]);
        setRecentActivity((ra.data.data || []) as CustomerLog[]);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  return (
    <div>
      <Title level={4}>欢迎回来，{username}</Title>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="客户总数" value={overview?.total_customers || 0} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="今日订单" value={overview?.today_orders || 0} prefix={<ShoppingCartOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="今日销售额" value={overview?.today_order_amount || 0} prefix={<DollarOutlined />} precision={2} suffix="CNY" />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="活跃商机" value={overview?.active_opportunities || 0} prefix={<ThunderboltOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="已赢单额" value={overview?.won_amount || 0} prefix={<RiseOutlined />} precision={2} suffix="CNY" />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="今日新商机" value={overview?.today_opportunities || 0} prefix={<ThunderboltOutlined />} />
          </Card>
        </Col>
      </Row>

      {realtime && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="订单状态分布" size="small">
              <Table
                rowKey="status"
                dataSource={realtime.order_status}
                columns={[
                  { title: "状态", dataIndex: "status", width: 100 },
                  { title: "数量", dataIndex: "count", width: 80 },
                  { title: "金额", dataIndex: "amount", render: (v: number) => `¥${v.toLocaleString()}` },
                ]}
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
          <Col xs={24} lg={6}>
            <Card title="Top 客户" size="small">
              <Table
                rowKey="name"
                dataSource={realtime.top_customers}
                columns={[
                  { title: "客户", dataIndex: "name", ellipsis: true },
                  { title: "金额", dataIndex: "amount", render: (v: number) => `¥${v.toLocaleString()}` },
                ]}
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
          <Col xs={24} lg={6}>
            <Card title="Top 产品" size="small">
              <Table
                rowKey="name"
                dataSource={realtime.top_products}
                columns={[
                  { title: "产品", dataIndex: "name", ellipsis: true },
                  { title: "次数", dataIndex: "count", width: 60 },
                ]}
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      )}

      {upcomingVisits.length > 0 && (
        <Card title={<span><CalendarOutlined /> 未来14天拜访计划</span>} size="small" style={{ marginTop: 16 }}>
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

      <Card style={{ marginTop: 24 }}
        title={<><AlertOutlined style={{ marginRight: 8 }} />AI 全局监控 (Watchtower)</>}
        extra={<Button icon={<ReloadOutlined />} loading={wtLoading} onClick={async () => {
          setWtLoading(true);
          try { const r = await scanWatchtower(); setWatchtower(r.data.data as WatchtowerResult); } catch {}
          finally { setWtLoading(false); }
        }}>{watchtower ? "重新扫描" : "开始扫描"}</Button>}
      >
        {watchtower ? (
          <div>
            <Row gutter={[12, 12]}>
              <Col span={6}>
                <Statistic title="异常总数" value={watchtower.total_alerts} valueStyle={{ color: watchtower.severity === "紧急" ? "#cf1322" : watchtower.severity === "需关注" ? "#fa8c16" : "#52c41a" }} />
              </Col>
              <Col span={6}>
                <Statistic title="严重程度" value={watchtower.severity} />
              </Col>
              <Col span={12}>
                <Typography.Text>{watchtower.summary}</Typography.Text>
              </Col>
              {watchtower.top_actions.length > 0 && (
                <Col span={12}>
                  <Card size="small" type="inner" title="优先行动">
                    <List size="small" dataSource={watchtower.top_actions} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="red">{s}</Tag></List.Item>} />
                  </Card>
                </Col>
              )}
              {watchtower.risk_areas.length > 0 && (
                <Col span={12}>
                  <Card size="small" type="inner" title="风险领域">
                    <List size="small" dataSource={watchtower.risk_areas} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="orange">{s}</Tag></List.Item>} />
                  </Card>
                </Col>
              )}
              {watchtower.anomalies.churn_risk.length > 0 && (
                <Col span={12}>
                  <Card size="small" type="inner" title={`流失风险 (${watchtower.anomalies.churn_risk.length})`} style={{ background: "#fff2e8" }}>
                    {watchtower.anomalies.churn_risk.map(c => <Tag key={c.customer_id} color="red" style={{ marginBottom: 4 }}>{c.name} — {c.signal}</Tag>)}
                  </Card>
                </Col>
              )}
              {watchtower.anomalies.order_drop.length > 0 && (
                <Col span={12}>
                  <Card size="small" type="inner" title={`订单下降 (${watchtower.anomalies.order_drop.length})`} style={{ background: "#fffbe6" }}>
                    {watchtower.anomalies.order_drop.map(o => <Tag key={o.customer_id} color="orange" style={{ marginBottom: 4 }}>{o.name} ↓{o.drop_pct}%</Tag>)}
                  </Card>
                </Col>
              )}
              {watchtower.anomalies.low_stock.length > 0 && (
                <Col span={12}>
                  <Card size="small" type="inner" title={`低库存 (${watchtower.anomalies.low_stock.length})`}>
                    {watchtower.anomalies.low_stock.map(p => <Tag key={p.product_id} style={{ marginBottom: 4 }}>[{p.brand}] {p.product_name}: {p.qty}/{p.safety}</Tag>)}
                  </Card>
                </Col>
              )}
              {watchtower.anomalies.out_of_stock.length > 0 && (
                <Col span={12}>
                  <Card size="small" type="inner" title={`缺货 (${watchtower.anomalies.out_of_stock.length})`} style={{ background: "#fff1f0" }}>
                    {watchtower.anomalies.out_of_stock.map(p => <Tag key={p.product_id} color="red" style={{ marginBottom: 4 }}>[{p.brand}] {p.product_name}</Tag>)}
                  </Card>
                </Col>
              )}
            </Row>
          </div>
        ) : (
          <p>点击“开始扫描”让 AI 扫描系统异常（流失风险、订单下降、库存预警等），主动发现问题。</p>
        )}
      </Card>

      <Card style={{ marginTop: 24 }}
        title={<><AimOutlined style={{ marginRight: 8 }} />AI 全局诊断 (Global 360)</>}
        extra={<Button icon={<ReloadOutlined />} loading={g360Loading} onClick={async () => {
          setG360Loading(true);
          try { const r = await orchestrateGlobal360(); setGlobal360(r.data.data as Global360); } catch {}
          finally { setG360Loading(false); }
        }}>{global360 ? "重新诊断" : "开始诊断"}</Button>}
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
          <p>点击"开始诊断"让 AI 联合多个 Agent 执行企业全面诊断，生成健康评分、商机优先级、风险清单和战略建议。</p>
        )}
      </Card>
    </div>
  );
}
