import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Descriptions, Card, Spin, Alert, Empty, Popconfirm, message } from "antd";
import { ArrowLeftOutlined, EditOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { getDeliveryNote, deleteDeliveryNote, getDeliveryNoteItems, deleteDeliveryNoteItem } from "../../api";
import type { DeliveryNote, DeliveryNoteItem } from "../../types";

const statusColors: Record<string, string> = {
  pending: "orange", shipped: "cyan", delivered: "green", signed: "blue", cancelled: "red",
};

export default function DeliveryNoteDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DeliveryNote | null>(null);
  const [items, setItems] = useState<DeliveryNoteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [noteResp, itemsResp] = await Promise.all([
        getDeliveryNote(Number(id)),
        getDeliveryNoteItems(Number(id)),
      ]);
      setData(noteResp.data.data as DeliveryNote);
      setItems((itemsResp.data.data as DeliveryNoteItem[]) || []);
    } catch (e) { setError((e as Error).message || "加载失败"); } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [id]);

  const handleDelete = async () => {
    try { await deleteDeliveryNote(Number(id)); message.success("已删除"); navigate("/sales/delivery-notes"); }
    catch { message.error("删除失败"); }
  };

  const handleDeleteItem = async (itemId: number) => {
    try { await deleteDeliveryNoteItem(Number(id), itemId); message.success("已删除"); load(); }
    catch { message.error("删除失败"); }
  };

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!data) return <Empty description="未找到该送货单" />;

  const itemColumns = [
    { title: "产品ID", dataIndex: "product_id", width: 150 },
    { title: "数量", dataIndex: "quantity", width: 100 },
    {
      title: "操作", width: 80, render: (_: unknown, record: DeliveryNoteItem) => (
        <Popconfirm title="确定删除?" onConfirm={() => handleDeleteItem(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/delivery-notes")}>返回列表</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/delivery-notes/${data.id}/edit`)}>编辑</Button>
        <Popconfirm title="确定删除?" onConfirm={handleDelete}>
          <Button danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      </Space>
      <Card title={`送货单: ${data.note_no || "NO-" + data.id}`} style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="销售订单ID">{data.sales_order_id}</Descriptions.Item>
          <Descriptions.Item label="客户ID">{data.customer_id}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={statusColors[data.status] || "default"}>{data.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="送货日期">{data.delivery_date || "-"}</Descriptions.Item>
          <Descriptions.Item label="签收日期">{data.signed_at || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{data.notes || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{data.created_at}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="送货项" extra={<Button icon={<PlusOutlined />} onClick={() => navigate(`/sales/delivery-notes/${data.id}/edit`)}>管理送货项</Button>}>
        <Table rowKey="id" columns={itemColumns} dataSource={items} pagination={false} />
      </Card>
    </div>
  );
}
