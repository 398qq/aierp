import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Alert, Button, Card, Checkbox, Descriptions, Divider, Empty, Form, Input, Modal, Progress, Select, Space, Spin, Switch, Table, Tooltip, Typography, message } from "antd";
import {
  ArrowLeftOutlined,
  CarOutlined,
  DollarOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  PrinterOutlined,
} from "@ant-design/icons";
import { getPayments, getSalesOrder, getSalesOrderBusinessChain, convertSalesOrderToDelivery, updateSalesOrder, downloadSalesOrderPDF, getApiErrorMessage } from "../../api";
import type { SalesOrderPDFOptions } from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { SalesOrder, SalesOrderBusinessChain, SalesOrderItem } from "../../types";
import { CustomerLink, ErpExportButton, ErpStatusTimeline, MetricBand, SalesModuleShell, SalesStatusTag, money, shortDate } from "./salesUi";
import { SalesOrderPrint } from "./SalesOrderPrint";

const STATUS_STEPS = [
  { key: "pending", label: "待确认" },
  { key: "confirmed", label: "已确认" },
  { key: "shipped", label: "已发货" },
  { key: "delivered", label: "已签收" },
];

export default function SalesOrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<SalesOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeAi, setIncludeAi] = useState(true);
  const [showExtraColumns, setShowExtraColumns] = useState(false);
  const [payments, setPayments] = useState<{ amount: number; status: string }[]>([]);
  const [businessChain, setBusinessChain] = useState<SalesOrderBusinessChain | null>(null);
  const [pdfOpen, setPdfOpen] = useState(false);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [pdfForm] = Form.useForm<SalesOrderPDFOptions>();

  const loadPayments = async (orderId: number) => {
    try {
      const resp = await getPayments({ sales_order_id: orderId, page_size: 50 });
      setPayments(resp.data.data.list || []);
    } catch {
      setPayments([]);
    }
  };

  useEffect(() => {
    setLoading(true);
    setError(null);
    const oid = Number(id);
    getSalesOrder(oid, includeAi)
      .then((r) => {
        setOrder(r.data.data);
        loadPayments(oid);
        getSalesOrderBusinessChain(oid)
          .then((chain) => setBusinessChain(chain.data.data))
          .catch(() => setBusinessChain(null));
      })
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id, includeAi]);

  const itemSummary = useMemo(() => {
    const items = order?.items || [];
    const quantity = items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    const amount = items.reduce((sum, item) => sum + Number(item.total_price || 0), 0);
    return { count: items.length, quantity, amount };
  }, [order]);

  const paymentSummary = useMemo(() => {
    const paid = payments.filter((p) => p.status === "completed").reduce((s, p) => s + Number(p.amount || 0), 0);
    const total = order?.total_amount || 0;
    const outstanding = Math.max(0, total - paid);
    const pct = total > 0 ? (paid / total) * 100 : 0;
    return { paid, total, outstanding, pct };
  }, [payments, order]);

  const financialSummary = useMemo(() => {
    const gross = Number(order?.total_amount || 0);
    const untaxed = (order?.items || []).reduce((sum, item) => {
      const lineTotal = Number(item.total_price || 0);
      const taxRate = Number(item.tax_rate || 0) / 100;
      return sum + (taxRate > 0 ? lineTotal / (1 + taxRate) : lineTotal);
    }, 0);
    return { gross, untaxed, tax: Math.max(gross - untaxed, 0) };
  }, [order]);

  const itemProgress = useMemo(
    () => new Map((businessChain?.item_progress || []).map((item) => [item.order_item_id, item])),
    [businessChain],
  );

  const isDeliveryOverdue = Boolean(
    order?.delivery_date
    && new Date(order.delivery_date).getTime() < Date.now()
    && (businessChain?.progress.pending_delivery_quantity || 0) > 0,
  );

  const runAction = async (action: () => Promise<void>, success: string) => {
    setActionLoading(true);
    try {
      await action();
      message.success(success);
      if (order) {
        const resp = await getSalesOrder(order.id, includeAi);
        setOrder(resp.data.data);
      }
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "操作失败")); } finally {
      setActionLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (!order) return;
    setPdfDownloading(true);
    try {
      const values = await pdfForm.validateFields();
      await downloadSalesOrderPDF(order.id, `sales_order_${order.order_no || order.id}.pdf`, values);
      setPdfOpen(false);
    } catch (err: unknown) {
      if (err && typeof err === "object" && "errorFields" in err) return;
      message.error("下载失败");
    } finally {
      setPdfDownloading(false);
    }
  };

  if (loading) {
    return (
      <SalesModuleShell title="订单详情" activeKey="orders">
        <Spin style={{ display: "block", margin: "100px auto" }} />
      </SalesModuleShell>
    );
  }

  if (error) {
    return (
      <SalesModuleShell title="订单详情" activeKey="orders">
        <Alert type="error" message={error} />
      </SalesModuleShell>
    );
  }

  if (!order) {
    return (
      <SalesModuleShell title="订单详情" activeKey="orders">
        <Empty description="订单不存在" />
      </SalesModuleShell>
    );
  }

  return (
    <SalesModuleShell
      title={order.order_no || `订单 #${order.id}`}
      subtitle={order.notes ? `备注: ${order.notes}` : "销售订单详情，含产品明细和交付执行信息"}
      activeKey="orders"
      extra={(
        <>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/orders")}>返回</Button>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/orders/${order.id}/edit`)}>编辑</Button>
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </>
      )}
    >
      <SalesOrderPrint order={order} />
      <MetricBand
        items={[
          { title: "价税合计", value: order.total_amount || 0, prefix: "¥", precision: 2 },
          { title: "待发数量", value: businessChain?.progress.pending_delivery_quantity ?? itemSummary.quantity, suffix: "件" },
          { title: "未开票", value: businessChain?.progress.uninvoiced_amount ?? order.total_amount, prefix: "¥", precision: 2 },
          { title: "未回款", value: businessChain?.progress.outstanding_amount ?? paymentSummary.outstanding, prefix: "¥", precision: 2 },
          { title: "状态", value: order.status },
          { title: "交付日期", value: order.delivery_date ? shortDate(order.delivery_date) : "-" },
        ]}
      />

      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          {["pending", "draft"].includes(order.status) ? (
            <Button
              type="primary"
              style={{ background: "#52c41a", borderColor: "#52c41a" }}
              loading={actionLoading}
              onClick={() => runAction(
                () => updateSalesOrder(order.id, { status: "confirmed" }).then(() => {}),
                "订单已确认，库存已锁定",
              )}
            >
              确认订单
            </Button>
          ) : null}
          <Button
            icon={<CarOutlined />}
            loading={actionLoading}
            onClick={() => runAction(async () => {
              await convertSalesOrderToDelivery(order.id);
              navigate("/sales/delivery-notes");
            }, "已转为发货单")}
          >
            转发货单
          </Button>
          <Button icon={<DownloadOutlined />} onClick={() => setPdfOpen(true)}>智能PDF</Button>
          <Button icon={<PrinterOutlined />} onClick={() => window.print()}>打印销售订单</Button>
        </Space>
      </Card>

      <Modal
        title="自定义订单 PDF"
        open={pdfOpen}
        onCancel={() => setPdfOpen(false)}
        onOk={handleDownloadPDF}
        confirmLoading={pdfDownloading}
        okText="下载 PDF"
        width={680}
      >
        <Form
          form={pdfForm}
          layout="vertical"
          onValuesChange={(changed) => {
            if (!("template" in changed)) return;
            if (changed.template === "smart") {
              pdfForm.setFieldsValue({ show_smart_summary: true, show_line_hints: true, show_terms: true, show_notes: true, show_signature: true });
            } else if (changed.template === "standard") {
              pdfForm.setFieldsValue({ show_smart_summary: false, show_line_hints: false, show_terms: true, show_notes: true, show_signature: true });
            } else if (changed.template === "compact") {
              pdfForm.setFieldsValue({ show_smart_summary: false, show_line_hints: false, show_terms: true, show_notes: false, show_signature: false });
            }
          }}
          initialValues={{
            template: "smart",
            document_title: "正式销售订单 / SALES ORDER",
            show_smart_summary: true,
            show_line_hints: true,
            show_terms: true,
            show_notes: true,
            show_signature: true,
            terms: [
              "1、订单产品、数量、单价、交期以双方确认的销售订单为准；",
              "2、交付前请确认库存、包装、收货地址及客户验收要求；",
              "3、付款方式、发票及运输方式以合同或双方最终确认为准；",
            ].join("\n"),
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            <Form.Item name="template" label="PDF 形式">
              <Select options={[
                { value: "smart", label: "智能版：含交付摘要" },
                { value: "standard", label: "标准版：订单和条款" },
                { value: "compact", label: "紧凑版：适合打印" },
              ]} />
            </Form.Item>
            <Form.Item name="company_name" label="抬头公司">
              <Input placeholder="默认取客户公司名称" />
            </Form.Item>
          </div>
          <Form.Item name="document_title" label="文档标题">
            <Input />
          </Form.Item>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            <Form.Item name="prepared_by" label="制单人">
              <Input placeholder="销售 / 商务负责人" />
            </Form.Item>
            <Form.Item name="contact_phone" label="联系电话">
              <Input placeholder="对外联系号码" />
            </Form.Item>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8 }}>
            <Form.Item name="show_smart_summary" valuePropName="checked"><Checkbox>智能摘要</Checkbox></Form.Item>
            <Form.Item name="show_line_hints" valuePropName="checked"><Checkbox>交付提示</Checkbox></Form.Item>
            <Form.Item name="show_terms" valuePropName="checked"><Checkbox>交付条款</Checkbox></Form.Item>
            <Form.Item name="show_notes" valuePropName="checked"><Checkbox>订单备注</Checkbox></Form.Item>
            <Form.Item name="show_signature" valuePropName="checked"><Checkbox>签署确认栏</Checkbox></Form.Item>
          </div>
          <Form.Item name="terms" label="交付条款">
            <Input.TextArea rows={5} />
          </Form.Item>
        </Form>
      </Modal>

      <div className="erp-detail-two-column">
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Card
            title="订单信息"
            size="small"
            extra={<SalesStatusTag value={order.status} />}
          >
            <Descriptions column={2} size="small">
              <Descriptions.Item label="订单号">{order.order_no || `#${order.id}`}</Descriptions.Item>
              <Descriptions.Item label="客户"><CustomerLink id={order.customer_id} /></Descriptions.Item>
              <Descriptions.Item label="总金额">{money(order.total_amount)}</Descriptions.Item>
              <Descriptions.Item label="下单日期">{shortDate(order.order_date)}</Descriptions.Item>
              <Descriptions.Item label="预计交货">{shortDate(order.delivery_date)}</Descriptions.Item>
              <Descriptions.Item label="客户订单号">{order.customer_po_no || "-"}</Descriptions.Item>
              <Descriptions.Item label="关联报价">{order.quotation_no || (order.quotation_id ? `报价 #${order.quotation_id}` : "-")}</Descriptions.Item>
              <Descriptions.Item label="币种">{order.currency || "CNY"}</Descriptions.Item>
              <Descriptions.Item label="贸易条款">{order.incoterms || "-"}</Descriptions.Item>
              <Descriptions.Item label="付款条件">{order.payment_terms || "-"}</Descriptions.Item>
              <Descriptions.Item label="付款到期日">{shortDate(order.due_date)}</Descriptions.Item>
              <Descriptions.Item label="收货地址" span={2}>{order.shipping_address || "-"}</Descriptions.Item>
              <Descriptions.Item label="开票地址" span={2}>{order.billing_address || "-"}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{order.notes || "-"}</Descriptions.Item>
            </Descriptions>
          </Card>

          {businessChain && (
            <Card title="业务链与履约进度" size="small">
              <Descriptions column={3} size="small">
                <Descriptions.Item label="来源商机">{businessChain.opportunity?.number || "-"}</Descriptions.Item>
                <Descriptions.Item label="来源报价">{businessChain.quotation?.number || "-"}</Descriptions.Item>
                <Descriptions.Item label="合同">{businessChain.contracts.map((item) => item.number).join("、") || "-"}</Descriptions.Item>
                <Descriptions.Item label="发货进度">
                  {businessChain.progress.delivered_quantity}/{businessChain.progress.ordered_quantity}（{businessChain.progress.delivery_percent}%）
                </Descriptions.Item>
                <Descriptions.Item label="开票进度">
                  {money(businessChain.progress.invoiced_amount)} / {money(businessChain.progress.order_amount)}
                </Descriptions.Item>
                <Descriptions.Item label="回款进度">
                  {money(businessChain.progress.paid_amount)} / {money(businessChain.progress.order_amount)}
                </Descriptions.Item>
                <Descriptions.Item label="待发数量">{businessChain.progress.pending_delivery_quantity}</Descriptions.Item>
                <Descriptions.Item label="未开票">{money(businessChain.progress.uninvoiced_amount)}</Descriptions.Item>
                <Descriptions.Item label="未回款">
                  <Typography.Text type={businessChain.progress.outstanding_amount > 0 ? "danger" : undefined}>
                    {money(businessChain.progress.outstanding_amount)}
                  </Typography.Text>
                </Descriptions.Item>
              </Descriptions>
              <Divider style={{ margin: "12px 0" }} />
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                {[
                  { title: "合同", rows: businessChain.contracts, path: "contracts" },
                  { title: "发货单", rows: businessChain.deliveries, path: "delivery-notes" },
                  { title: "发票", rows: businessChain.invoices, path: "invoices" },
                  { title: "回款", rows: businessChain.payments, path: "payments" },
                ].map((group) => (
                  <div key={group.title}>
                    <Typography.Text strong>{group.title}（{group.rows.length}）</Typography.Text>
                    <Table
                      style={{ marginTop: 6 }}
                      rowKey="id"
                      size="small"
                      pagination={false}
                      locale={{ emptyText: `暂无${group.title}` }}
                      dataSource={group.rows}
                      columns={[
                        { title: "单据号", dataIndex: "number", render: (value: string, row) => (
                          <Typography.Link onClick={() => navigate(group.path === "payments" ? `/sales/payments/${row.id}/edit` : `/sales/${group.path}/${row.id}`)}>{value}</Typography.Link>
                        ) },
                        { title: "状态", dataIndex: "status", width: 110, render: (value: string) => <SalesStatusTag value={value} /> },
                        { title: "日期", dataIndex: "date", width: 110, render: (value: string | null) => shortDate(value) },
                        { title: "金额", dataIndex: "amount", width: 120, align: "right", render: (value?: number) => value == null ? "-" : money(value) },
                      ]}
                    />
                  </div>
                ))}
              </Space>
            </Card>
          )}

          <Card
            title="订单明细"
            size="small"
            extra={(
              <Space>
                <Tooltip title={showExtraColumns ? "隐藏备注列" : "显示备注列"}>
                  <Button
                    size="small"
                    type={showExtraColumns ? "primary" : "default"}
                    icon={showExtraColumns ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                    onClick={() => setShowExtraColumns((prev) => !prev)}
                  >
                    {showExtraColumns ? "隐藏备注" : "查看备注"}
                  </Button>
                </Tooltip>
                <ErpExportButton
                  data={order.items as unknown as Record<string, unknown>[]}
                  columns={[
                    { key: "product_id", title: "产品ID" },
                    { key: "product_name", title: "产品" },
                    { key: "unit", title: "单位" },
                    { key: "quantity", title: "数量" },
                    { key: "unit_price", title: "单价" },
                    { key: "total_price", title: "小计" },
                  ]}
                  filename={`sales_order_${order.order_no || order.id}_items.csv`}
                />
              </Space>
            )}
          >
            <Table
              rowKey="id"
              dataSource={order.items}
              size="small"
              pagination={false}
              columns={[
                { title: "#", width: 40, render: (_: unknown, __: SalesOrderItem, index: number) => index + 1 },
                { title: "产品编码", width: 120, render: (_: unknown, row: SalesOrderItem) => itemProgress.get(row.id)?.product_code || (row.product_id ? `#${row.product_id}` : "-") },
                { title: "产品名称 / 规格", dataIndex: "product_name", ellipsis: true },
                { title: "单位", dataIndex: "unit", width: 65, render: (v: string | null) => v || "-" },
                { title: "订单数量", dataIndex: "quantity", width: 85, align: "right" as const },
                { title: "已发", width: 70, align: "right" as const, render: (_: unknown, row: SalesOrderItem) => itemProgress.get(row.id)?.delivered_quantity ?? 0 },
                { title: "待发", width: 70, align: "right" as const, render: (_: unknown, row: SalesOrderItem) => <Typography.Text type={(itemProgress.get(row.id)?.pending_quantity ?? row.quantity) > 0 ? "warning" : undefined}>{itemProgress.get(row.id)?.pending_quantity ?? row.quantity}</Typography.Text> },
                { title: "单价", dataIndex: "unit_price", width: 110, align: "right" as const, render: (v: number | null) => (v != null ? money(v) : "-") },
                { title: "折扣", dataIndex: "discount_rate", width: 70, align: "right" as const, render: (v: number | null) => v != null ? `${v}%` : "-" },
                { title: "税率", dataIndex: "tax_rate", width: 70, align: "right" as const, render: (v: number | null) => v != null ? `${v}%` : "-" },
                { title: "价税合计", dataIndex: "total_price", width: 120, align: "right" as const, render: (v: number | null) => (v != null ? <Typography.Text strong>{money(v)}</Typography.Text> : "-") },
                ...(showExtraColumns ? [{ title: "备注", dataIndex: "notes" as keyof SalesOrderItem, width: 160, ellipsis: true, render: (v: string | null) => v || "-" }] : []),
              ]}
              summary={() => (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0}><Typography.Text strong>合计</Typography.Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={1} />
                  <Table.Summary.Cell index={2} />
                  <Table.Summary.Cell index={3} />
                  <Table.Summary.Cell index={4}><Typography.Text strong>{itemSummary.quantity}</Typography.Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={5}><Typography.Text strong>{businessChain?.progress.delivered_quantity || 0}</Typography.Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={6}><Typography.Text strong>{businessChain?.progress.pending_delivery_quantity ?? itemSummary.quantity}</Typography.Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={7} />
                  <Table.Summary.Cell index={8} />
                  <Table.Summary.Cell index={9} />
                  <Table.Summary.Cell index={10}><Typography.Text strong>{money(itemSummary.amount)}</Typography.Text></Table.Summary.Cell>
                </Table.Summary.Row>
              )}
              scroll={{ x: "max-content" }}
            />
          </Card>

          {includeAi && order.ai ? <SalesAIInsight aiData={order.ai} /> : null}
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
          <Card size="small" title={<><DollarOutlined /> 订单摘要</>}>
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">未税金额</Typography.Text>
                <Typography.Text>{money(financialSummary.untaxed)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">税额</Typography.Text>
                <Typography.Text>{money(financialSummary.tax)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">价税合计</Typography.Text>
                <Typography.Text strong>{money(financialSummary.gross)}</Typography.Text>
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
                <SalesStatusTag value={order.status} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">下单日期</Typography.Text>
                <Typography.Text>{shortDate(order.order_date)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">交付日期</Typography.Text>
                <Typography.Text>{shortDate(order.delivery_date)}</Typography.Text>
              </div>
            </Space>
          </Card>

          <Card size="small" title="履约与风险">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              <div>
                <Typography.Text type="secondary">发货进度</Typography.Text>
                <Progress size="small" percent={businessChain?.progress.delivery_percent || 0} />
              </div>
              <div>
                <Typography.Text type="secondary">开票进度</Typography.Text>
                <Progress size="small" percent={businessChain?.progress.invoice_percent || 0} />
              </div>
              <div>
                <Typography.Text type="secondary">回款进度</Typography.Text>
                <Progress size="small" percent={businessChain?.progress.payment_percent || 0} />
              </div>
              {isDeliveryOverdue ? <Alert showIcon type="error" message="订单已超过预计交期，仍有待发数量" /> : null}
              {businessChain && businessChain.contracts.length === 0 ? <Alert showIcon type="warning" message="订单尚未关联合同" /> : null}
              {businessChain && businessChain.progress.outstanding_amount > 0 ? <Alert showIcon type="warning" message={`尚有 ${money(businessChain.progress.outstanding_amount)} 未回款`} /> : null}
              {!isDeliveryOverdue && businessChain?.contracts.length && businessChain.progress.outstanding_amount <= 0 ? <Alert showIcon type="success" message="当前未发现履约异常" /> : null}
            </Space>
          </Card>

          <Card size="small" title={<><DollarOutlined /> 回款情况</>}>
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">订单金额</Typography.Text>
                <Typography.Text strong>{money(paymentSummary.total)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">已回款</Typography.Text>
                <Typography.Text style={{ color: "#52c41a" }}>{money(paymentSummary.paid)}</Typography.Text>
              </div>
              <Divider style={{ margin: "6px 0" }} />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text strong>未回款</Typography.Text>
                <Typography.Text strong type={paymentSummary.outstanding > 0 ? "danger" : undefined}>
                  {money(paymentSummary.outstanding)}
                </Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">回款进度</Typography.Text>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div style={{
                    width: 60, height: 6, borderRadius: 3, background: "#f0f0f0",
                    overflow: "hidden",
                  }}>
                    <div style={{
                      width: `${Math.min(paymentSummary.pct, 100)}%`, height: "100%",
                      background: paymentSummary.pct >= 100 ? "#52c41a" : paymentSummary.pct > 0 ? "#1677ff" : "#f0f0f0",
                      borderRadius: 3, transition: "width 0.3s",
                    }} />
                  </div>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {paymentSummary.pct.toFixed(0)}%
                  </Typography.Text>
                </div>
              </div>
              {paymentSummary.outstanding > 0 && (
                <Button size="small" block icon={<DollarOutlined />} style={{ marginTop: 4 }}
                  onClick={() => navigate(`/sales/payments/new?order_id=${order.id}&customer_id=${order.customer_id}`)}>
                  登记回款
                </Button>
              )}
            </Space>
          </Card>

          <Card size="small" title="状态流转">
            <ErpStatusTimeline
              currentStatus={order.status}
              steps={STATUS_STEPS}
              createdAt={order.created_at}
              lostStatus="cancelled"
            />
          </Card>

          <Card size="small" title="下一步动作">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              {["pending", "draft"].includes(order.status) ? (
                <Alert showIcon type="info" message="订单待确认，建议检查产品明细和交期后确认。" />
              ) : order.status === "confirmed" ? (
                <Alert showIcon type="success" message="订单已确认，可转为发货单执行交付。" />
              ) : order.status === "shipped" ? (
                <Alert showIcon type="info" message="已发货，需跟进客户签收确认。" />
              ) : order.status === "delivered" ? (
                <Alert showIcon type="success" message="订单已完成签收。" />
              ) : null}
              <Button block icon={<EditOutlined />} onClick={() => navigate(`/sales/orders/${order.id}/edit`)}>编辑订单</Button>
              {order.customer_id ? (
                <Button block onClick={() => navigate(`/customers/${order.customer_id}`)}>查看客户</Button>
              ) : null}
            </Space>
          </Card>
        </Space>
      </div>
    </SalesModuleShell>
  );
}
