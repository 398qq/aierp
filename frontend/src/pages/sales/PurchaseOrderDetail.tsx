import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, Descriptions, Table, Tag, Button, Space, message, Spin, InputNumber, Modal } from "antd";
import { ArrowLeftOutlined, EditOutlined, CheckCircleOutlined } from "@ant-design/icons";
import { getPurchaseOrder, receivePurchaseOrder } from "../../api";
import client from "../../api/client";
import type { PurchaseOrder } from "../../types";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" },
  received: { color: "green", label: "已收货" },
  cancelled: { color: "red", label: "已取消" },
};

type POItem = { id: number; product_id: number; product_name?: string; product_sku?: string; quantity: number; unit_price: number; amount: number };

export default function PurchaseOrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [po, setPo] = useState<(PurchaseOrder & { items: POItem[] }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [receiveWarehouseId, setReceiveWarehouseId] = useState(1);
  const [receiving, setReceiving] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const r = await getPurchaseOrder(Number(id));
      setPo(r.data.data as PurchaseOrder & { items: POItem[] });
    } catch { message.error("加载采购订单详情失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [id]);

  const handleReceive = async () => {
    if (!po) return;
    setReceiving(true);
    try {
      await receivePurchaseOrder(po.id, receiveWarehouseId);
      message.success(`PO ${po.order_no || `#${po.id}`} 已收货，库存已入库`);
      fetch();
    } catch { message.error("收货失败"); }
    finally { setReceiving(false); }
  };

  if (loading) return <Spin style={{ display: "block", margin: "80px auto" }} />;
  if (!po) return <div>采购订单不存在</div>;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/purchase-orders")}>返回列表</Button>
        <Space>
          {po.status === "draft" && (
            <>
              <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/purchase-orders/${po.id}/edit`)}>编辑</Button>
              <Button type="primary" icon={<CheckCircleOutlined />}
                onClick={() => Modal.confirm({
                  title: "采购收货",
                  content: (
                    <div>
                      <p>确认收货 <strong>{po.order_no || `#${po.id}`}</strong> ?</p>
                      <p>入库仓库: <InputNumber min={1} value={receiveWarehouseId} onChange={(v) => setReceiveWarehouseId(v || 1)} style={{ width: 80 }} /></p>
                    </div>
                  ),
                  onOk: handleReceive, okButtonProps: { loading: receiving }, okText: "确认收货",
                })}>收货</Button>
            </>
          )}
          <Button onClick={async () => {
            try { await client.post("/approvals/submit", { doc_type: "purchase_order", doc_id: po.id }); message.success("已提交审批"); } catch { message.error("提交审批失败"); }
          }}>提交审批</Button>
        </Space>
      </Space>

      <Card title={`采购订单 ${po.order_no || `#${po.id}`}`}>
        <Descriptions bordered size="small" column={2} style={{ marginBottom: 24 }}>
          <Descriptions.Item label="订单号">{po.order_no || "-"}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={STATUS[po.status]?.color}>{STATUS[po.status]?.label || po.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="供应商">{po.supplier_name || `#${po.supplier_id}`}</Descriptions.Item>
          <Descriptions.Item label="金额">¥{po.total_amount?.toLocaleString() ?? 0}</Descriptions.Item>
          <Descriptions.Item label="预计到货">{po.expected_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{po.created_at?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{po.notes || "-"}</Descriptions.Item>
        </Descriptions>

        <Table
          title={() => <strong>采购明细</strong>}
          rowKey="id"
          dataSource={po.items || []}
          size="small"
          pagination={false}
          columns={[
            { title: "#", width: 50, render: (_: unknown, __: unknown, i: number) => i + 1 },
            { title: "产品", dataIndex: "product_name", ellipsis: true,
              render: (v: string, r: POItem) => v || `${r.product_sku || ""} #${r.product_id}` },
            { title: "数量", dataIndex: "quantity", width: 80 },
            { title: "单价", dataIndex: "unit_price", width: 100, render: (v: number) => `¥${v?.toFixed(2) ?? "0.00"}` },
            { title: "小计", dataIndex: "amount", width: 100, render: (v: number) => `¥${v?.toFixed(2) ?? "0.00"}` },
          ]}
        />
      </Card>
    </div>
  );
}
