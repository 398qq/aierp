/**
 * Batch Traceability — Stage 18 / Production Batch Management
 *
 * Bidirectional traceability for a single inventory batch.
 *   - Upstream: supplier + stock-in receipts
 *   - Downstream: deliveries → sales orders → customers
 *
 * Route: /inventory/batches/:id/traceability
 * API:   GET /api/v1/inventory/batches/{id}/traceability
 */

import { useEffect, useState } from "react";
import { useParams, Link } from "@/router";
import {
  Card,
  Descriptions,
  Empty,
  Spin,
  Table,
  Tag,
  Typography,
  Alert,
  Space,
  Statistic,
  Row,
  Col,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  message as antMessage,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import client from "../../api/client";

const { Title, Text } = Typography;

interface BatchInfo {
  id: number;
  batch_no: string;
  product_id: number;
  product_name: string | null;
  product_sku: string | null;
  warehouse_id: number;
  warehouse_name: string | null;
  supplier_id: number | null;
  supplier_name: string | null;
  quantity: number;
  locked_quantity: number;
  unit_cost: number;
  received_date: string | null;
  manufacture_date: string | null;
  expiry_date: string | null;
  status: string;
  rohs_compliant: boolean;
  msl_level: string | null;
  certificate_url: string | null;
  notes: string | null;
}

interface StockInRecord {
  id: number;
  reference_type: string | null;
  reference_id: number | null;
  quantity: number;
  before_qty: number | null;
  after_qty: number | null;
  created_at: string | null;
  notes: string | null;
}

interface PurchaseOrderRef {
  id: number;
  po_no: string | null;
  supplier_id: number | null;
  status: string | null;
  order_date: string | null;
  expected_date: string | null;
  total_amount: number;
}

interface DeliveryConsumption {
  transaction_id: number;
  transaction_at: string | null;
  quantity: number;
  delivery_note_id: number | null;
  delivery_no: string | null;
  sales_order_id: number | null;
  sales_order_no: string | null;
  customer_id: number | null;
  customer_name: string | null;
}

interface UpstreamInfo {
  supplier: { id: number; name: string | null } | null;
  purchase_orders: PurchaseOrderRef[];
  stock_in_records: StockInRecord[];
}

interface DownstreamInfo {
  deliveries: DeliveryConsumption[];
  customers: { id: number; name: string; short_name: string | null }[];
  total_consumed: number;
  remaining_qty: number;
  delivery_count: number;
  customer_count: number;
}

interface TraceabilityResponse {
  batch: BatchInfo;
  upstream: UpstreamInfo;
  downstream: DownstreamInfo;
}

interface ApiEnvelope<T> {
  code: number;
  data: T;
  msg?: string;
}

const STATUS_COLOR: Record<string, string> = {
  available: "green",
  locked: "orange",
  consumed: "default",
  expired: "red",
  recalled: "red",
  quarantined: "volcano",
};

export default function BatchTraceability() {
  const { id } = useParams<{ id: string }>();
  const batchId = Number(id);
  const [data, setData] = useState<TraceabilityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!batchId || Number.isNaN(batchId)) {
      setError("无效的批次 ID");
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const resp = await client.get<ApiEnvelope<TraceabilityResponse>>(
          `/inventory/batches/${batchId}/traceability`,
        );
        if (!cancelled) setData(resp.data.data);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "加载失败";
        if (!cancelled) setError(msg);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [batchId]);

  // ── Action state (Transfer / Split / Merge) ───────────────────────
  const [actionModal, setActionModal] = useState<"transfer" | "split" | "merge" | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [transferForm] = Form.useForm();
  const [splitForm] = Form.useForm();
  const [mergeForm] = Form.useForm();

  const reload = async () => {
    try {
      const resp = await client.get<{ data: TraceabilityResponse }>(
        `/inventory/batches/${batchId}/traceability`,
      );
      setData(resp.data.data);
    } catch {
      // ignore — keep prior data
    }
  };

  const handleAction = async (
    kind: "transfer" | "split" | "merge",
    payload: Record<string, unknown>,
  ) => {
    setActionLoading(true);
    try {
      const url =
        kind === "transfer"
          ? `/inventory/batches/${batchId}/transfer`
          : kind === "split"
          ? `/inventory/batches/${batchId}/split`
          : `/inventory/batches/merge`;
      const resp = await client.post<{ code: number; data: unknown; msg?: string }>(
        url,
        payload,
      );
      if (resp.data.code === 200) {
        antMessage.success(
          kind === "transfer"
            ? "调拨成功"
            : kind === "split"
            ? "拆分成功"
            : "合并成功",
        );
        setActionModal(null);
        transferForm.resetFields();
        splitForm.resetFields();
        mergeForm.resetFields();
        await reload();
      } else {
        antMessage.error(resp.data.msg || "操作失败");
      }
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { msg?: string } } }).response?.data?.msg
          : undefined;
      antMessage.error(msg || "请求失败");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: "center" }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: 24 }}>
        <Alert type="error" message="无法加载批次追溯" description={error ?? "数据为空"} />
      </div>
    );
  }

  const b = data.batch;
  const upstream = data.upstream;
  const downstream = data.downstream;

  const stockInColumns: ColumnsType<StockInRecord> = [
    {
      title: "入库时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 160,
      render: (v: string | null) => (v ? formatDateTime(v) : "-"),
    },
    {
      title: "关联单据",
      key: "ref",
      render: (_, r) =>
        r.reference_type ? `${r.reference_type} #${r.reference_id ?? "?"}` : "-",
    },
    { title: "数量", dataIndex: "quantity", key: "quantity", width: 80 },
    { title: "入库前/后", key: "before_after", width: 120, render: (_, r) => `${r.before_qty ?? "-"} / ${r.after_qty ?? "-"}` },
    { title: "备注", dataIndex: "notes", key: "notes" },
  ];

  const poColumns: ColumnsType<PurchaseOrderRef> = [
    {
      title: "PO 单号",
      dataIndex: "po_no",
      key: "po_no",
      render: (v: string | null, r) =>
        v ? <Link to={`/sales/purchase-orders/${r.id}`}>{v}</Link> : `#${r.id}`,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (v: string | null) => (v ? <Tag>{v}</Tag> : "-"),
    },
    {
      title: "订单日期",
      dataIndex: "order_date",
      key: "order_date",
      width: 120,
      render: (v: string | null) => (v ? formatDateTime(v) : "-"),
    },
    {
      title: "预计到货",
      dataIndex: "expected_date",
      key: "expected_date",
      width: 120,
      render: (v: string | null) => (v ? formatDateTime(v) : "-"),
    },
    {
      title: "金额",
      dataIndex: "total_amount",
      key: "total_amount",
      width: 120,
      render: (v: number) => v.toFixed(2),
    },
  ];

  const deliveryColumns: ColumnsType<DeliveryConsumption> = [
    {
      title: "出库时间",
      dataIndex: "transaction_at",
      key: "transaction_at",
      width: 160,
      render: (v: string | null) => (v ? formatDateTime(v) : "-"),
    },
    {
      title: "发货单",
      key: "delivery",
      render: (_, r) =>
        r.delivery_no ? (
          <Link to={`/sales/delivery-notes/${r.delivery_note_id}`}>{r.delivery_no}</Link>
        ) : (
          "-"
        ),
    },
    {
      title: "销售单",
      key: "so",
      render: (_, r) =>
        r.sales_order_no ? (
          <Link to={`/sales/orders/${r.sales_order_id}`}>{r.sales_order_no}</Link>
        ) : (
          "-"
        ),
    },
    {
      title: "客户",
      key: "customer",
      render: (_, r) =>
        r.customer_id ? (
          <Link to={`/customers/${r.customer_id}`}>{r.customer_name}</Link>
        ) : (
          "-"
        ),
    },
    { title: "数量", dataIndex: "quantity", key: "quantity", width: 80 },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Link to="/warehouse/inventory-batches">← 返回批次列表</Link>
        <span style={{ flex: 1 }} />
        <Button onClick={() => setActionModal("transfer")}>调拨</Button>
        <Button onClick={() => setActionModal("split")}>拆分</Button>
        <Button onClick={() => setActionModal("merge")}>合并</Button>
        <Link to={`/inventory/batches/${batchId}/recall`}>
          <Button danger>召回</Button>
        </Link>
      </Space>

      {/* Batch header */}
      <Card style={{ marginBottom: 16 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={3} style={{ margin: 0 }}>
              批次 {b.batch_no}
            </Title>
            <Space style={{ marginTop: 8 }}>
              <Tag color={STATUS_COLOR[b.status] ?? "default"}>{b.status}</Tag>
              {b.rohs_compliant ? <Tag color="green">RoHS</Tag> : <Tag color="red">非 RoHS</Tag>}
              {b.msl_level && <Tag>MSL {b.msl_level}</Tag>}
            </Space>
          </Col>
          <Col>
            <Statistic title="剩余数量" value={b.quantity} suffix={b.product_name ?? ""} />
          </Col>
        </Row>
      </Card>

      {/* Batch detail */}
      <Card title="批次详情" style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small" bordered>
          <Descriptions.Item label="批次号">{b.batch_no}</Descriptions.Item>
          <Descriptions.Item label="产品">
            {b.product_name ? <Link to={`/products/${b.product_id}`}>{b.product_name}</Link> : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="SKU">{b.product_sku ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="仓库">{b.warehouse_name ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="供应商">{b.supplier_name ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="单位成本">¥ {b.unit_cost.toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="生产日期">{b.manufacture_date ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="入库日期">{b.received_date ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="有效期">
            {b.expiry_date ? (
              <Text type={isExpired(b.expiry_date) ? "danger" : undefined}>
                {b.expiry_date} {isExpired(b.expiry_date) && "(已过期)"}
              </Text>
            ) : (
              "-"
            )}
          </Descriptions.Item>
          <Descriptions.Item label="锁定数量">{b.locked_quantity}</Descriptions.Item>
          <Descriptions.Item label="证书" span={2}>
            {b.certificate_url ? (
              <a href={b.certificate_url} target="_blank" rel="noreferrer">
                {b.certificate_url}
              </a>
            ) : (
              "-"
            )}
          </Descriptions.Item>
          {b.notes && <Descriptions.Item label="备注" span={3}>{b.notes}</Descriptions.Item>}
        </Descriptions>
      </Card>

      {/* Upstream */}
      <Card title="上游追溯（来源）" style={{ marginBottom: 16 }}>
        <Descriptions column={2} size="small" style={{ marginBottom: 12 }}>
          <Descriptions.Item label="供应商">
            {upstream.supplier ? (
              upstream.supplier.name ? (
                upstream.supplier.name
              ) : (
                `#${upstream.supplier.id}`
              )
            ) : (
              <Text type="secondary">未指定</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="关联采购单">
            {upstream.purchase_orders.length}
          </Descriptions.Item>
        </Descriptions>

        <Title level={5} style={{ marginTop: 0 }}>
          入库记录 ({upstream.stock_in_records.length})
        </Title>
        <Table<StockInRecord>
          rowKey="id"
          columns={stockInColumns}
          dataSource={upstream.stock_in_records}
          size="small"
          pagination={false}
          locale={{ emptyText: <Empty description="尚无入库记录" /> }}
        />

        {upstream.purchase_orders.length > 0 && (
          <>
            <Title level={5} style={{ marginTop: 16 }}>
              相关采购单
            </Title>
            <Table<PurchaseOrderRef>
              rowKey="id"
              columns={poColumns}
              dataSource={upstream.purchase_orders}
              size="small"
              pagination={false}
            />
          </>
        )}
      </Card>

      {/* Downstream */}
      <Card title="下游追溯（去向）" style={{ marginBottom: 16 }}>
        <Row gutter={16} style={{ marginBottom: 12 }}>
          <Col span={6}>
            <Statistic title="已消耗数量" value={downstream.total_consumed} />
          </Col>
          <Col span={6}>
            <Statistic title="剩余数量" value={downstream.remaining_qty} />
          </Col>
          <Col span={6}>
            <Statistic title="发货次数" value={downstream.delivery_count} />
          </Col>
          <Col span={6}>
            <Statistic title="涉及客户" value={downstream.customer_count} />
          </Col>
        </Row>

        <Title level={5} style={{ marginTop: 0 }}>
          发货记录 ({downstream.deliveries.length})
        </Title>
        <Table<DeliveryConsumption>
          rowKey="transaction_id"
          columns={deliveryColumns}
          dataSource={downstream.deliveries}
          size="small"
          pagination={false}
          locale={{ emptyText: <Empty description="此批次尚未出库" /> }}
        />

        {downstream.customers.length > 0 && (
          <>
            <Title level={5} style={{ marginTop: 16 }}>
              涉及客户 ({downstream.customers.length})
            </Title>
            <Space wrap>
              {downstream.customers.map((c) => (
                <Link key={c.id} to={`/customers/${c.id}`}>
                  <Tag color="blue">{c.name}</Tag>
                </Link>
              ))}
            </Space>
          </>
        )}
      </Card>
        {/* Action modals: Transfer / Split / Merge */}
        <Modal
          title="调拨批次"
          open={actionModal === "transfer"}
          onCancel={() => { setActionModal(null); transferForm.resetFields(); }}
          confirmLoading={actionLoading}
          onOk={() => transferForm.submit()}
          okText="确认调拨"
        >
          <Form
            form={transferForm}
            layout="vertical"
            onFinish={(v: { dst_warehouse_id: number; quantity: number; reason: string }) =>
              handleAction("transfer", { dst_warehouse_id: v.dst_warehouse_id, quantity: v.quantity, reason: v.reason })
            }
          >
            <Form.Item name="dst_warehouse_id" label="目标仓库 ID" rules={[{ required: true, message: "必填" }]}>
              <InputNumber min={1} style={{ width: "100%" }} placeholder="如 2" />
            </Form.Item>
            <Form.Item name="quantity" label="数量" rules={[{ required: true, message: "必填" }]}>
              <InputNumber min={1} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="reason" label="原因" rules={[{ required: true, min: 1, message: "必填" }]}>
              <Input.TextArea rows={2} placeholder="如 调拨到上海仓" />
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="拆分批次"
          open={actionModal === "split"}
          onCancel={() => { setActionModal(null); splitForm.resetFields(); }}
          confirmLoading={actionLoading}
          onOk={() => splitForm.submit()}
          okText="确认拆分"
        >
          <Form
            form={splitForm}
            layout="vertical"
            onFinish={(v: { quantity: number; new_batch_no?: string; reason: string }) =>
              handleAction("split", { quantity: v.quantity, new_batch_no: v.new_batch_no || undefined, reason: v.reason })
            }
          >
            <Form.Item name="quantity" label="拆分数量" rules={[{ required: true, message: "必填" }]}>
              <InputNumber min={1} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="new_batch_no" label="新批次号（可选）">
              <Input placeholder="省略时自动 -S1, -S2..." />
            </Form.Item>
            <Form.Item name="reason" label="原因" rules={[{ required: true, min: 1, message: "必填" }]}>
              <Input.TextArea rows={2} placeholder="如 拆分给 VIP 客户" />
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="合并批次"
          open={actionModal === "merge"}
          onCancel={() => { setActionModal(null); mergeForm.resetFields(); }}
          confirmLoading={actionLoading}
          onOk={() => mergeForm.submit()}
          okText="确认合并"
        >
          <Form
            form={mergeForm}
            layout="vertical"
            onFinish={(v: { batch_ids: string; reason: string }) =>
              handleAction("merge", {
                batch_ids: v.batch_ids.split(",").map((s: string) => parseInt(s.trim(), 10)).filter((n: number) => !Number.isNaN(n)),
                reason: v.reason,
              })
            }
          >
            <Form.Item name="batch_ids" label="要合并的批次 ID（逗号分隔，含本批次 ≥2 个）" rules={[{ required: true, message: "必填" }]}>
              <Input placeholder={`如 ${batchId},456,789`} />
            </Form.Item>
            <Form.Item name="reason" label="原因" rules={[{ required: true, min: 1, message: "必填" }]}>
              <Input.TextArea rows={2} placeholder="如 清理重复批次" />
            </Form.Item>
          </Form>
        </Modal>

    </div>
          );
}

function isExpired(expiryDate: string): boolean {
  return new Date(expiryDate) < new Date();
}



function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}