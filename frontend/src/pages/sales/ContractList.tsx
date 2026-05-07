import { useEffect, useState } from "react";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select, DatePicker, InputNumber, Popconfirm } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import { getContracts, createContract, updateContract, deleteContract, getCustomers, getSalesOrders } from "../../api";
import type { Contract, Customer, SalesOrder } from "../../types";

const statusColors: Record<string, string> = { draft: "default", active: "green", expired: "orange", terminated: "red" };

export default function ContractList() {
  const [data, setData] = useState<Contract[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [filters, setFilters] = useState({ customer_id: "", status: "" });

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (filters.customer_id) params.customer_id = Number(filters.customer_id);
      if (filters.status) params.status = filters.status;
      const resp = await getContracts(params);
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
  const openEdit = (r: Contract) => {
    setEditingId(r.id); loadRefs();
    form.setFieldsValue({
      ...r,
      signed_date: r.signed_date ? dayjs(r.signed_date) : null,
      expire_date: r.expire_date ? dayjs(r.expire_date) : null,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const data = {
        ...values,
        signed_date: values.signed_date ? dayjs(values.signed_date as string).format("YYYY-MM-DDTHH:mm:ss") : null,
        expire_date: values.expire_date ? dayjs(values.expire_date as string).format("YYYY-MM-DDTHH:mm:ss") : null,
      };
      if (editingId) { await updateContract(editingId, data); message.success("更新成功"); }
      else { await createContract(data); message.success("创建成功"); }
      form.resetFields(); setModalOpen(false); fetch(1);
    } catch { message.error("操作失败"); }
  };

  const handleDelete = async (id: number) => {
    try { await deleteContract(id); message.success("已删除"); fetch(page); } catch { message.error("删除失败"); }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "合同号", dataIndex: "contract_no", width: 120 },
    { title: "标题", dataIndex: "title", width: 200, ellipsis: true },
    { title: "客户ID", dataIndex: "customer_id", width: 80 },
    { title: "金额", dataIndex: "amount", width: 100, render: (v: number) => `¥${v.toFixed(2)}` },
    { title: "签订日期", dataIndex: "signed_date", width: 120 },
    { title: "到期日期", dataIndex: "expire_date", width: 120 },
    { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag> },
    {
      title: "操作", width: 150, render: (_: unknown, r: Contract) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/sales/contracts/${r.id}`)} />
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
        <Input placeholder="客户ID" style={{ width: 120 }} value={filters.customer_id} onChange={e => setFilters(f => ({ ...f, customer_id: e.target.value }))} />
        <Select placeholder="状态" allowClear style={{ width: 100 }} onChange={v => setFilters(f => ({ ...f, status: v || "" }))}>
          <Select.Option value="draft">草稿</Select.Option>
          <Select.Option value="active">生效中</Select.Option>
          <Select.Option value="expired">已过期</Select.Option>
          <Select.Option value="terminated">已终止</Select.Option>
        </Select>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增合同</Button>
      </Space>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />

      <Modal title={editingId ? "编辑合同" : "新增合同"} open={modalOpen} onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()} width={500}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="title" label="合同标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={customers.map(c => ({ label: `${c.name} (ID:${c.id})`, value: c.id }))} />
          </Form.Item>
          <Form.Item name="sales_order_id" label="关联订单">
            <Select allowClear showSearch optionFilterProp="label" options={orders.map(o => ({ label: `${o.order_no} (ID:${o.id})`, value: o.id }))} />
          </Form.Item>
          <Form.Item name="amount" label="金额" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="signed_date" label="签订日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="expire_date" label="到期日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={[{ label: "草稿", value: "draft" }, { label: "生效中", value: "active" }, { label: "已过期", value: "expired" }, { label: "已终止", value: "terminated" }]} />
          </Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
