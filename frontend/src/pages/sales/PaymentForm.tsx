import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Form, Input, Select, InputNumber, DatePicker, Button, message } from "antd";
import { getPayment, createPayment, updatePayment, getSalesOrders, getDeliveryNotes, getInvoices } from "../../api";
import dayjs from "dayjs";
import type { DeliveryNote, Invoice, SalesOrder } from "../../types";
import { CustomerSelect, shortDate } from "./salesUi";

export default function PaymentForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [deliveryNotes, setDeliveryNotes] = useState<DeliveryNote[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const isEdit = !!id;

  useEffect(() => {
    getSalesOrders({ page: 1, page_size: 200 }).then((r) => setOrders(r.data.data.list || []));
    if (isEdit) {
      getPayment(Number(id)).then((r) => {
        const p = r.data.data;
        form.setFieldsValue({ ...p, payment_date: p.payment_date ? dayjs(p.payment_date) : null });
        if (p.sales_order_id) {
          loadDeliveryNotes(p.sales_order_id);
          loadInvoices(p.sales_order_id);
        }
      });
    }
  }, [form, id, isEdit]);

  const orderById = useMemo(() => new Map(orders.map((order) => [order.id, order])), [orders]);

  const loadDeliveryNotes = async (orderId: number) => {
    try {
      const resp = await getDeliveryNotes({ page: 1, page_size: 100, sales_order_id: orderId });
      setDeliveryNotes(resp.data.data.list || []);
    } catch {
      setDeliveryNotes([]);
    }
  };

  const loadInvoices = async (orderId: number) => {
    try {
      const resp = await getInvoices({ page: 1, page_size: 100, sales_order_id: orderId });
      setInvoices(resp.data.data.list || []);
    } catch {
      setInvoices([]);
    }
  };

  const applyOrder = (orderId: number) => {
    const order = orderById.get(orderId);
    if (!order) return;
    form.setFieldsValue({
      customer_id: order.customer_id,
      amount: form.getFieldValue("amount") ?? order.total_amount,
    });
    form.setFieldsValue({ delivery_note_id: undefined, invoice_id: undefined });
    loadDeliveryNotes(orderId);
    loadInvoices(orderId);
  };

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload = { ...values, payment_date: values.payment_date ? (values.payment_date as string) : null };
      if (isEdit) { await updatePayment(Number(id), payload); message.success("回款已更新"); }
      else { await createPayment(payload); message.success("回款已创建"); }
      navigate("/sales/payments");
    } catch { message.error("保存失败"); }
    finally { setLoading(false); }
  };

  return (
    <Card size="small" title={isEdit ? "编辑回款" : "新增回款"}>
      <Form form={form} layout="vertical" size="small" onFinish={onFinish} initialValues={{ status: "pending", payment_method: "bank" }}>
        <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
          <CustomerSelect />
        </Form.Item>
        <Form.Item name="sales_order_id" label="关联销售订单" rules={[{ required: true }]}>
          <Select
            showSearch
            placeholder="选择订单"
            optionFilterProp="label"
            onChange={applyOrder}
            options={orders.map((order) => ({
              value: order.id,
              label: `${order.order_no || `#${order.id}`} / 客户 #${order.customer_id} / ${shortDate(order.delivery_date)}`,
            }))}
          />
        </Form.Item>
        <Form.Item name="delivery_note_id" label="关联发货单">
          <Select
            allowClear
            placeholder="选择发货单（可选）"
            options={deliveryNotes.map((dn) => ({
              value: dn.id,
              label: `${dn.delivery_no || `#${dn.id}`} / ${shortDate(dn.delivery_date)}`,
            }))}
          />
        </Form.Item>
        <Form.Item name="invoice_id" label="关联发票（核销）">
          <Select
            allowClear
            placeholder="选择发票进行核销（可选）"
            options={invoices.map((inv) => ({
              value: inv.id,
              label: `${inv.invoice_no || `#${inv.id}`} / ¥${inv.amount.toLocaleString("zh-CN")} / ${inv.status}`,
            }))}
          />
        </Form.Item>
        <Form.Item name="amount" label="金额" rules={[{ required: true }]}><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
        <Form.Item name="payment_method" label="付款方式">
          <Select options={[{ value: "bank", label: "银行转账" }, { value: "cash", label: "现金" }, { value: "check", label: "支票" }]} />
        </Form.Item>
        <Form.Item name="payment_date" label="付款日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="status" label="状态">
          <Select options={[
            { value: "pending", label: "待收款" }, { value: "completed", label: "已收款" }, { value: "overdue", label: "逾期" },
          ]} />
        </Form.Item>
        <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/payments")}>取消</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
