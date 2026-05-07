import { useEffect, useState } from "react";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select, Popconfirm, Upload } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, UploadOutlined, DownloadOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { getDeliveryNotes, createDeliveryNote, updateDeliveryNote, deleteDeliveryNote, getCustomers, batchDeleteDeliveryNotes, exportDeliveryNotes, importDeliveryNotes } from "../../api";
import type { DeliveryNote, Customer } from "../../types";

const statusColors: Record<string, string> = {
  pending: "orange", shipped: "cyan", delivered: "green", signed: "blue", cancelled: "red",
};

export default function DeliveryNoteList() {
  const [data, setData] = useState<DeliveryNote[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const [filters, setFilters] = useState({ customer_id: "", status: "" });

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (filters.customer_id) params.customer_id = Number(filters.customer_id);
      if (filters.status) params.status = filters.status;
      const resp = await getDeliveryNotes(params);
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch {
      message.error("加载送货单失败");
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

  const openCreate = () => { setEditingId(null); form.resetFields(); loadCustomers(); setModalOpen(true); };

  const openEdit = async (record: DeliveryNote) => {
    setEditingId(record.id); loadCustomers(); form.setFieldsValue(record); setModalOpen(true);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      if (editingId) { await updateDeliveryNote(editingId, values); message.success("更新成功"); }
      else { await createDeliveryNote(values); message.success("创建成功"); }
      form.resetFields(); setModalOpen(false); fetch(1);
    } catch { message.error("操作失败"); }
  };

  const handleDelete = async (id: number) => {
    try { await deleteDeliveryNote(id); message.success("已删除"); fetch(page); } catch { message.error("删除失败"); }
  };

  const handleBatchDelete = async () => {
    try { await batchDeleteDeliveryNotes(selectedRowKeys); message.success(`已删除 ${selectedRowKeys.length} 条`); setSelectedRowKeys([]); fetch(1); } catch { message.error("批量删除失败"); }
  };

  const handleExport = async () => {
    try {
      const params: Record<string, unknown> = {};
      if (filters.customer_id) params.customer_id = Number(filters.customer_id);
      if (filters.status) params.status = filters.status;
      const resp = await exportDeliveryNotes(params);
      const url = URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url; a.download = "delivery_notes.xlsx"; a.click();
      URL.revokeObjectURL(url);
      message.success("导出成功");
    } catch { message.error("导出失败"); }
  };

  const handleImport = async (file: File) => {
    try {
      const resp = await importDeliveryNotes(file);
      message.success(`导入成功: ${(resp.data.data as { imported: number }).imported} 条`);
      fetch(1);
    } catch { message.error("导入失败，请检查文件格式"); }
    return false;
  };

  const columns = [
    { title: "送货单号", dataIndex: "note_no", width: 150 },
    { title: "销售订单ID", dataIndex: "sales_order_id", width: 100 },
    { title: "客户ID", dataIndex: "customer_id", width: 80 },
    { title: "状态", dataIndex: "status", width: 100, render: (v: string) => <Tag color={statusColors[v] || "default"}>{v}</Tag> },
    { title: "送货日期", dataIndex: "delivery_date", width: 120 },
    { title: "签收日期", dataIndex: "signed_at", width: 120 },
    { title: "创建时间", dataIndex: "created_at", width: 180 },
    {
      title: "操作", width: 180, render: (_: unknown, record: DeliveryNote) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/sales/delivery-notes/${record.id}`)}>详情</Button>
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
        <h3>送货单</h3>
        <Space>
          <Input placeholder="客户ID" value={filters.customer_id} onChange={(e) => setFilters({ ...filters, customer_id: e.target.value })} style={{ width: 120 }} />
          <Select placeholder="状态" value={filters.status || undefined} onChange={(v) => setFilters({ ...filters, status: v || "" })} allowClear style={{ width: 120 }}
            options={Object.keys(statusColors).map((k) => ({ value: k, label: k }))} />
          {selectedRowKeys.length > 0 && (
            <Popconfirm title={`确定删除 ${selectedRowKeys.length} 个送货单?`} onConfirm={handleBatchDelete}>
              <Button danger icon={<DeleteOutlined />}>批量删除</Button>
            </Popconfirm>
          )}
          <Upload accept=".xlsx" showUploadList={false} beforeUpload={handleImport}>
            <Button icon={<UploadOutlined />}>导入</Button>
          </Upload>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建送货单</Button>
        </Space>
      </Space>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading}
        rowSelection={{ selectedRowKeys, onChange: (keys) => setSelectedRowKeys(keys as number[]) }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }} />
      <Modal title={editingId ? "编辑送货单" : "新建送货单"} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="note_no" label="送货单号"><Input /></Form.Item>
          <Form.Item name="sales_order_id" label="销售订单ID" rules={[{ required: true }]}><Input type="number" /></Form.Item>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <Select showSearch allowClear placeholder="选择客户" onSearch={loadCustomers} filterOption={false}>
              {customers.map((c) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select>{Object.keys(statusColors).map((k) => <Select.Option key={k} value={k}>{k}</Select.Option>)}</Select>
          </Form.Item>
          <Form.Item name="delivery_date" label="送货日期"><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="signed_at" label="签收日期"><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
