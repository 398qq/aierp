import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Form, Input, Select, InputNumber, DatePicker, Button, message } from "antd";
import { getPayment, createPayment, updatePayment, getCustomers, getSalesOrders } from "../../api";
import dayjs from "dayjs";
import type { Customer, SalesOrder } from "../../types";

export default function PaymentForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const isEdit = !!id;

  useEffect(() => {
    getCustomers({ page: 1, page_size: 200 }).then((r) => setCustomers(r.data.data.list || []));
    getSalesOrders({ page: 1, page_size: 200 }).then((r) => setOrders(r.data.data.list || []));
    if (isEdit) {
      getPayment(Number(id)).then((r) => {
        const p = r.data.data;
        form.setFieldsValue({ ...p, payment_date: p.payment_date ? dayjs(p.payment_date) : null });
      });
    }
  }, [id]);

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
    <Card title={isEdit ? "编辑回款" : "新增回款"}>
      <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ status: "pending", payment_method: "bank" }}>
        <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
          <Select showSearch placeholder="选择客户" options={customers.map((c) => ({ value: c.id, label: c.name }))} />
        </Form.Item>
        <Form.Item name="sales_order_id" label="关联销售订单" rules={[{ required: true }]}>
          <Select showSearch placeholder="选择订单" options={orders.map((o) => ({ value: o.id, label: o.order_no || `#${o.id}` }))} />
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
