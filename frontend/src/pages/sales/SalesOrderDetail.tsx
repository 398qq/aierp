import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Descriptions, Card, Spin, Alert, Empty, Popconfirm, message } from "antd";
import { ArrowLeftOutlined, EditOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { getSalesOrder, deleteSalesOrder, getSalesOrderItems, deleteSalesOrderItem } from "../../api";
import type { SalesOrder, SalesOrderItem } from "../../types";

const statusColors: Record<string, string> = {
  pending: "orange", confirmed: "blue", shipped: "cyan", delivered: "green", cancelled: "red",
};

export default function SalesOrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<SalesOrder | null>(null);
  const [items, setItems] = useState<SalesOrderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [orderResp, itemsResp] = await Promise.all([
        getSalesOrder(Number(id)),
        getSalesOrderItems(Number(id)),
      ]);
      setData(orderResp.data.data as SalesOrder);
      setItems((itemsResp.data.data as SalesOrderItem[]) || []);
    } catch (e) { setError((e as Error).message || "加载失败"); } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [id]);

  const handleDelete = async () => {
    try { await deleteSalesOrder(Number(id)); message.success("已删除"); navigate("/sales/orders"); }
    catch { message.error("删除失败"); }
  };

  const handleDeleteItem = async (itemId: number) => {
    try { await deleteSalesOrderItem(Number(id), itemId); message.success("已删除"); load(); }
    catch { message.error("删除失败"); }
  };

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!data) return <Empty description="未找到该订单" />;

  const itemColumns = [
    { title: "产品ID", dataIndex: "product_id", width: 100 },
    { title: "数量", dataIndex: "quantity", width: 80 },
    { title: "单价", dataIndex: "unit_price", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
    { title: "金额", dataIndex: "amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
    {
      title: "操作", width: 80, render: (_: unknown, record: SalesOrderItem) => (
        <Popconfirm title="确定删除?" onConfirm={() => handleDeleteItem(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/orders")}>返回列表</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/orders/${data.id}/edit`)}>编辑</Button>
        <Popconfirm title="确定删除?" onConfirm={handleDelete}>
          <Button danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      </Space>
      <Card title={`销售订单: ${data.order_no || "NO-" + data.id}`} style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="客户ID">{data.customer_id}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={statusColors[data.status] || "default"}>{data.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="总金额">¥{data.total_amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="交货日期">{data.delivery_date || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{data.notes || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{data.created_at}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="订单项" extra={<Button icon={<PlusOutlined />} onClick={() => navigate(`/sales/orders/${data.id}/edit`)}>管理订单项</Button>}>
        <Table rowKey="id" columns={itemColumns} dataSource={items} pagination={false} />
      </Card>
    </div>
  );
}
