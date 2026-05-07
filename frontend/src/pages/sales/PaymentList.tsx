import { useEffect, useState } from "react";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select, DatePicker, InputNumber, Popconfirm } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import {
  getPaymentRecords, createPaymentRecord, updatePaymentRecord, deletePaymentRecord,
  getCustomers, getSalesOrders,
} from "../../api";
import type { PaymentRecord, Customer, SalesOrder } from "../../types";

const statusColors: Record<string, string> = { pending: "orange", received: "green", overdue: "red" };
const methodLabels: Record<string, string> = { bank: "银行转账", cash: "现金", wx: "微信", alipay: "支付宝" };

export default function PaymentList() {
  const [data, setData] = useState<PaymentRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [form] = Form.useForm();

  const [filters, setFilters] = useState({ customer_id: "", order_id: "", status: "" });

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (filters.customer_id) params.customer_id = Number(filters.customer_id);
      if (filters.order_id) params.order_id = Number(filters.order_id);
      if (filters.status) params.status = filters.status;
      const resp = await getPaymentRecords(params);
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [page, filters]);

  const loadRefs = async () => {
    try {
      const [cResp, oResp] = await Promise.all([
        getCustomers({ page: 1, page_size: 200 }),
        getSalesOrders({ page: 1, page_size: 200 }),
      ]);
      setCustomers(cResp.data.data.list || []);
      setOrders(oResp.data.data.list || []);
    } catch { /* ignore */ }
  };

  const openCreate = () => { setEditingId(null); form.resetFields(); loadRefs(); setModalOpen(true); };
  const openEdit = async (r: PaymentRecord) => {
    setEditingId(r.id); await loadRefs();
    form.setFieldsValue({ ...r, payment_date: r.payment_date ? dayjs(r.payment_date) : null });
    setModalOpen(true);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const data = { ...values, payment_date: values.payment_date ? dayjs(values.payment_date as string).format("YYYY-MM-DDTHH:mm:ss") : null };
      if (editingId) { await updatePaymentRecord(editingId, data); message.success("更新成功"); }
      else { await createPaymentRecord(data); message.success("创建成功"); }
      form.resetFields(); setModalOpen(false); fetch(1);
    } catch { message.error("操作失败"); }
  };

  const handleDelete = async (id: number) => {
    try { await deletePaymentRecord(id); message.success("已删除"); fetch(page); } catch { message.error("删除失败"); }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "客户", dataIndex: "customer_id", width: 80 },
    { title: "订单ID", dataIndex: "sales_order_id", width: 80 },
    { title: "金额", dataIndex: "amount", width: 120, render: (v: number) => `¥${v.toFixed(2)}` },
    { title: "回款日期", dataIndex: "payment_date", width: 120 },
    { title: "方式", dataIndex: "payment_method", width: 100, render: (v: string) => methodLabels[v] || v },
    { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag> },
    { title: "备注", dataIndex: "notes", ellipsis: true },
    {
      title: "操作", width: 120, render: (_: unknown, r: PaymentRecord) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input.Search placeholder="客户ID" style={{ width: 120 }} onSearch={v => setFilters(f => ({ ...f, customer_id: v }))} />
        <Input.Search placeholder="订单ID" style={{ width: 120 }} onSearch={v => setFilters(f => ({ ...f, order_id: v }))} />
        <Select placeholder="状态" allowClear style={{ width: 100 }} onChange={v => setFilters(f => ({ ...f, status: v || "" }))}>
          <Select.Option value="pending">待回款</Select.Option>
          <Select.Option value="received">已回款</Select.Option>
          <Select.Option value="overdue">逾期</Select.Option>
        </Select>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增回款</Button>
      </Space>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />

      <Modal title={editingId ? "编辑回款" : "新增回款"} open={modalOpen} onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()} width={500}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="sales_order_id" label="销售订单" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={orders.map(o => ({ label: `${o.order_no} (ID:${o.id})`, value: o.id }))} />
          </Form.Item>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={customers.map(c => ({ label: `${c.name} (ID:${c.id})`, value: c.id }))} />
          </Form.Item>
          <Form.Item name="amount" label="金额" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="payment_date" label="回款日期">
            <DatePicker showTime style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="payment_method" label="支付方式">
            <Select options={Object.entries(methodLabels).map(([k, v]) => ({ label: v, value: k }))} />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={[{ label: "待回款", value: "pending" }, { label: "已回款", value: "received" }, { label: "逾期", value: "overdue" }]} />
          </Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
