import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Alert, Button, Card, Descriptions, Empty, Progress, Space, Spin, Switch, Tag, Typography } from "antd";
import { ArrowLeftOutlined, EditOutlined, FileTextOutlined } from "@ant-design/icons";
import { getOpportunity } from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { Opportunity } from "../../types";
import { CustomerLink, SalesModuleShell, SalesStatusTag, money, shortDate, stageLabel } from "./salesUi";

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
      )}
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 12, alignItems: "start" }}>
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Card
            title="商机概览"
            size="small"
            extra={(
              <Space>
                <SalesStatusTag value={opp.status} />
                <Tag color="blue">{stageLabel[opp.stage || ""] || opp.stage || "-"}</Tag>
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
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Card size="small" title="推进建议">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              <Typography.Text>
                {opp.stage === "proposal"
                  ? "当前处于报价阶段，优先确认价格、交期和付款条件。"
                  : opp.stage === "negotiation"
                    ? "当前处于谈判阶段，建议沉淀客户异议和让步边界。"
                    : "优先补齐客户预算、需求数量、决策链和竞品信息。"}
              </Typography.Text>
              <Button block type="primary" icon={<FileTextOutlined />} onClick={() => navigate(`/sales/quotations/new?customer_id=${opp.customer_id}&opportunity_id=${opp.id}`)}>
                基于商机创建报价
              </Button>
            </Space>
          </Card>
          {includeAi && <SalesAIInsight aiData={opp.ai} />}
        </Space>
      </div>
    </SalesModuleShell>
  );
}
