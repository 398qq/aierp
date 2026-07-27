import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router";
import { Card, Form, Input, Select, InputNumber, DatePicker, Button, message } from "antd";
import { getInvoice, createInvoice, updateInvoice, getSalesOrders } from "../../api";
import dayjs, { type Dayjs } from "dayjs";
import type { SalesOrder } from "../../types";
import { CustomerSelect, SalesModuleShell, shortDate } from "./salesUi";

export default function InvoiceForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const isEdit = !!id;
  const amount = Form.useWatch("amount", form);

  useEffect(() => {
    const numericAmount = Number(amount);
    form.setFieldValue(
      "tax_amount",
      Number.isFinite(numericAmount) ? Math.round(numericAmount * 13) / 100 : 0,
    );
  }, [amount, form]);

  useEffect(() => {
    getSalesOrders({ page: 1, page_size: 100 }).then((r) => setOrders(r.data.data.list || []));
    if (isEdit) {
      getInvoice(Number(id)).then((r) => {
        const inv = r.data.data;
        form.setFieldsValue({ ...inv, invoice_date: inv.invoice_date ? dayjs(inv.invoice_date) : null });
      });
    }
  }, [form, id, isEdit]);

  const orderById = useMemo(() => new Map(orders.map((order) => [order.id, order])), [orders]);

  const applyOrder = (orderId?: number) => {
    const order = orderById.get(Number(orderId));
    if (!order) return;
    form.setFieldsValue({
      customer_id: order.customer_id,
      amount: form.getFieldValue("amount") ?? order.total_amount,
    });
  };

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload = {
        ...values,
        invoice_date: values.invoice_date
          ? (values.invoice_date as Dayjs).toISOString()
          : null,
      };
      if (isEdit) { await updateInvoice(Number(id), payload); message.success("发票已更新"); }
      else { await createInvoice(payload); message.success("发票已创建"); }
      navigate("/sales/invoices");
    } catch (e: unknown) {
      const errMsg =
        (e as { response?: { data?: { msg?: string } } })?.response?.data?.msg ||
        (e as Error)?.message ||
        "保存失败";
      message.error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑发票" : "新增发票"}
      subtitle="填写发票信息，关联销售订单"
      activeKey="invoices"
    >
      <Card size="small">
        <Form form={form} layout="vertical" size="small" onFinish={onFinish} initialValues={{ status: "draft", invoice_type: "普通发票" }}>
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
        <Form.Item name="invoice_no" label="发票号"><Input placeholder="留空自动生成" /></Form.Item>
        <Form.Item name="amount" label="金额" rules={[{ required: true, message: "请输入金额" }]}><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
        <Form.Item name="tax_amount" label="税额（自动按 13% 计算）">
          <InputNumber style={{ width: "100%" }} prefix="¥" precision={2} readOnly />
        </Form.Item>
        <Form.Item name="invoice_type" label="发票类型">
          <Select options={[{ value: "普通发票", label: "普通发票" }, { value: "增值税专用发票", label: "增值税专用发票" }]} />
        </Form.Item>
        <Form.Item name="status" label="状态">
          <Select options={[
            { value: "draft", label: "草稿" }, { value: "issued", label: "已开票" }, { value: "paid", label: "已付款" }, { value: "cancelled", label: "已取消" },
          ]} />
        </Form.Item>
        <Form.Item name="invoice_date" label="开票日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/invoices")}>取消</Button>
        </Form.Item>
      </Form>
      </Card>
    </SalesModuleShell>
  );
}
