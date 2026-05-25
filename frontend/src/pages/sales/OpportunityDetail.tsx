import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Button, Space, Tag, Spin, Alert, Empty, Switch, message } from "antd";
import { ArrowLeftOutlined, EditOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { getOpportunity } from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { Opportunity } from "../../types";
import { CustomerLink } from "./salesUi";

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

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!opp) return <Empty description="商机不存在" />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/opportunities")}>返回</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/opportunities/${opp.id}/edit`)}>编辑</Button>
        <Space>
          <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
          <span style={{ fontSize: 13 }}>AI</span>
        </Space>
      </Space>

      <Card title={opp.title} extra={<Tag color={opp.status === "active" ? "green" : opp.status === "won" ? "blue" : "red"}>{opp.status}</Tag>}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="客户"><CustomerLink id={opp.customer_id} /></Descriptions.Item>
          <Descriptions.Item label="金额">{opp.amount ? `¥${opp.amount.toLocaleString()}` : "-"}</Descriptions.Item>
          <Descriptions.Item label="阶段">{opp.stage || "-"}</Descriptions.Item>
          <Descriptions.Item label="赢单率">{opp.win_probability !== null ? `${opp.win_probability}%` : "-"}</Descriptions.Item>
          <Descriptions.Item label="预计成交">{opp.expected_close_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="负责人">{opp.assigned_to || "-"}</Descriptions.Item>
          <Descriptions.Item label="来源">{opp.source || "-"}</Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>{opp.description || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{opp.notes || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>

      {includeAi && <SalesAIInsight aiData={opp.ai} />}
    </div>
  );
}
