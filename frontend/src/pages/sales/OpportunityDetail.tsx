import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Alert, Button, Card, Descriptions, Empty, Progress, Space, Spin, Switch, Tag, Typography } from "antd";
import { StatusTag } from "../../ui";
import { ArrowLeftOutlined, DollarOutlined, EditOutlined, FileTextOutlined } from "@ant-design/icons";
import { getOpportunity } from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { Opportunity } from "../../types";
import { CustomerLink, ErpStatusTimeline, MetricBand, SalesModuleShell, SalesStatusTag, money, shortDate, stageLabel } from "./salesUi";

const STATUS_STEPS = [
  { key: "lead", label: "线索" },
  { key: "qualification", label: "需求确认" },
  { key: "proposal", label: "方案/报价" },
  { key: "negotiation", label: "谈判" },
  { key: "closed_won", label: "赢单" },
];

export default function OpportunityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [opp, setOpp] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeAi, setIncludeAi] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getOpportunity(Number(id), includeAi)
      .then((r) => setOpp(r.data.data))
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id, includeAi]);

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
            title="商机概览"
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
              <Descriptions.Item label="预计成交">{shortDate(opp.expected_close_date)}</Descriptions.Item>
              <Descriptions.Item label="负责人">{opp.assigned_to || "-"}</Descriptions.Item>
              <Descriptions.Item label="来源">{opp.source || "-"}</Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>{opp.description || "-"}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{opp.notes || "-"}</Descriptions.Item>
            </Descriptions>
          </Card>

          {includeAi && <SalesAIInsight aiData={opp.ai} />}
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
