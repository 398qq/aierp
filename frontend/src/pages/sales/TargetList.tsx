import { useEffect, useState } from "react";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select, DatePicker, InputNumber, Popconfirm } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { getSalesTargets, createSalesTarget, updateSalesTarget, deleteSalesTarget } from "../../api";
import type { SalesTarget } from "../../types";

const typeLabels: Record<string, string> = { monthly: "月度", quarterly: "季度", yearly: "年度" };

export default function TargetList() {
  const [data, setData] = useState<SalesTarget[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [filters, setFilters] = useState({ target_type: "", status: "" });

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (filters.target_type) params.target_type = filters.target_type;
      if (filters.status) params.status = filters.status;
      const resp = await getSalesTargets(params);
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [page, filters]);

  const openCreate = () => { setEditingId(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (r: SalesTarget) => {
    setEditingId(r.id);
    form.setFieldsValue({ ...r, period_start: r.period_start ? dayjs(r.period_start) : null, period_end: r.period_end ? dayjs(r.period_end) : null });
    setModalOpen(true);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const data = {
        ...values,
        period_start: values.period_start ? dayjs(values.period_start as string).format("YYYY-MM-DDTHH:mm:ss") : null,
        period_end: values.period_end ? dayjs(values.period_end as string).format("YYYY-MM-DDTHH:mm:ss") : null,
      };
      if (editingId) { await updateSalesTarget(editingId, data); message.success("更新成功"); }
      else { await createSalesTarget(data); message.success("创建成功"); }
      form.resetFields(); setModalOpen(false); fetch(1);
    } catch { message.error("操作失败"); }
  };

  const handleDelete = async (id: number) => {
    try { await deleteSalesTarget(id); message.success("已删除"); fetch(page); } catch { message.error("删除失败"); }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "用户ID", dataIndex: "user_id", width: 80 },
    { title: "目标金额", dataIndex: "target_amount", width: 120, render: (v: number) => `¥${v.toFixed(2)}` },
    { title: "实际金额", dataIndex: "actual_amount", width: 120, render: (v: number) => `¥${v.toFixed(2)}` },
    { title: "完成率", key: "rate", width: 100, render: (_: unknown, r: SalesTarget) => {
      const rate = r.target_amount > 0 ? (r.actual_amount / r.target_amount * 100).toFixed(1) : 0;
      return <Tag color={Number(rate) >= 100 ? "green" : Number(rate) >= 60 ? "orange" : "red"}>{rate}%</Tag>;
    }},
    { title: "类型", dataIndex: "target_type", width: 80, render: (v: string) => typeLabels[v] || v },
    { title: "开始", dataIndex: "period_start", width: 120 },
    { title: "结束", dataIndex: "period_end", width: 120 },
    { title: "状态", dataIndex: "status", width: 80 },
    {
      title: "操作", width: 120, render: (_: unknown, r: SalesTarget) => (
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
        <Select placeholder="类型" allowClear style={{ width: 100 }} onChange={v => setFilters(f => ({ ...f, target_type: v || "" }))}>
          <Select.Option value="monthly">月度</Select.Option>
          <Select.Option value="quarterly">季度</Select.Option>
          <Select.Option value="yearly">年度</Select.Option>
        </Select>
        <Select placeholder="状态" allowClear style={{ width: 100 }} onChange={v => setFilters(f => ({ ...f, status: v || "" }))}>
          <Select.Option value="active">活跃</Select.Option>
          <Select.Option value="completed">已完成</Select.Option>
        </Select>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增目标</Button>
      </Space>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />

      <Modal title={editingId ? "编辑目标" : "新增目标"} open={modalOpen} onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()} width={500}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="user_id" label="用户ID" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="target_amount" label="目标金额" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="actual_amount" label="实际金额"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="target_type" label="目标类型">
            <Select options={Object.entries(typeLabels).map(([k, v]) => ({ label: v, value: k }))} />
          </Form.Item>
          <Form.Item name="period_start" label="开始日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="period_end" label="结束日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={[{ label: "活跃", value: "active" }, { label: "已完成", value: "completed" }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
