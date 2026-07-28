import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Alert,
  Button,
  Descriptions,
  Divider,
  Empty,
  message,
  Popconfirm,
  Space,
  Spin,
  Switch,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import type { ProColumns } from "@ant-design/pro-components";
import { ProCard, ProTable } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  DollarOutlined,
  EditOutlined,
  FileTextOutlined,
  PrinterOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import {
  getDeliveryNote,
  getPayments,
  markDeliveryNotePaid,
  updateDeliveryNote,
  getApiErrorMessage,
  convertDeliveryToInvoice,
  convertDeliveryToReturn,
} from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { DeliveryNote, PaymentRecord } from "../../types";
import { DeliveryNotePrint } from "./DeliveryNotePrint";
import {
  CustomerLink,
  ErpStatusTimeline,
  MetricBand,
  SalesModuleShell,
  SalesStatusTag,
  money,
  shortDate,
} from "./salesUi";

const STATUS_STEPS = [
  { key: "pending", label: "待发货" },
  { key: "shipped", label: "已发货" },
  { key: "delivered", label: "已签收" },
];

export default function DeliveryNoteDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [note, setNote] = useState<DeliveryNote | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeAi, setIncludeAi] = useState(true);
  const [payments, setPayments] = useState<PaymentRecord[]>([]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const noteId = Number(id);
    Promise.all([
      getDeliveryNote(noteId, includeAi),
      getPayments({ page: 1, page_size: 100, delivery_note_id: noteId }),
    ])
      .then(([noteResp, payResp]) => {
        setNote(noteResp.data.data);
        setPayments(payResp.data.data.list || []);
      })
      .catch((err) => setError(err.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id, includeAi]);

  const itemSummary = useMemo(() => {
    const items = note?.items || [];
    const quantity = items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    return { count: items.length, quantity };
  }, [note]);

  if (loading) {
    return (
      <SalesModuleShell title="发货单详情" activeKey="delivery">
        <Spin style={{ display: "block", margin: "100px auto" }} />
      </SalesModuleShell>
    );
  }

  if (error) {
    return (
      <SalesModuleShell title="发货单详情" activeKey="delivery">
        <Alert type="error" message={error} />
      </SalesModuleShell>
    );
  }

  if (!note) {
    return (
      <SalesModuleShell title="发货单详情" activeKey="delivery">
        <Empty description="发货单不存在" />
      </SalesModuleShell>
    );
  }

  return (
    <SalesModuleShell
      title={note.delivery_no || `发货单 #${note.id}`}
      subtitle="发货单客户来自关联销售订单，发货后会触发库存扣减"
      activeKey="delivery"
      extra={
        <>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/delivery-notes")}>
            返回
          </Button>
          <Button
            icon={<EditOutlined />}
            onClick={() => navigate(`/sales/delivery-notes/${note.id}/edit`)}
          >
            编辑
          </Button>
          <Button icon={<PrinterOutlined />} onClick={() => window.print()}>
            打印送货单
          </Button>
          {note.status === "pending" ? (
            <Button
              type="primary"
              onClick={async () => {
                try {
                  await updateDeliveryNote(note.id, { status: "shipped" });
                  message.success("已发货，库存已自动扣减");
                  setNote({ ...note, status: "shipped" });
                } catch (e: unknown) {
                  message.error(getApiErrorMessage(e, "操作失败"));
                }
              }}
            >
              标记发货
            </Button>
          ) : null}
          {payments.length === 0 ? (
            <Tooltip title="登记回款后回款栏将显示「已收款」">
              <Popconfirm
                title="登记为已收款？"
                description="将自动创建收款记录并标记为签收"
                okText="确认收款"
                cancelText="取消"
                onConfirm={async () => {
                  try {
                    const resp = await markDeliveryNotePaid(note.id);
                    message.success(resp.data.data.created ? "已登记回款" : "回款记录已存在");
                    const [noteResp, payResp] = await Promise.all([
                      getDeliveryNote(note.id, includeAi),
                      getPayments({ page: 1, page_size: 100, delivery_note_id: note.id }),
                    ]);
                    setNote(noteResp.data.data);
                    setPayments(payResp.data.data.list || []);
                  } catch (e: unknown) {
                    message.error(getApiErrorMessage(e, "操作失败"));
                  }
                }}
              >
                <Button icon={<DollarOutlined />} type="primary" ghost>
                  登记回款
                </Button>
              </Popconfirm>
            </Tooltip>
          ) : (
            <Button
              icon={<CheckCircleOutlined />}
              type="text"
              disabled
              style={{ color: "#52c41a" }}
            >
              已收款
            </Button>
          )}
          {["shipped", "delivered"].includes(note.status) ? (
            <Popconfirm
              title="生成发票？"
              description="将基于此发货单创建发票"
              okText="确认"
              cancelText="取消"
              onConfirm={async () => {
                try {
                  const resp = await convertDeliveryToInvoice(note.id);
                  message.success(`已生成发票 ${resp.data.data.document_no}`);
                  const noteResp = await getDeliveryNote(note.id, includeAi);
                  setNote(noteResp.data.data);
                } catch (e: unknown) {
                  message.error(getApiErrorMessage(e, "生成发票失败"));
                }
              }}
            >
              <Button icon={<FileTextOutlined />}>生成发票</Button>
            </Popconfirm>
          ) : null}
          {note.status === "delivered" ? (
            <Popconfirm
              title="申请退货？"
              description="将创建退货单，可在退货管理中查看"
              okText="确认"
              cancelText="取消"
              onConfirm={async () => {
                try {
                  const resp = await convertDeliveryToReturn(note.id);
                  message.success(`已创建退货单 ${resp.data.data.document_no}`);
                  const noteResp = await getDeliveryNote(note.id, includeAi);
                  setNote(noteResp.data.data);
                } catch (e: unknown) {
                  message.error(getApiErrorMessage(e, "创建退货失败"));
                }
              }}
            >
              <Button icon={<SwapOutlined />}>申请退货</Button>
            </Popconfirm>
          ) : null}
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </>
      }
    >
      <DeliveryNotePrint note={note} />
      <MetricBand
        items={[
          { title: "产品行数", value: itemSummary.count, suffix: "项" },
          { title: "总数量", value: itemSummary.quantity, suffix: "件" },
          { title: "状态", value: note.status },
          { title: "发货日期", value: note.delivery_date ? shortDate(note.delivery_date) : "-" },
        ]}
      />

      <div className="erp-detail-two-column">
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <ProCard title="发货信息" extra={<SalesStatusTag value={note.status} />} size="small">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="关联订单">
                <Typography.Link onClick={() => navigate(`/sales/orders/${note.sales_order_id}`)}>
                  订单 #{note.sales_order_id}
                </Typography.Link>
              </Descriptions.Item>
              <Descriptions.Item label="客户">
                <CustomerLink id={note.customer_id} />
              </Descriptions.Item>
              <Descriptions.Item label="发货日期">
                {shortDate(note.delivery_date)}
              </Descriptions.Item>
              <Descriptions.Item label="签收日期">
                {shortDate(note.received_date)}
              </Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>
                {note.notes || "-"}
              </Descriptions.Item>
            </Descriptions>
          </ProCard>

          {note.items.length > 0 && (
            <ProCard title="发货明细" size="small">
              <ProTable
                rowKey="id"
                dataSource={note.items}
                size="small"
                pagination={false}
                columns={
                  [
                    {
                      title: "客户料号",
                      dataIndex: "customer_part_no",
                      width: 170,
                      render: (value: string | null) => value || "-",
                    },
                    {
                      title: "产品",
                      ellipsis: true,
                      render: (_: unknown, row) =>
                        row.customer_product_name || row.product_name || "-",
                    },
                    { title: "数量", dataIndex: "quantity", width: 90 },
                    { title: "备注", dataIndex: "notes", ellipsis: true },
                  ] as ProColumns<DeliveryNote["items"][number]>[]
                }
              />
            </ProCard>
          )}

          <ProCard title="回款信息" size="small">
            {payments.length === 0 ? (
              <Typography.Text type="secondary">暂无回款记录</Typography.Text>
            ) : (
              <ProTable
                rowKey="id"
                dataSource={payments}
                size="small"
                pagination={false}
                columns={
                  [
                    {
                      title: "金额",
                      dataIndex: "amount",
                      width: 120,
                      render: (v: number) => money(v),
                    },
                    { title: "方式", dataIndex: "payment_method", width: 80 },
                    {
                      title: "日期",
                      dataIndex: "payment_date",
                      width: 110,
                      render: (v: string) => v?.slice(0, 10) || "-",
                    },
                    {
                      title: "状态",
                      dataIndex: "status",
                      width: 80,
                      render: (v: string) => {
                        const m: Record<string, { color: string; label: string }> = {
                          pending: { color: "orange", label: "待收款" },
                          completed: { color: "green", label: "已收款" },
                          overdue: { color: "red", label: "逾期" },
                        };
                        return <StatusTag tone={m[v]?.color}>{m[v]?.label || v}</StatusTag>;
                      },
                    },
                  ] as ProColumns<PaymentRecord>[]
                }
              />
            )}
          </ProCard>

          {includeAi && <SalesAIInsight aiData={note.ai} />}
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
          <ProCard
            size="small"
            title={
              <>
                <DollarOutlined /> 发货摘要
              </>
            }
          >
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">关联订单</Typography.Text>
                <Typography.Link onClick={() => navigate(`/sales/orders/${note.sales_order_id}`)}>
                  订单 #{note.sales_order_id}
                </Typography.Link>
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
                <SalesStatusTag value={note.status} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">发货日期</Typography.Text>
                <Typography.Text>{shortDate(note.delivery_date)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">签收日期</Typography.Text>
                <Typography.Text>{shortDate(note.received_date)}</Typography.Text>
              </div>
            </Space>
          </ProCard>

          <ProCard size="small" title="状态流转">
            <ErpStatusTimeline
              currentStatus={note.status}
              steps={STATUS_STEPS}
              createdAt={note.created_at}
              lostStatus="returned"
            />
          </ProCard>

          <ProCard size="small" title="下一步动作">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              {note.status === "pending" ? (
                <Alert showIcon type="info" message="发货单待发货，确认产品明细后执行发货。" />
              ) : note.status === "shipped" ? (
                <Alert showIcon type="success" message="已发货，需跟进客户签收确认。" />
              ) : note.status === "delivered" ? (
                <Alert showIcon type="success" message="已签收，发货流程完成。" />
              ) : null}
              {note.sales_order_id ? (
                <Button block onClick={() => navigate(`/sales/orders/${note.sales_order_id}`)}>
                  查看关联订单
                </Button>
              ) : null}
              {note.customer_id ? (
                <Button block onClick={() => navigate(`/customers/${note.customer_id}`)}>
                  查看客户
                </Button>
              ) : null}
            </Space>
          </ProCard>
        </Space>
      </div>
    </SalesModuleShell>
  );
}
