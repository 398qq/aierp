import { useEffect, useRef, useState } from "react";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select, Popconfirm, Result } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, ExportOutlined, ImportOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { getQuotations, createQuotation, updateQuotation, deleteQuotation, getCustomers, batchDeleteQuotations, exportQuotations, importQuotations } from "../../api";
import type { Quotation, Customer } from "../../types";

const statusColors: Record<string, string> = {
  draft: "default", sent: "blue", approved: "green", rejected: "red", expired: "orange",
};

export default function QuotationList() {
  const [data, setData] = useState<Quotation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [filters, setFilters] = useState({ customer_id: "", status: "" });
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [error, setError] = useState(false);

  const fetch = async (p = page) => {
    setLoading(true);
    setError(false);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (filters.customer_id) params.customer_id = Number(filters.customer_id);
      if (filters.status) params.status = filters.status;
      const resp = await getQuotations(params);
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch {
      setError(true);
      message.error("加载报价单失败");
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

  const openEdit = async (record: Quotation) => {
    setEditingId(record.id); loadCustomers(); form.setFieldsValue(record); setModalOpen(true);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      if (editingId) { await updateQuotation(editingId, values); message.success("更新成功"); }
      else { await createQuotation(values); message.success("创建成功"); }
      form.resetFields(); setModalOpen(false); fetch(1);
    } catch { message.error("操作失败"); }
  };

  const handleDelete = async (id: number) => {
    try { await deleteQuotation(id); message.success("已删除"); fetch(page); } catch { message.error("删除失败"); }
  };

  const handleBatchDelete = async () => {
    try {
      await batchDeleteQuotations(selectedRowKeys as number[]);
      message.success(`已批量删除 ${selectedRowKeys.length} 条`);
      setSelectedRowKeys([]);
      fetch(1);
    } catch { message.error("批量删除失败"); }
  };

  const handleExport = async () => {
    try {
      const params: Record<string, unknown> = {};
      if (filters.customer_id) params.customer_id = Number(filters.customer_id);
      if (filters.status) params.status = filters.status;
      const resp = await exportQuotations(params);
      const url = window.URL.createObjectURL(new Blob([resp.data as BlobPart]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "quotations.xlsx";
      a.click();
      window.URL.revokeObjectURL(url);
      message.success("导出成功");
    } catch { message.error("导出失败"); }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const resp = await importQuotations(file);
      message.success(`导入成功: ${resp.data.data.imported} 条`);
      fetch(1);
    } catch { message.error("导入失败"); }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
  };

  const columns = [
    { title: "报价单号", dataIndex: "quotation_no", width: 150 },
    { title: "客户ID", dataIndex: "customer_id", width: 80 },
    { title: "状态", dataIndex: "status", width: 100, render: (v: string) => <Tag color={statusColors[v] || "default"}>{v}</Tag> },
    { title: "金额", dataIndex: "total_amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
    { title: "有效期至", dataIndex: "valid_until", width: 120 },
    { title: "创建时间", dataIndex: "created_at", width: 180 },
    {
      title: "操作", width: 180, render: (_: unknown, record: Quotation) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/sales/quotations/${record.id}`)}>详情</Button>
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
        <h3>报价单</h3>
        <Space>
          <Input placeholder="客户ID" value={filters.customer_id} onChange={(e) => setFilters({ ...filters, customer_id: e.target.value })} style={{ width: 120 }} />
          <Select placeholder="状态" value={filters.status || undefined} onChange={(v) => setFilters({ ...filters, status: v || "" })} allowClear style={{ width: 120 }}
            options={Object.keys(statusColors).map((k) => ({ value: k, label: k }))} />
          <Button icon={<ExportOutlined />} onClick={handleExport}>导出</Button>
          <Button icon={<ImportOutlined />} onClick={() => fileInputRef.current?.click()}>导入</Button>
          <input ref={fileInputRef} type="file" accept=".xlsx" style={{ display: "none" }} onChange={handleImport} />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建报价单</Button>
        </Space>
      </Space>

      {selectedRowKeys.length > 0 && (
        <Space style={{ marginBottom: 8 }}>
          <span>已选 {selectedRowKeys.length} 项</span>
          <Popconfirm title={`确定批量删除 ${selectedRowKeys.length} 条?`} onConfirm={handleBatchDelete}>
            <Button danger size="small">批量删除</Button>
          </Popconfirm>
        </Space>
      )}

      {error ? (
        <Result status="warning" title="加载失败" subTitle="无法加载报价单数据" extra={<Button onClick={() => fetch()}>重试</Button>} />
      ) : (
        <Table rowKey="id" rowSelection={rowSelection} columns={columns} dataSource={data} loading={loading}
          locale={{ emptyText: "暂无报价单" }}
          pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t: number) => `共 ${t} 条` }} />
      )}
      <Modal title={editingId ? "编辑报价单" : "新建报价单"} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="quotation_no" label="报价单号"><Input /></Form.Item>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <Select showSearch allowClear placeholder="选择客户" onSearch={loadCustomers} filterOption={false}>
              {customers.map((c) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select>{Object.keys(statusColors).map((k) => <Select.Option key={k} value={k}>{k}</Select.Option>)}</Select>
          </Form.Item>
          <Form.Item name="valid_until" label="有效期至"><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
