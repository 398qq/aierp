import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Alert, Button, Card, Descriptions, Divider, Modal, Space, Spin, Table, Tag, Typography, InputNumber, message } from "antd";
import { ArrowLeftOutlined, DollarOutlined, EditOutlined, CheckCircleOutlined } from "@ant-design/icons";
import { getPurchaseOrder, receivePurchaseOrder } from "../../api";
import client from "../../api/client";
import type { PurchaseOrder } from "../../types";
import { ErpStatusTimeline, MetricBand, SalesModuleShell, shortDate, money } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" },
  received: { color: "green", label: "已收货" },
  cancelled: { color: "red", label: "已取消" },
};

const STATUS_STEPS = [
  { key: "draft", label: "草稿" },
  { key: "received", label: "已收货" },
];

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

  const itemSummary = useMemo(() => {
    const items = po?.items || [];
    const quantity = items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    const amount = items.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    return { count: items.length, quantity, amount };
  }, [po]);

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

  if (loading) {
    return (
      <SalesModuleShell title="采购订单详情" activeKey="procurement">
        <Spin style={{ display: "block", margin: "80px auto" }} />
      </SalesModuleShell>
    );
  }

  if (!po) {
    return (
      <SalesModuleShell title="采购订单详情" activeKey="procurement">
        <div>采购订单不存在</div>
      </SalesModuleShell>
    );
  }

  return (
    <SalesModuleShell
      title={po.order_no || `采购订单 #${po.id}`}
      subtitle={po.notes ? `备注: ${po.notes}` : "采购订单详情，含采购明细和供应商信息"}
      activeKey="procurement"
      extra={(
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/purchase-orders")}>返回列表</Button>
      )}
    >
      <MetricBand
        items={[
          { title: "采购金额", value: po.total_amount || 0, prefix: "¥", precision: 0 },
          { title: "产品行数", value: itemSummary.count, suffix: "项" },
          { title: "总数量", value: itemSummary.quantity, suffix: "件" },
          { title: "状态", value: STATUS[po.status]?.label || po.status },
          { title: "预计到货", value: po.expected_date ? shortDate(po.expected_date) : "-" },
        ]}
      />

      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
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
                  onOk: handleReceive,
                  okButtonProps: { loading: receiving },
                  okText: "确认收货",
                })}>收货</Button>
            </>
          )}
          <Button onClick={async () => {
            try { await client.post("/approvals/submit", { doc_type: "purchase_order", doc_id: po.id }); message.success("已提交审批"); } catch { message.error("提交审批失败"); }
          }}>提交审批</Button>
        </Space>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 320px", gap: 12, alignItems: "start" }}>
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Card
            size="small"
            title="采购订单信息"
            extra={<Tag color={STATUS[po.status]?.color}>{STATUS[po.status]?.label || po.status}</Tag>}
          >
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="订单号">{po.order_no || "-"}</Descriptions.Item>
              <Descriptions.Item label="供应商">{po.supplier_name || `#${po.supplier_id}`}</Descriptions.Item>
              <Descriptions.Item label="总金额">¥{po.total_amount?.toLocaleString() ?? 0}</Descriptions.Item>
              <Descriptions.Item label="预计到货">{shortDate(po.expected_date)}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{shortDate(po.created_at)}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{po.notes || "-"}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card
            size="small"
            title="采购明细"
          >
            <Table
              rowKey="id"
              dataSource={po.items || []}
              size="small"
              pagination={false}
              bordered
              columns={[
                { title: "#", width: 50, render: (_: unknown, __: unknown, i: number) => i + 1 },
                { title: "产品", dataIndex: "product_name", ellipsis: true,
                  render: (v: string | undefined, r: POItem) => v || `${r.product_sku || ""} #${r.product_id}` },
                { title: "数量", dataIndex: "quantity", width: 80, align: "right" as const },
                { title: "单价", dataIndex: "unit_price", width: 110, align: "right" as const, render: (v: number) => `¥${v?.toFixed(2) ?? "0.00"}` },
                { title: "小计", dataIndex: "amount", width: 120, align: "right" as const, render: (v: number) => <Typography.Text strong>{`¥${v?.toFixed(2) ?? "0.00"}`}</Typography.Text> },
              ]}
              summary={() => (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0}><Typography.Text strong>合计</Typography.Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={1} />
                  <Table.Summary.Cell index={2}><Typography.Text strong>{itemSummary.quantity}</Typography.Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={3}>-</Table.Summary.Cell>
                  <Table.Summary.Cell index={4}><Typography.Text strong>{money(itemSummary.amount)}</Typography.Text></Table.Summary.Cell>
                </Table.Summary.Row>
              )}
              scroll={{ x: "max-content" }}
            />
          </Card>
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
          <Card size="small" title={<><DollarOutlined /> 采购摘要</>}>
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">采购金额</Typography.Text>
                <Typography.Text strong>{money(po.total_amount)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">产品行数</Typography.Text>
                <Typography.Text>{itemSummary.count} 项</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">总数量</Typography.Text>
                <Typography.Text>{itemSummary.quantity} 件</Typography.Text>
              </div>
              <Divider style={{ margin: "6px 0" }} />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">状态</Typography.Text>
                <Tag color={STATUS[po.status]?.color}>{STATUS[po.status]?.label || po.status}</Tag>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">供应商</Typography.Text>
                <Typography.Text>{po.supplier_name || `#${po.supplier_id}`}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">预计到货</Typography.Text>
                <Typography.Text>{shortDate(po.expected_date)}</Typography.Text>
              </div>
            </Space>
          </Card>

          <Card size="small" title="状态流转">
            <ErpStatusTimeline
              currentStatus={po.status}
              steps={STATUS_STEPS}
              createdAt={po.created_at}
              lostStatus="cancelled"
            />
          </Card>

          <Card size="small" title="下一步动作">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              {po.status === "draft" ? (
                <Alert showIcon type="info" message="采购单待处理，可编辑修改或执行收货。" />
              ) : po.status === "received" ? (
                <Alert showIcon type="success" message="采购单已收货，库存已自动更新。" />
              ) : null}
              <Button block icon={<EditOutlined />} onClick={() => navigate(`/sales/purchase-orders/${po.id}/edit`)}>编辑采购单</Button>
            </Space>
          </Card>
        </Space>
      </div>
    </SalesModuleShell>
  );
}
