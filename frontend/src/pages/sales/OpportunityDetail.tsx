import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Alert, Button, Card, Descriptions, Empty, List, Progress, Space, Spin, Switch, Tag, Timeline, Typography } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { ArrowLeftOutlined, AuditOutlined, CalendarOutlined, DollarOutlined, EditOutlined, FileTextOutlined, PlusOutlined } from "@ant-design/icons";
import { getOpportunity, getOpportunityAudit, getOpportunityBusinessChain, getOpportunityFollowUps } from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { FollowUp, Opportunity, OpportunityAuditItem, OpportunityAuditTrail, OpportunityBusinessChain } from "../../types";
import { CustomerLink, ErpStatusTimeline, MetricBand, SalesModuleShell, SalesStatusTag, money, shortDate, stageLabel } from "./salesUi";

const STATUS_STEPS = [
  { key: "lead", label: "线索" },
  { key: "qualified", label: "需求确认" },
  { key: "proposal", label: "方案/报价" },
  { key: "negotiation", label: "谈判" },
  { key: "closed_won", label: "赢单" },
];

const followUpDate = (value: string | null) => value
  ? new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
  : "未计划";

const AUDIT_FIELD_LABELS: Record<string, string> = {
  title: "商机名称",
  description: "描述",
  status: "状态",
  stage: "阶段",
  amount: "预计金额",
  win_probability: "赢单概率",
  expected_close_date: "预计成交日期",
  assigned_to: "负责人",
  source: "来源",
  notes: "备注",
  product_id: "关联产品",
};

const auditValue = (item: OpportunityAuditItem, value: string | null) => {
  if (!value) return "未填写";
  if (item.field_name === "stage") return stageLabel[value] || value;
  if (item.field_name === "amount") return money(Number(value));
  if (item.field_name === "win_probability") return `${value}%`;
  if (item.field_name === "expected_close_date") return shortDate(value);
  return value;
};

const auditTitle = (item: OpportunityAuditItem) => {
  if (item.action === "create") return "创建商机";
  if (item.action === "stage_change") return "推进商机阶段";
  if (item.action === "status_change") return "变更商机状态";
  if (item.action === "delete") return "删除商机";
  return `修改${AUDIT_FIELD_LABELS[item.field_name] || item.field_name}`;
};

export default function OpportunityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [opp, setOpp] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeAi, setIncludeAi] = useState(true);
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [followUpsLoading, setFollowUpsLoading] = useState(false);
  const [businessChain, setBusinessChain] = useState<OpportunityBusinessChain | null>(null);
  const [chainLoading, setChainLoading] = useState(false);
  const [auditTrail, setAuditTrail] = useState<OpportunityAuditTrail | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getOpportunity(Number(id), includeAi)
      .then((r) => setOpp(r.data.data))
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id, includeAi]);

  useEffect(() => {
    const opportunityId = Number(id);
    if (!opportunityId) return;
    setFollowUpsLoading(true);
    setChainLoading(true);
    setAuditLoading(true);
    getOpportunityFollowUps(opportunityId)
      .then((r) => setFollowUps(r.data.data || []))
      .catch(() => setFollowUps([]))
      .finally(() => setFollowUpsLoading(false));
    getOpportunityBusinessChain(opportunityId)
      .then((r) => setBusinessChain(r.data.data))
      .catch(() => setBusinessChain(null))
      .finally(() => setChainLoading(false));
    getOpportunityAudit(opportunityId)
      .then((r) => setAuditTrail(r.data.data))
      .catch(() => setAuditTrail(null))
      .finally(() => setAuditLoading(false));
  }, [id]);

  const weightedAmount = useMemo(
    () => Number(opp?.amount || 0) * Number(opp?.win_probability || 0) / 100,
    [opp]
  );

  if (loading) {
    return (
      <SalesModuleShell title="商机详情" activeKey="opportunities">
        <Spin style={{ display: "block", margin: "100px auto" }} />
      </SalesModuleShell>
    );
  }

  if (error) {
    return (
      <SalesModuleShell title="商机详情" activeKey="opportunities">
        <Alert type="error" message={error} />
      </SalesModuleShell>
    );
  }

  if (!opp) {
    return (
      <SalesModuleShell title="商机详情" activeKey="opportunities">
        <Empty description="商机不存在" />
      </SalesModuleShell>
    );
  }

  return (
    <SalesModuleShell
      title={opp.title}
      subtitle="查看商机推进状态、成交概率和下一步动作"
      activeKey="opportunities"
      extra={(
        <>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/opportunities")}>返回</Button>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/opportunities/${opp.id}/edit`)}>编辑</Button>
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </>
      )}
    >
      <MetricBand
        items={[
          { title: "预计金额", value: opp.amount || 0, prefix: "¥", precision: 0 },
          { title: "加权金额", value: weightedAmount, prefix: "¥", precision: 0 },
          { title: "赢单概率", value: opp.win_probability || 0, suffix: "%" },
          { title: "阶段", value: stageLabel[opp.stage || ""] || opp.stage || "-" },
          { title: "预计成交", value: opp.expected_close_date ? shortDate(opp.expected_close_date) : "-" },
        ]}
      />

      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/opportunities")}>返回</Button>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/opportunities/${opp.id}/edit`)}>编辑</Button>
          <Button
            type="primary"
            icon={<FileTextOutlined />}
            onClick={() => navigate(`/sales/quotations/new?customer_id=${opp.customer_id}&opportunity_id=${opp.id}`)}
          >
            创建报价
          </Button>
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </Space>
      </Card>

      <div className="erp-detail-two-column">
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Card
            title="商机经营表现"
            size="small"
            extra={(
              <Space>
                <SalesStatusTag value={opp.status} />
                <StatusTag tone="info">{stageLabel[opp.stage || ""] || opp.stage || "-"}</StatusTag>
              </Space>
            )}
          >
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 16 }}>
              <div style={{ border: "1px solid #edf0f3", borderRadius: 6, padding: 12 }}>
                <Typography.Text type="secondary">预计金额</Typography.Text>
                <Typography.Title level={4} style={{ margin: "4px 0 0" }}>{money(opp.amount)}</Typography.Title>
              </div>
              <div style={{ border: "1px solid #edf0f3", borderRadius: 6, padding: 12 }}>
                <Typography.Text type="secondary">加权金额</Typography.Text>
                <Typography.Title level={4} style={{ margin: "4px 0 0" }}>{money(weightedAmount)}</Typography.Title>
              </div>
              <div style={{ border: "1px solid #edf0f3", borderRadius: 6, padding: 12 }}>
                <Typography.Text type="secondary">赢单概率</Typography.Text>
                <Progress percent={Number(opp.win_probability || 0)} size="small" />
              </div>
            </div>

            <Descriptions column={2} size="small">
              <Descriptions.Item label="客户"><CustomerLink id={opp.customer_id} /></Descriptions.Item>
              <Descriptions.Item label="商机编号">OPP-{String(opp.id).padStart(6, "0")}</Descriptions.Item>
              <Descriptions.Item label="预计成交">{shortDate(opp.expected_close_date)}</Descriptions.Item>
              <Descriptions.Item label="负责人">{opp.assigned_to || "-"}</Descriptions.Item>
              <Descriptions.Item label="来源">{opp.source || "-"}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{shortDate(opp.created_at)}</Descriptions.Item>
              <Descriptions.Item label="最近更新">{shortDate(opp.updated_at || opp.created_at)}</Descriptions.Item>
              <Descriptions.Item label="关联产品">{opp.product_name || (opp.product_id ? `产品 #${opp.product_id}` : "-" )}</Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>{opp.description || "-"}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{opp.notes || "-"}</Descriptions.Item>
            </Descriptions>
          </Card>

          {includeAi && <SalesAIInsight aiData={opp.ai} />}

          <Card
            size="small"
            title={<><CalendarOutlined /> 跟进与今日待办</>}
            extra={(
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                onClick={() => navigate(`/customers/${opp.customer_id}/follow-ups/new?opportunity_id=${opp.id}`)}
              >
                添加跟进
              </Button>
            )}
          >
            {followUpsLoading ? <List loading /> : followUps.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无跟进记录" />
            ) : (
              <List
                size="small"
                dataSource={followUps}
                renderItem={(item) => {
                  const overdue = item.status !== "completed" && item.planned_at && new Date(item.planned_at).getTime() < Date.now();
                  return (
                    <List.Item
                      actions={[
                        <Button key="edit" type="link" size="small" onClick={() => navigate(`/customers/${opp.customer_id}/follow-ups/${item.id}/edit?opportunity_id=${opp.id}`)}>编辑</Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={(
                          <Space size={6} wrap>
                            <Typography.Text strong>{item.content || "未填写跟进内容"}</Typography.Text>
                            <Tag color={item.status === "completed" ? "green" : overdue ? "red" : "blue"}>{item.status === "completed" ? "已完成" : overdue ? "已超期" : "待跟进"}</Tag>
                            {item.priority === "high" && <Tag color="orange">高优先级</Tag>}
                          </Space>
                        )}
                        description={(
                          <Space size={12} wrap>
                            <span>{item.method || "未注明方式"}</span>
                            <span>计划：{followUpDate(item.planned_at)}</span>
                            {item.assigned_to && <span>负责人：{item.assigned_to}</span>}
                            {item.result && <span>结果：{item.result}</span>}
                          </Space>
                        )}
                      />
                    </List.Item>
                  );
                }}
              />
            )}
          </Card>

          <Card
            size="small"
            title="业务单据链"
            extra={(
              <Button
                type={businessChain?.summary.quotation_count ? "default" : "primary"}
                size="small"
                icon={<FileTextOutlined />}
                onClick={() => navigate(`/sales/quotations/new?customer_id=${opp.customer_id}&opportunity_id=${opp.id}`)}
              >
                创建新报价
              </Button>
            )}
            loading={chainLoading}
          >
            {businessChain?.summary.quotation_count ? (
              <Alert
                showIcon
                type="info"
                message={`该商机已有 ${businessChain.summary.quotation_count} 份报价、${businessChain.summary.order_count} 份订单`}
                description="如客户需要修订方案，可创建新报价版本；已有报价转换订单时会返回原关联订单，避免重复生成。"
                style={{ marginBottom: 12 }}
              />
            ) : null}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8, marginBottom: 12 }}>
              <Card size="small"><Typography.Text type="secondary">报价数量</Typography.Text><Typography.Title level={5} style={{ margin: "4px 0 0" }}>{businessChain?.summary.quotation_count || 0}</Typography.Title></Card>
              <Card size="small"><Typography.Text type="secondary">报价金额</Typography.Text><Typography.Title level={5} style={{ margin: "4px 0 0" }}>{money(businessChain?.summary.quoted_amount || 0)}</Typography.Title></Card>
              <Card size="small"><Typography.Text type="secondary">订单金额</Typography.Text><Typography.Title level={5} style={{ margin: "4px 0 0" }}>{money(businessChain?.summary.ordered_amount || 0)}</Typography.Title></Card>
              <Card size="small"><Typography.Text type="secondary">报价转单率</Typography.Text><Typography.Title level={5} style={{ margin: "4px 0 0" }}>{businessChain?.summary.conversion_rate || 0}%</Typography.Title></Card>
            </div>
            <ProTable search={false} options={false}
              rowKey="id"
              size="small"
              pagination={false}
              locale={{ emptyText: "暂无关联报价" }}
              dataSource={businessChain?.quotations || []}
              columns={[
                { title: "报价单号", dataIndex: "number", render: (value: string, row: any) => <Typography.Link onClick={() => navigate(`/sales/quotations/${row.id}`)}>{value}</Typography.Link> },
                { title: "状态", dataIndex: "status", width: 100, render: (value: string) => <SalesStatusTag value={value} /> },
                { title: "金额", dataIndex: "amount", width: 120, align: "right", render: money },
                { title: "创建时间", dataIndex: "created_at", width: 120, render: shortDate },
                {
                  title: "关联订单",
                  key: "orders",
                  width: 180,
                  render: (_: unknown, row: any) => {
                    const orders = (businessChain?.orders || []).filter((item) => item.quotation?.id === row.id);
                    return orders.length ? (
                      <Space wrap size={4}>{orders.map((item) => <Button key={item.order.id} type="link" size="small" onClick={() => navigate(`/sales/orders/${item.order.id}`)}>{item.order.number}</Button>)}</Space>
                    ) : <Typography.Text type="secondary">未转订单</Typography.Text>;
                  },
                },
              ] as any}
            />
          </Card>
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
          <Card size="small" title={<><DollarOutlined /> 商机摘要</>}>
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">预计金额</Typography.Text>
                <Typography.Text strong>{money(opp.amount)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">加权金额</Typography.Text>
                <Typography.Text>{money(weightedAmount)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">赢单概率</Typography.Text>
                <Typography.Text>{opp.win_probability || 0}%</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">阶段</Typography.Text>
                <StatusTag tone="info">{stageLabel[opp.stage || ""] || opp.stage || "-"}</StatusTag>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">预计成交</Typography.Text>
                <Typography.Text>{shortDate(opp.expected_close_date)}</Typography.Text>
              </div>
            </Space>
          </Card>

          <Card size="small" title="状态流转">
            <ErpStatusTimeline
              currentStatus={opp.stage || opp.status}
              steps={STATUS_STEPS}
              createdAt={opp.created_at}
              lostStatus="closed_lost"
            />
          </Card>

          <Card
            size="small"
            title={<><AuditOutlined /> 变更轨迹</>}
            extra={<Typography.Text type="secondary">{auditTrail?.total || 0} 条</Typography.Text>}
            loading={auditLoading}
          >
            {auditTrail?.list.length ? (
              <Timeline
                items={auditTrail.list.slice(0, 12).map((item) => ({
                  color: item.event_type === "transition" ? "blue" : "gray",
                  children: (
                    <div>
                      <Space size={6} wrap>
                        <Typography.Text strong>{auditTitle(item)}</Typography.Text>
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          {new Date(item.occurred_at).toLocaleString("zh-CN")}
                        </Typography.Text>
                      </Space>
                      {item.action !== "create" ? (
                        <div style={{ marginTop: 2, fontSize: 12 }}>
                          <Typography.Text type="secondary">{auditValue(item, item.before)}</Typography.Text>
                          <Typography.Text type="secondary"> → </Typography.Text>
                          <Typography.Text>{auditValue(item, item.after)}</Typography.Text>
                        </div>
                      ) : null}
                      <Typography.Text type="secondary" style={{ display: "block", fontSize: 12 }}>
                        操作人：{item.actor || "系统"}
                      </Typography.Text>
                    </div>
                  ),
                }))}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无变更记录" />
            )}
          </Card>

          <Card size="small" title="下一步动作">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              {opp.stage === "proposal" ? (
                <Alert showIcon type="info" message="当前处于报价阶段，优先确认价格、交期和付款条件。" />
              ) : opp.stage === "negotiation" ? (
                <Alert showIcon type="info" message="当前处于谈判阶段，建议沉淀客户异议和让步边界。" />
              ) : (
                <Alert showIcon type="info" message="优先补齐客户预算、需求数量、决策链和竞品信息。" />
              )}
              <Button block type="primary" icon={<FileTextOutlined />} onClick={() => navigate(`/sales/quotations/new?customer_id=${opp.customer_id}&opportunity_id=${opp.id}`)}>
                基于商机创建报价
              </Button>
              {opp.customer_id ? (
                <Button block onClick={() => navigate(`/customers/${opp.customer_id}`)}>查看客户</Button>
              ) : null}
            </Space>
          </Card>
        </Space>
      </div>
    </SalesModuleShell>
  );
}
