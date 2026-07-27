/**
 * Batch Recall — Stage 18 / Production Batch Management
 *
 * Two-step recall workflow:
 *   1. Preview: GET /inventory/batches/{id}/recall-impact shows affected customers
 *      + deliveries before committing.
 *   2. Execute: POST /inventory/batches/{id}/recall with reason marks the batch
 *      as recalled, freezes remaining inventory, and returns the impact payload.
 *
 * Route: /inventory/batches/:id/recall
 * APIs:   GET  /api/v1/inventory/batches/{id}/recall-impact
 *        POST /api/v1/inventory/batches/{id}/recall
 */

import { useEffect, useState } from "react";
import { useParams, Link } from "react-router";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  Row,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import client from "../../api/client";

const { Title, Text } = Typography;
const { TextArea } = Input;

interface BatchInfo {
  id: number;
  batch_no: string;
  product_id: number;
  product_name: string | null;
  quantity: number;
  status: string;
}

interface ImpactCustomer {
  id: number;
  name: string;
  short_name: string | null;
}

interface ImpactDelivery {
  transaction_id: number;
  transaction_at: string | null;
  quantity: number;
  delivery_no: string | null;
  sales_order_no: string | null;
  customer_name: string | null;
}

interface ImpactPayload {
  batch: BatchInfo;
  affected_customers: ImpactCustomer[];
  deliveries: ImpactDelivery[];
  customer_count: number;
  delivery_count: number;
  total_quantity_consumed: number;
  frozen_remaining: number;
  recall?: {
    previous_status: string;
    reason: string;
    actor: string;
  };
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

export default function BatchRecall() {
  const { id } = useParams<{ id: string }>();
  const batchId = Number(id);
  const [impact, setImpact] = useState<ImpactPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [recalled, setRecalled] = useState(false);

  useEffect(() => {
    if (!batchId || Number.isNaN(batchId)) {
      setError("无效的批次 ID");
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const resp = await client.get<ApiEnvelope<ImpactPayload>>(
          `/inventory/batches/${batchId}/recall-impact`,
        );
        if (!cancelled) setImpact(resp.data.data);
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

  const handleSubmit = async (values: { reason: string }) => {
    setSubmitting(true);
    try {
      const resp = await client.post<ApiEnvelope<ImpactPayload>>(
        `/inventory/batches/${batchId}/recall`,
        { reason: values.reason },
      );
      setImpact(resp.data.data);
      setRecalled(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "召回失败";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: "center" }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (error || !impact) {
    return (
      <div style={{ padding: 24 }}>
        <Alert type="error" message="无法加载召回影响" description={error ?? "数据为空"} />
        <div style={{ marginTop: 16 }}>
          <Link to="/warehouse/inventory-batches">← 返回批次列表</Link>
        </div>
      </div>
    );
  }

  const batch = impact.batch;
  const alreadyRecalled = batch.status === "recalled" || recalled;

  const deliveryColumns: ColumnsType<ImpactDelivery> = [
    {
      title: "时间",
      dataIndex: "transaction_at",
      key: "transaction_at",
      width: 160,
      render: (v: string | null) => (v ? v.slice(0, 16).replace("T", " ") : "-"),
    },
    {
      title: "发货单",
      dataIndex: "delivery_no",
      key: "delivery_no",
      render: (v: string | null) => v || "-",
    },
    {
      title: "销售单",
      dataIndex: "sales_order_no",
      key: "sales_order_no",
      render: (v: string | null) => v || "-",
    },
    {
      title: "客户",
      dataIndex: "customer_name",
      key: "customer_name",
      render: (v: string | null) => v || "-",
    },
    { title: "数量", dataIndex: "quantity", key: "quantity", width: 80 },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Link to="/warehouse/inventory-batches">← 返回批次列表</Link>
        <Link to={`/inventory/batches/${batchId}/traceability`}>查看追溯</Link>
      </Space>

      <Title level={3}>批次召回</Title>

      {/* Batch header */}
      <Card style={{ marginBottom: 16 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              {batch.batch_no}
            </Title>
            <Space style={{ marginTop: 8 }}>
              <Tag color={STATUS_COLOR[batch.status] ?? "default"}>
                {batch.status}
              </Tag>
              {batch.product_name && <Text type="secondary">{batch.product_name}</Text>}
            </Space>
          </Col>
          <Col>
            <Statistic title="剩余数量（将被冻结）" value={batch.quantity} />
          </Col>
        </Row>
      </Card>

      {/* Impact preview */}
      <Card title="召回影响预览" style={{ marginBottom: 16 }}>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic title="受影响客户" value={impact.customer_count} suffix="个" />
          </Col>
          <Col span={6}>
            <Statistic title="发货次数" value={impact.delivery_count} suffix="次" />
          </Col>
          <Col span={6}>
            <Statistic title="已消耗数量" value={impact.total_quantity_consumed} />
          </Col>
          <Col span={6}>
            <Statistic title="剩余冻结数量" value={impact.frozen_remaining} />
          </Col>
        </Row>

        {impact.affected_customers.length > 0 && (
          <>
            <Title level={5} style={{ marginTop: 0 }}>
              涉及客户
            </Title>
            <Space wrap style={{ marginBottom: 16 }}>
              {impact.affected_customers.map((c) => (
                <Link key={c.id} to={`/customers/${c.id}`}>
                  <Tag color="blue">{c.name}</Tag>
                </Link>
              ))}
            </Space>
          </>
        )}

        <Title level={5}>发货记录</Title>
        <Table<ImpactDelivery>
          rowKey="transaction_id"
          columns={deliveryColumns}
          dataSource={impact.deliveries}
          size="small"
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: <Empty description="此批次尚未出库" /> }}
        />
      </Card>

      {/* Execute recall */}
      {alreadyRecalled ? (
        <Card>
          <Alert
            type="success"
            message="批次已召回"
            description={
              impact.recall
                ? `操作人: ${impact.recall.actor} · 原因: ${impact.recall.reason} · 之前状态: ${impact.recall.previous_status}`
                : "该批次已被标记为 recalled。"
            }
            showIcon
          />
        </Card>
      ) : (
        <Card title="执行召回">
          <Alert
            type="warning"
            message="召回操作不可撤销"
            description="提交后将立即标记 status=recalled 并冻结剩余库存。建议先通过 notification 服务通知受影响客户。"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Form layout="vertical" onFinish={handleSubmit}>
            <Form.Item
              label="召回原因"
              name="reason"
              rules={[
                { required: true, message: "请填写召回原因" },
                { min: 4, message: "至少 4 个字符" },
              ]}
            >
              <TextArea
                rows={3}
                placeholder="例：供应商批次检测不达标，需召回所有已发货客户"
              />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button
                  type="primary"
                  danger
                  htmlType="submit"
                  loading={submitting}
                >
                  确认召回
                </Button>
                <Link to={`/inventory/batches/${batchId}/traceability`}>
                  <Button>先看追溯</Button>
                </Link>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      )}
    </div>
  );
}