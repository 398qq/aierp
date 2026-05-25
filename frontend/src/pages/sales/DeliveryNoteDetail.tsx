import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Alert, Button, Card, Descriptions, Empty, message, Space, Spin, Switch, Table } from "antd";
import { ArrowLeftOutlined, EditOutlined } from "@ant-design/icons";
import { getDeliveryNote, updateDeliveryNote } from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { DeliveryNote } from "../../types";
import { CustomerLink, SalesModuleShell, SalesStatusTag, shortDate } from "./salesUi";

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
      .catch((err) => setError(err.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id, includeAi]);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!note) return <Empty description="发货单不存在" />;

  return (
    <SalesModuleShell
      title={note.delivery_no || `发货单 #${note.id}`}
      subtitle="发货单客户来自关联销售订单，发货后会触发库存扣减"
      activeKey="delivery"
      extra={
        <>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/delivery-notes")}>返回</Button>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/delivery-notes/${note.id}/edit`)}>编辑</Button>
          {note.status === "pending" && (
            <Button type="primary" onClick={async () => {
              try {
                await updateDeliveryNote(note.id, { status: "shipped" });
                message.success("已发货，库存已自动扣减");
                setNote({ ...note, status: "shipped" });
              } catch {
                message.error("操作失败");
              }
            }}>标记发货</Button>
          )}
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </>
      }
    >
      <Card title="发货信息" extra={<SalesStatusTag value={note.status} />}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="关联订单">#{note.sales_order_id}</Descriptions.Item>
          <Descriptions.Item label="客户"><CustomerLink id={note.customer_id} /></Descriptions.Item>
          <Descriptions.Item label="发货日期">{shortDate(note.delivery_date)}</Descriptions.Item>
          <Descriptions.Item label="签收日期">{shortDate(note.received_date)}</Descriptions.Item>
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
              { title: "数量", dataIndex: "quantity", width: 90 },
              { title: "备注", dataIndex: "notes", ellipsis: true },
            ]}
          />
        </Card>
      )}

      {includeAi && <SalesAIInsight aiData={note.ai} />}
    </SalesModuleShell>
  );
}
