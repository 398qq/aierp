import { useEffect, useState } from "react";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select, Popconfirm } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { getOpportunities, createOpportunity, updateOpportunity, deleteOpportunity, getCustomers } from "../../api";
import type { Opportunity, Customer } from "../../types";

const stageColors: Record<string, string> = {
  lead: "default", qualified: "blue", proposal: "orange", negotiation: "purple",
  won: "green", lost: "red",
};

export default function OpportunityList() {
  const [data, setData] = useState<Opportunity[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const [filters, setFilters] = useState({ customer_id: "", stage: "" });

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (filters.customer_id) params.customer_id = Number(filters.customer_id);
      if (filters.stage) params.stage = filters.stage;
      const resp = await getOpportunities(params);
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch {
      message.error("加载机会列表失败");
    } finally {
      setLoading(false);
    }
  };

  const loadCustomers = async (q?: string) => {
    try {
      const resp = await getCustomers({ page: 1, page_size: 100, q });
      setCustomers(resp.data.data.list || []);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetch(); }, [page, filters]);

  const openCreate = () => {
    setEditingId(null);
    form.resetFields();
    loadCustomers();
    setModalOpen(true);
  };

  const openEdit = async (record: Opportunity) => {
    setEditingId(record.id);
    loadCustomers();
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      if (editingId) {
        await updateOpportunity(editingId, values);
        message.success("更新成功");
      } else {
        await createOpportunity(values);
        message.success("创建成功");
      }
      form.resetFields();
      setModalOpen(false);
      fetch(1);
    } catch {
      message.error("操作失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteOpportunity(id);
      message.success("已删除");
      fetch(page);
    } catch {
      message.error("删除失败");
    }
  };

  const columns = [
    { title: "名称", dataIndex: "name", width: 200 },
    { title: "客户ID", dataIndex: "customer_id", width: 80 },
    { title: "阶段", dataIndex: "stage", width: 100, render: (v: string) => <Tag color={stageColors[v] || "default"}>{v}</Tag> },
    { title: "金额", dataIndex: "amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
    { title: "概率", dataIndex: "probability", width: 80, render: (v: number) => `${v}%` },
    { title: "预计成交", dataIndex: "expected_close_date", width: 120 },
    { title: "创建时间", dataIndex: "created_at", width: 180 },
    {
      title: "操作", width: 180, render: (_: unknown, record: Opportunity) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/sales/opportunities/${record.id}`)}>详情</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: "space-between", width: "100%" }}>
        <h3>销售 Pipeline</h3>
        <Space>
          <Input placeholder="客户ID" value={filters.customer_id} onChange={(e) => setFilters({ ...filters, customer_id: e.target.value })} style={{ width: 120 }} />
          <Select placeholder="阶段" value={filters.stage || undefined} onChange={(v) => setFilters({ ...filters, stage: v || "" })} allowClear style={{ width: 120 }}
            options={Object.keys(stageColors).map((k) => ({ value: k, label: k }))} />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建机会</Button>
        </Space>
      </Space>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
      <Modal title={editingId ? "编辑机会" : "新建机会"} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <Select showSearch allowClear placeholder="选择客户" onSearch={loadCustomers} filterOption={false}>
              {customers.map((c) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="amount" label="金额"><Input type="number" /></Form.Item>
          <Form.Item name="stage" label="阶段">
            <Select>{Object.keys(stageColors).map((k) => <Select.Option key={k} value={k}>{k}</Select.Option>)}</Select>
          </Form.Item>
          <Form.Item name="probability" label="概率(%)"><Input type="number" min={0} max={100} /></Form.Item>
          <Form.Item name="expected_close_date" label="预计成交日期"><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
