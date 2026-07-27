import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Alert, Button, Card, Checkbox, DatePicker, Descriptions, Empty, Form, InputNumber, Modal, Select, Space, Spin, Typography, message } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { ArrowLeftOutlined, CheckCircleOutlined, EditOutlined, PrinterOutlined, SendOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { confirmLargePurchaseOrder, confirmPurchaseOrderSupplier, getApiErrorMessage, getPurchaseOrder, receivePurchaseOrder, transitionPurchaseOrder } from "../../api";
import type { PurchaseOrder, PurchaseOrderItem } from "../../types";
import { StatusTag } from "../../ui";
import { ErpStatusTimeline, MetricBand, SalesModuleShell, money, shortDate } from "./salesUi";
import { PurchaseOrderPrint } from "./PurchaseOrderPrint";

const STATUS: Record<string, { label: string; tone: "neutral" | "info" | "processing" | "success" | "danger" }> = {
  draft: { label: "草稿", tone: "neutral" }, approved: { label: "已审批", tone: "info" },
  ordered: { label: "已下单", tone: "processing" }, partially_received: { label: "部分收货", tone: "processing" },
  received: { label: "已收货", tone: "success" }, cancelled: { label: "已取消", tone: "danger" },
};
const STEPS = ["draft", "approved", "ordered", "partially_received", "received"].map((key) => ({ key, label: STATUS[key].label }));

export default function PurchaseOrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [po, setPo] = useState<(PurchaseOrder & { items: PurchaseOrderItem[] }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [receiveOpen, setReceiveOpen] = useState(false);
  const [warehouseId, setWarehouseId] = useState(1);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [printOpen, setPrintOpen] = useState(false);
  const [includeCustomerReferences, setIncludeCustomerReferences] = useState(false);
  const [confirmationForm] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try { const response = await getPurchaseOrder(Number(id)); setPo(response.data.data); }
    catch (error: unknown) { message.error(getApiErrorMessage(error, "加载采购订单失败")); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [id]);

  const summary = useMemo(() => ({
    quantity: (po?.items || []).reduce((sum, item) => sum + Number(item.quantity || 0), 0),
    amount: (po?.items || []).reduce((sum, item) => sum + Number(item.amount || 0), 0),
  }), [po]);

  const transition = async (target: string) => {
    if (!po) return;
    setActing(true);
    try { await transitionPurchaseOrder(po.id, target); message.success("采购订单状态已更新"); await load(); }
    catch (error: unknown) { message.error(getApiErrorMessage(error, "状态更新失败")); }
    finally { setActing(false); }
  };
  const confirmLarge = async () => {
    if (!po) return;
    setActing(true);
    try { await confirmLargePurchaseOrder(po.id); message.success("大额采购已完成二次确认"); await load(); }
    catch (error: unknown) { message.error(getApiErrorMessage(error, "二次确认失败")); }
    finally { setActing(false); }
  };
  const confirmSupplier = async () => {
    if (!po) return;
    const values = await confirmationForm.validateFields();
    setActing(true);
    try {
      await confirmPurchaseOrderSupplier(po.id, { ...values, confirmed_delivery_date: dayjs(values.confirmed_delivery_date).format("YYYY-MM-DD") });
      message.success("供应商书面确认已记录"); setConfirmOpen(false); await load();
    } catch (error: unknown) { message.error(getApiErrorMessage(error, "记录供应商确认失败")); }
    finally { setActing(false); }
  };
  const receive = async () => {
    if (!po) return;
    setActing(true);
    try { await receivePurchaseOrder(po.id, warehouseId); message.success("收货入库完成"); setReceiveOpen(false); await load(); }
    catch (error: unknown) { message.error(getApiErrorMessage(error, "收货失败")); }
    finally { setActing(false); }
  };
  const openPrintDialog = () => {
    setIncludeCustomerReferences(false);
    setPrintOpen(true);
  };
  const confirmPrint = () => {
    setPrintOpen(false);
    window.setTimeout(() => window.print(), 0);
  };

  if (loading) return <SalesModuleShell title="采购订单详情" activeKey="procurement"><Spin style={{ display: "block", margin: 80 }} /></SalesModuleShell>;
  if (!po) return <SalesModuleShell title="采购订单详情" activeKey="procurement"><Empty description="采购订单不存在" /></SalesModuleShell>;
  const needsLargeConfirm = po.total_amount > 10000 && !po.large_order_confirmed;

  return <SalesModuleShell title={po.order_no || `PO #${po.id}`} subtitle={`采购订单模板 ${po.contract_terms_version || "v3.4"}`} activeKey="procurement" extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/purchase-orders")}>返回列表</Button>}>
    <PurchaseOrderPrint po={po} includeCustomerReferences={includeCustomerReferences} />
    <MetricBand items={[
      { title: "价税合计", value: po.total_amount, prefix: "¥", precision: 2 }, { title: "总数量", value: summary.quantity, suffix: "pcs" },
      { title: "明细行", value: po.items.length, suffix: "项" }, { title: "状态", value: STATUS[po.status]?.label || po.status },
      { title: "供应商确认", value: po.supplier_confirmation_status === "confirmed" ? "已确认" : "待确认" },
    ]} />
    <Card size="small" style={{ marginBottom: 12 }}><Space wrap>
      {po.status === "draft" && <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/purchase-orders/${po.id}/edit`)}>编辑</Button>}
      {po.status === "draft" && needsLargeConfirm && <Button danger icon={<SafetyCertificateOutlined />} loading={acting} onClick={() => Modal.confirm({ title: "大额采购二次确认", content: `确认采购金额 ${money(po.total_amount)} 及全部批次、交期要求？`, onOk: confirmLarge })}>二次确认</Button>}
      {po.status === "draft" && !needsLargeConfirm && <Button type="primary" loading={acting} onClick={() => transition("approved")}>审批通过</Button>}
      {po.status === "approved" && <Button type="primary" icon={<SendOutlined />} loading={acting} onClick={() => transition("ordered")}>发送给供应商</Button>}
      {po.status === "ordered" && <Button icon={<CheckCircleOutlined />} onClick={() => setConfirmOpen(true)}>记录供应商确认</Button>}
      {["ordered", "partially_received"].includes(po.status) && <Button type="primary" onClick={() => setReceiveOpen(true)}>采购收货</Button>}
      {["draft", "approved", "ordered", "partially_received"].includes(po.status) && <Button danger onClick={() => Modal.confirm({ title: "取消采购订单", content: "取消后不可恢复，确认继续？", okText: "确认取消", okButtonProps: { danger: true }, onOk: () => transition("cancelled") })}>取消订单</Button>}
      <Button icon={<PrinterOutlined />} onClick={openPrintDialog}>打印采购订单</Button>
    </Space></Card>
    {needsLargeConfirm && <Alert style={{ marginBottom: 12 }} type="warning" showIcon message="金额超过 ¥10,000，审批前必须完成二次确认" />}
    {po.status === "ordered" && po.supplier_confirmation_status !== "confirmed" && <Alert style={{ marginBottom: 12 }} type="warning" showIcon message="供应商须在 PO 发出后 24 小时内书面确认单价、数量、交期、批次和分批交货安排" />}

    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 300px", gap: 12, alignItems: "start" }}>
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        <Card size="small" title="采购订单头信息" extra={<StatusTag tone={STATUS[po.status]?.tone}>{STATUS[po.status]?.label}</StatusTag>}>
          <Descriptions bordered size="small" column={3}>
            <Descriptions.Item label="订单号">{po.order_no}</Descriptions.Item><Descriptions.Item label="创建日期">{shortDate(po.created_at)}</Descriptions.Item><Descriptions.Item label="合同条款">{po.contract_terms_version}</Descriptions.Item>
            <Descriptions.Item label="供应商">{po.supplier_name}</Descriptions.Item><Descriptions.Item label="联系人">{po.supplier_contact || "-"}</Descriptions.Item><Descriptions.Item label="付款方式">{po.payment_terms || "-"}</Descriptions.Item>
            <Descriptions.Item label="预计交期">{shortDate(po.expected_date)}</Descriptions.Item><Descriptions.Item label="关联SO">{po.sales_order_no || "-"}</Descriptions.Item><Descriptions.Item label="客户">{po.customer_name || "-"}</Descriptions.Item>
            <Descriptions.Item label="交货地址" span={3}>{po.delivery_address || "-"}</Descriptions.Item>
            <Descriptions.Item label="备注" span={3}>{po.notes || "-"}</Descriptions.Item>
          </Descriptions>
        </Card>
        <Card size="small" title="采购明细（含税）">
          <ProTable rowKey="id" size="small" bordered pagination={false} scroll={{ x: 1650 }} dataSource={po.items} columns={[
            { title: "#", width: 45, fixed: "left", render: (_v: any, _r: any, index: any) => index + 1 },
            { title: "供应商型号(MPN)", dataIndex: "supplier_mpn", width: 170, fixed: "left" }, { title: "自有SKU", dataIndex: "product_sku", width: 140 },
            { title: "品名", dataIndex: "product_name", width: 180 }, { title: "品牌", dataIndex: "brand_name", width: 100 }, { title: "封装", dataIndex: "package_type", width: 100 },
            { title: "数量(pcs)", dataIndex: "quantity", width: 100, align: "right" }, { title: "最小包装", width: 110, render: (_v: any, r: any) => r.min_pack_qty ? `${r.min_pack_qty}/${r.min_pack_unit || "包"}` : "-" },
            { title: "生产批次", dataIndex: "date_code_requirement", width: 120 }, { title: "含税单价", dataIndex: "unit_price", width: 110, align: "right", render: (value: any) => money(value) },
            { title: "金额", dataIndex: "amount", width: 120, align: "right", render: (value: any) => <Typography.Text strong>{money(value)}</Typography.Text> },
            { title: "备注", dataIndex: "notes", width: 150 },
          ] as any} search={false} options={false} summary={() => <ProTable.Summary.Row><ProTable.Summary.Cell index={0} colSpan={6}><Typography.Text strong>合计</Typography.Text></ProTable.Summary.Cell><ProTable.Summary.Cell index={6}><Typography.Text strong>{summary.quantity.toLocaleString()}</Typography.Text></ProTable.Summary.Cell><ProTable.Summary.Cell index={7} colSpan={3} /><ProTable.Summary.Cell index={10}><Typography.Text strong>{money(summary.amount)}</Typography.Text></ProTable.Summary.Cell><ProTable.Summary.Cell index={11} /></ProTable.Summary.Row>} />
        </Card>
      </Space>
      <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
        <Card size="small" title="金额与控制"><div>未税金额：{money(po.subtotal)}</div><div>税率：{po.tax_rate}%</div><div>税额：{money(po.tax_amount)}</div><div><strong>价税合计：{money(po.total_amount)}</strong></div><div style={{ marginTop: 8 }}>大额确认：{po.large_order_confirmed ? "已确认" : po.total_amount > 10000 ? "待确认" : "无需"}</div></Card>
        <Card size="small" title="状态流转"><ErpStatusTimeline currentStatus={po.status} steps={STEPS} createdAt={po.created_at} lostStatus="cancelled" /></Card>
        <Card size="small" title="供应商确认"><div>状态：{po.supplier_confirmation_status === "confirmed" ? "已书面确认" : "待确认"}</div><div>方式：{po.supplier_confirmation_method || "-"}</div><div>确认交期：{shortDate(po.supplier_confirmed_delivery_date || null)}</div><div>分批交货：{po.allow_partial_delivery ? "允许" : "不允许"}</div></Card>
      </Space>
    </div>

    <Modal title="采购收货" open={receiveOpen} onCancel={() => setReceiveOpen(false)} onOk={receive} confirmLoading={acting}><Typography.Text>入库仓库 ID：</Typography.Text><InputNumber min={1} value={warehouseId} onChange={(value) => setWarehouseId(value || 1)} /></Modal>
    <Modal title="对外打印确认" open={printOpen} onCancel={() => setPrintOpen(false)} onOk={confirmPrint} okText="确认打印" cancelText="取消">
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        <Alert type="warning" showIcon message="客户信息保护" description="关联销售订单、关联客户和内部备注默认不打印，避免向供应商泄露客户及内部业务信息。" />
        <Checkbox checked={includeCustomerReferences} onChange={(event) => setIncludeCustomerReferences(event.target.checked)}>
          显示关联 SO、关联客户及内部备注
        </Checkbox>
        <Typography.Text type="secondary">采购合同条款 v3.4 将固定附在采购订单后打印。</Typography.Text>
      </Space>
    </Modal>
    <Modal title="记录供应商书面确认" open={confirmOpen} onCancel={() => setConfirmOpen(false)} onOk={confirmSupplier} confirmLoading={acting}><Form form={confirmationForm} layout="vertical" initialValues={{ method: "wechat", allow_partial_delivery: false }}><Form.Item name="method" label="确认方式" rules={[{ required: true }]}><Select options={[{ value: "wechat", label: "微信文字" }, { value: "email", label: "电子邮件" }, { value: "erp", label: "ERP确认" }, { value: "sealed_letter", label: "盖章确认函" }, { value: "implied_24h", label: "超过24小时默示接受" }]} /></Form.Item><Form.Item name="confirmed_delivery_date" label="供应商确认交期" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item><Form.Item name="allow_partial_delivery" label="是否允许分批交货"><Select options={[{ value: false, label: "不允许" }, { value: true, label: "允许" }]} /></Form.Item></Form></Modal>
  </SalesModuleShell>;
}
