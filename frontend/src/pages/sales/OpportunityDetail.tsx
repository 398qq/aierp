import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Descriptions, Card, Button, Space, Tag, Spin, Alert, Empty } from "antd";
import { ArrowLeftOutlined, EditOutlined } from "@ant-design/icons";
import { getOpportunity } from "../../api";
import type { Opportunity } from "../../types";

const stageColors: Record<string, string> = {
  lead: "default", qualified: "blue", proposal: "orange", negotiation: "purple",
  won: "green", lost: "red",
};

export default function OpportunityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getOpportunity(Number(id))
      .then((r) => setData(r.data.data as Opportunity))
      .catch((e) => setError((e as Error).message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!data) return <Empty description="未找到该机会" />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/opportunities")}>返回列表</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/opportunities/${data.id}/edit`)}>编辑</Button>
      </Space>
      <Card title={data.name}>
        <Descriptions column={2}>
          <Descriptions.Item label="客户ID">{data.customer_id}</Descriptions.Item>
          <Descriptions.Item label="阶段"><Tag color={stageColors[data.stage] || "default"}>{data.stage}</Tag></Descriptions.Item>
          <Descriptions.Item label="金额">¥{data.amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="概率">{data.probability}%</Descriptions.Item>
          <Descriptions.Item label="预计成交日期">{data.expected_close_date || "-"}</Descriptions.Item>
          <Descriptions.Item label="实际成交日期">{data.actual_close_date || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{data.notes || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{data.created_at}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
