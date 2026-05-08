import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Button, Space, Tag, Spin, Alert, Empty, Table, Switch } from "antd";
import { ArrowLeftOutlined, EditOutlined } from "@ant-design/icons";
import { getDeliveryNote } from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { DeliveryNote } from "../../types";

const STATUS: Record<string, { color: string; label: string }> = {
  pending: { color: "default", label: "待发货" }, shipped: { color: "blue", label: "已发货" },
  delivered: { color: "green", label: "已签收" }, returned: { color: "red", label: "已退回" },
};

export default function DeliveryNoteDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [note, setNote] = useState<DeliveryNote | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeAi, setIncludeAi] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getDeliveryNote(Number(id), includeAi)
      .then((r) => setNote(r.data.data))
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id, includeAi]);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!note) return <Empty description="发货单不存在" />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/delivery-notes")}>返回</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/delivery-notes/${note.id}/edit`)}>编辑</Button>
        <Space>
          <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
          <span style={{ fontSize: 13 }}>AI</span>
        </Space>
      </Space>

      <Card title={note.delivery_no || `发货单 #${note.id}`} extra={<Tag color={STATUS[note.status]?.color}>{STATUS[note.status]?.label || note.status}</Tag>}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="关联订单">{note.sales_order_id}</Descriptions.Item>
          <Descriptions.Item label="客户ID">{note.customer_id}</Descriptions.Item>
          <Descriptions.Item label="发货日期">{note.delivery_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="签收日期">{note.received_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{note.notes || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>

      {note.items.length > 0 && (
        <Card title="发货明细" size="small" style={{ marginTop: 16 }}>
          <Table
            rowKey="id"
            dataSource={note.items}
            size="small"
            pagination={false}
            columns={[
              { title: "产品", dataIndex: "product_name", ellipsis: true },
              { title: "数量", dataIndex: "quantity", width: 80 },
              { title: "备注", dataIndex: "notes", ellipsis: true },
            ]}
          />
        </Card>
      )}

      {includeAi && <SalesAIInsight aiData={note.ai} />}
    </div>
  );
}
