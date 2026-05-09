import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Form, Input, Select, InputNumber, DatePicker, Button, message } from "antd";
import { getContract, createContract, updateContract, getCustomers, getSalesOrders } from "../../api";
import dayjs, { type Dayjs } from "dayjs";
import type { Customer, SalesOrder } from "../../types";

export default function ContractForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const isEdit = !!id;

  useEffect(() => {
    getCustomers({ page: 1, page_size: 200 }).then((r) => setCustomers(r.data.data.list || []));
    getSalesOrders({ page: 1, page_size: 100 }).then((r) => setOrders(r.data.data.list || []));
    if (isEdit) {
      getContract(Number(id)).then((r) => {
        const c = r.data.data;
        form.setFieldsValue({ ...c, signed_date: c.signed_date ? dayjs(c.signed_date) : null, expire_date: c.expire_date ? dayjs(c.expire_date) : null });
      });
    }
  }, [id]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload = { ...values, signed_date: values.signed_date ? (values.signed_date as string) : null, expire_date: values.expire_date ? (values.expire_date as string) : null };
      if (isEdit) { await updateContract(Number(id), payload); message.success("合同已更新"); }
      else { await createContract(payload); message.success("合同已创建"); }
      navigate("/sales/contracts");
    } catch { message.error("保存失败"); }
    finally { setLoading(false); }
  };

  return (
    <Card title={isEdit ? "编辑合同" : "新增合同"}>
      <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ status: "draft" }}>
        <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
          <Select showSearch placeholder="选择客户" options={customers.map((c) => ({ value: c.id, label: c.name }))} />
        </Form.Item>
        <Form.Item name="sales_order_id" label="关联订单">
          <Select showSearch allowClear placeholder="选择订单" options={orders.map((o) => ({ value: o.id, label: o.order_no || `#${o.id}` }))} />
        </Form.Item>
        <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="contract_no" label="合同号"><Input placeholder="留空自动生成" /></Form.Item>
        <Form.Item name="amount" label="金额"><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
        <Form.Item name="status" label="状态">
          <Select options={[
            { value: "draft", label: "草稿" }, { value: "signed", label: "已签署" }, { value: "active", label: "履行中" }, { value: "terminated", label: "已终止" },
          ]} />
        </Form.Item>
        <Form.Item name="signed_date" label="签署日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="expire_date" label="到期日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="file_url" label="文件URL"><Input /></Form.Item>
        <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/contracts")}>取消</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
