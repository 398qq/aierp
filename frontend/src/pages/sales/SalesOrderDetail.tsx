import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Button, Space, Tag, Spin, Alert, Empty, Table, Switch, message } from "antd";
import { ArrowLeftOutlined, EditOutlined } from "@ant-design/icons";
import { getSalesOrder, convertSalesOrderToDelivery, updateSalesOrder } from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { SalesOrder } from "../../types";
import { CustomerLink } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  pending: { color: "default", label: "待处理" }, confirmed: { color: "blue", label: "已确认" },
  shipped: { color: "orange", label: "已发货" }, delivered: { color: "green", label: "已签收" }, cancelled: { color: "red", label: "已取消" },
};

export default function SalesOrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<SalesOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeAi, setIncludeAi] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getSalesOrder(Number(id), includeAi)
      .then((r) => setOrder(r.data.data))
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id, includeAi]);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!order) return <Empty description="订单不存在" />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/orders")}>返回</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/orders/${order.id}/edit`)}>编辑</Button>
        <Button type="primary" onClick={async () => {
          try { await convertSalesOrderToDelivery(order.id); message.success("已转为发货单"); navigate("/sales/delivery-notes"); } catch { message.error("转换失败"); }
        }}>转为发货单</Button>
        {order.status === "pending" && (
          <Button type="primary" style={{ background: "#52c41a", borderColor: "#52c41a" }} onClick={async () => {
            try { await updateSalesOrder(order.id, { status: "confirmed" }); message.success("订单已确认，库存已锁定"); setOrder({ ...order, status: "confirmed" }); } catch { message.error("确认失败"); }
          }}>确认订单 (锁定库存)</Button>
        )}
        <Space>
          <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
          <span style={{ fontSize: 13 }}>AI</span>
        </Space>
      </Space>

      <Card title={order.order_no || `订单 #${order.id}`} extra={<Tag color={STATUS[order.status]?.color}>{STATUS[order.status]?.label || order.status}</Tag>}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="客户"><CustomerLink id={order.customer_id} /></Descriptions.Item>
          <Descriptions.Item label="总金额">¥{order.total_amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="下单日期">{order.order_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="预计交货">{order.delivery_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{order.notes || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>

      {order.items.length > 0 && (
        <Card title="订单明细" size="small" style={{ marginTop: 16 }}>
          <Table
            rowKey="id"
            dataSource={order.items}
            size="small"
            pagination={false}
            columns={[
              { title: "产品", dataIndex: "product_name", ellipsis: true },
              { title: "数量", dataIndex: "quantity", width: 80 },
              { title: "单价", dataIndex: "unit_price", width: 100, render: (v: number | null) => v ? `¥${v}` : "-" },
              { title: "小计", dataIndex: "total_price", width: 120, render: (v: number | null) => v ? `¥${v.toLocaleString()}` : "-" },
            ]}
          />
        </Card>
      )}

      {includeAi && <SalesAIInsight aiData={order.ai} />}
    </div>
  );
}
