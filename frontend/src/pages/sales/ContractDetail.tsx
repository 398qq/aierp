import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Button, Space, Tag, Spin, Alert, Empty } from "antd";
import { ArrowLeftOutlined, EditOutlined } from "@ant-design/icons";
import { getContract } from "../../api";
import type { Contract } from "../../types";
import { CustomerLink } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" }, signed: { color: "blue", label: "已签署" },
  active: { color: "green", label: "履行中" }, expired: { color: "orange", label: "已到期" }, terminated: { color: "red", label: "已终止" },
};

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [ct, setCt] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getContract(Number(id)).then((r) => setCt(r.data.data))
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!ct) return <Empty description="合同不存在" />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/contracts")}>返回</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/contracts/${ct.id}/edit`)}>编辑</Button>
      </Space>
      <Card title={ct.contract_no || `合同 #${ct.id}`} extra={<Tag color={STATUS[ct.status]?.color}>{STATUS[ct.status]?.label || ct.status}</Tag>}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="标题">{ct.title}</Descriptions.Item>
          <Descriptions.Item label="金额">¥{ct.amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="客户"><CustomerLink id={ct.customer_id} /></Descriptions.Item>
          <Descriptions.Item label="关联订单">{ct.sales_order_id || "-"}</Descriptions.Item>
          <Descriptions.Item label="签署日期">{ct.signed_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="到期日期">{ct.expire_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="文件">{ct.file_url || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{ct.notes || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
