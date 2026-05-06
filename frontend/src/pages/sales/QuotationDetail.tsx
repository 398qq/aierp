import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Descriptions, Card, Spin, Alert, Empty, Popconfirm, message } from "antd";
import { ArrowLeftOutlined, EditOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { getQuotation, deleteQuotation, getQuotationItems, deleteQuotationItem } from "../../api";
import type { Quotation, QuotationItem } from "../../types";

const statusColors: Record<string, string> = {
  draft: "default", sent: "blue", approved: "green", rejected: "red", expired: "orange",
};

export default function QuotationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<Quotation | null>(null);
  const [items, setItems] = useState<QuotationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [quoResp, itemsResp] = await Promise.all([
        getQuotation(Number(id)),
        getQuotationItems(Number(id)),
      ]);
      setData(quoResp.data.data as Quotation);
      setItems((itemsResp.data.data as QuotationItem[]) || []);
    } catch (e) {
      setError((e as Error).message || "加载失败");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [id]);

  const handleDelete = async () => {
    try { await deleteQuotation(Number(id)); message.success("已删除"); navigate("/sales/quotations"); }
    catch { message.error("删除失败"); }
  };

  const handleDeleteItem = async (itemId: number) => {
    try { await deleteQuotationItem(Number(id), itemId); message.success("已删除"); load(); }
    catch { message.error("删除失败"); }
  };

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!data) return <Empty description="未找到该报价单" />;

  const itemColumns = [
    { title: "产品ID", dataIndex: "product_id", width: 100 },
    { title: "数量", dataIndex: "quantity", width: 80 },
    { title: "单价", dataIndex: "unit_price", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
    { title: "金额", dataIndex: "amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
    {
      title: "操作", width: 80, render: (_: unknown, record: QuotationItem) => (
        <Popconfirm title="确定删除?" onConfirm={() => handleDeleteItem(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/quotations")}>返回列表</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/quotations/${data.id}/edit`)}>编辑</Button>
        <Popconfirm title="确定删除?" onConfirm={handleDelete}>
          <Button danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      </Space>
      <Card title={`报价单: ${data.quotation_no || "NO-" + data.id}`} style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="客户ID">{data.customer_id}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={statusColors[data.status] || "default"}>{data.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="总金额">¥{data.total_amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="有效期至">{data.valid_until || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{data.notes || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{data.created_at}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="报价项" extra={<Button icon={<PlusOutlined />} onClick={() => navigate(`/sales/quotations/${data.id}/edit`)}>管理报价项</Button>}>
        <Table rowKey="id" columns={itemColumns} dataSource={items} pagination={false} />
      </Card>
    </div>
  );
}
