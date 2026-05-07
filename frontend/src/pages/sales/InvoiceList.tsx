import { useEffect, useState } from "react";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select, DatePicker, InputNumber, Popconfirm } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import { getInvoices, createInvoice, updateInvoice, deleteInvoice, issueInvoice, voidInvoice, getCustomers, getSalesOrders } from "../../api";
import type { Invoice, Customer, SalesOrder } from "../../types";

const statusColors: Record<string, string> = { draft: "default", issued: "green", void: "red" };
const typeOptions = [{ label: "普通发票", value: "普通发票" }, { label: "增值税发票", value: "增值税发票" }];

export default function InvoiceList() {
  const [data, setData] = useState<Invoice[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const [filters, setFilters] = useState({ customer_id: "", order_id: "", status: "" });

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (filters.customer_id) params.customer_id = Number(filters.customer_id);
      if (filters.order_id) params.order_id = Number(filters.order_id);
      if (filters.status) params.status = filters.status;
      const resp = await getInvoices(params);
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
  const openEdit = async (r: Invoice) => {
    setEditingId(r.id); await loadRefs();
    form.setFieldsValue({ ...r, invoice_date: r.invoice_date ? dayjs(r.invoice_date) : null });
    setModalOpen(true);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const data = { ...values, invoice_date: values.invoice_date ? dayjs(values.invoice_date as string).format("YYYY-MM-DDTHH:mm:ss") : null };
      if (editingId) { await updateInvoice(editingId, data); message.success("更新成功"); }
      else { await createInvoice(data); message.success("创建成功"); }
      form.resetFields(); setModalOpen(false); fetch(1);
    } catch { message.error("操作失败"); }
  };

  const handleDelete = async (id: number) => {
    try { await deleteInvoice(id); message.success("已删除"); fetch(page); } catch { message.error("删除失败"); }
  };

  const handleIssue = async (id: number) => {
    try { await issueInvoice(id); message.success("发票已开具"); fetch(page); } catch { message.error("操作失败"); }
  };
  const handleVoid = async (id: number) => {
    try { await voidInvoice(id); message.success("发票已作废"); fetch(page); } catch { message.error("操作失败"); }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "发票号", dataIndex: "invoice_no", width: 120 },
    { title: "客户ID", dataIndex: "customer_id", width: 80 },
    { title: "订单ID", dataIndex: "sales_order_id", width: 80 },
    { title: "金额", dataIndex: "amount", width: 100, render: (v: number) => `¥${v.toFixed(2)}` },
    { title: "税额", dataIndex: "tax_amount", width: 100, render: (v: number) => `¥${v.toFixed(2)}` },
    { title: "类型", dataIndex: "invoice_type", width: 100 },
    { title: "开票日期", dataIndex: "invoice_date", width: 120 },
    { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag> },
    {
      title: "操作", width: 220, render: (_: unknown, r: Invoice) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/sales/invoices/${r.id}`)} />
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          {r.status === "draft" && <Button size="small" onClick={() => handleIssue(r.id)}>开具</Button>}
          {r.status === "issued" && <Button size="small" danger onClick={() => handleVoid(r.id)}>作废</Button>}
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
          <Select.Option value="draft">草稿</Select.Option>
          <Select.Option value="issued">已开具</Select.Option>
          <Select.Option value="void">已作废</Select.Option>
        </Select>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增发票</Button>
      </Space>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />

      <Modal title={editingId ? "编辑发票" : "新增发票"} open={modalOpen} onCancel={() => setModalOpen(false)}
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
          <Form.Item name="tax_amount" label="税额"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="invoice_type" label="发票类型"><Select options={typeOptions} /></Form.Item>
          <Form.Item name="invoice_date" label="开票日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
