import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Input, Space, message, Card, Modal, Form, Select, Popconfirm, Tooltip, Row, Col } from "antd";
import { PlusOutlined, ReloadOutlined, DownloadOutlined, DeleteOutlined, EditOutlined, SearchOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getSuppliers, createSupplier, updateSupplier } from "../../api";
import client from "../../api/client";
import type { Supplier } from "../../types";

const SUPPLIER_TYPES = ["原厂", "代理商", "贸易商", "OEM", "代工厂", "其他"];

export default function SupplierList() {
  const [data, setData] = useState<Supplier[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [supplierType, setSupplierType] = useState<string | undefined>();

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState(false);

  // Edit modal
  const [editOpen, setEditOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<Supplier | null>(null);
  const [editForm] = Form.useForm();
  const [editing, setEditing] = useState(false);

  // Batch selection
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [batchDeleting, setBatchDeleting] = useState(false);

  const navigate = useNavigate();

  const fetch = async (p = page, q = search, st = supplierType) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (q) params.q = q;
      if (st) params.supplier_type = st;
      const resp = await getSuppliers(params);
      setData(resp.data.data.list as Supplier[]);
      setTotal(resp.data.data.total as number);
    } catch { message.error("加载供应商失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [page, supplierType]);

  const handleSearch = (v: string) => {
    setPage(1);
    fetch(1, v, supplierType);
  };

  const handleCreate = async () => {
    setCreating(true);
    try {
      await createSupplier(createForm.getFieldsValue());
      message.success("创建成功");
      setCreateOpen(false);
      createForm.resetFields();
      fetch(1);
    } catch { message.error("创建失败"); }
    finally { setCreating(false); }
  };

  const openEdit = (record: Supplier) => {
    setEditRecord(record);
    editForm.setFieldsValue(record);
    setEditOpen(true);
  };

  const handleEdit = async () => {
    if (!editRecord) return;
    setEditing(true);
    try {
      await updateSupplier(editRecord.id, editForm.getFieldsValue());
      message.success("更新成功");
      setEditOpen(false);
      editForm.resetFields();
      setEditRecord(null);
      fetch();
    } catch { message.error("更新失败"); }
    finally { setEditing(false); }
  };

  const handleDelete = async (id: number) => {
    try {
      await client.delete(`/suppliers/${id}`);
      message.success("已删除");
      fetch();
    } catch { message.error("删除失败"); }
  };

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) return;
    setBatchDeleting(true);
    let success = 0;
    let failed = 0;
    for (const id of selectedRowKeys) {
      try {
        await client.delete(`/suppliers/${id}`);
        success++;
      } catch {
        failed++;
      }
    }
    setBatchDeleting(false);
    setSelectedRowKeys([]);
    if (failed === 0) {
      message.success(`已删除 ${success} 条`);
    } else {
      message.warning(`删除 ${success} 条，失败 ${failed} 条`);
    }
    fetch();
  };

  const handleExport = () => {
    const headers = ["ID", "名称", "联系人", "电话", "邮箱", "地址", "产品线", "类型", "备注", "创建时间"];
    const rows = data.map((s) => [
      s.id, s.name, s.contact_person || "", s.phone || "",
      s.email || "", s.address || "", s.product_lines || "",
      s.supplier_type || "", s.notes || "", s.created_at?.slice(0, 10) || "",
    ]);
    const csv = [headers, ...rows]
      .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "suppliers.csv"; a.click();
    URL.revokeObjectURL(url);
    message.success("导出成功");
  };

  const columns: ColumnsType<Supplier> = [
    { title: "ID", dataIndex: "id", width: 60 },
    {
      title: "名称", dataIndex: "name", width: 200,
      render: (v, r) => <a onClick={() => navigate(`/suppliers/${r.id}`)}>{v}</a>,
    },
    { title: "联系人", dataIndex: "contact_person", width: 100 },
    { title: "电话", dataIndex: "phone", width: 120 },
    { title: "邮箱", dataIndex: "email", width: 180, ellipsis: true },
    { title: "地址", dataIndex: "address", width: 200, ellipsis: true },
    {
      title: "产品线", dataIndex: "product_lines", width: 200, ellipsis: true,
      render: (v) => v || "-",
    },
    {
      title: "类型", dataIndex: "supplier_type", width: 100,
      render: (v) => v || "-",
    },
    {
      title: "创建时间", dataIndex: "created_at", width: 100,
      render: (v: string) => v?.slice(0, 10) || "-",
    },
    {
      title: "更新时间", dataIndex: "updated_at", width: 100,
      render: (v: string | null) => v?.slice(0, 10) || "-",
    },
    {
      title: "操作", key: "actions", width: 150, render: (_: unknown, r: Supplier) => (
        <Space size={4}>
          <Tooltip title="编辑">
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          </Tooltip>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="供应商管理"
        extra={
          <Space>
            <Input.Search
              placeholder="搜索供应商名称/联系人/电话"
              allowClear
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onSearch={handleSearch}
              style={{ width: 260 }}
            />
            <Select
              allowClear
              placeholder="供应商类型"
              style={{ width: 120 }}
              value={supplierType}
              onChange={(v) => { setSupplierType(v); setPage(1); fetch(1, search, v); }}
              options={SUPPLIER_TYPES.map((t) => ({ value: t, label: t }))}
            />
            <Button icon={<ReloadOutlined />} onClick={() => fetch()}>刷新</Button>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
            {selectedRowKeys.length > 0 && (
              <Popconfirm
                title={`确定删除选中的 ${selectedRowKeys.length} 个供应商?`}
                onConfirm={handleBatchDelete}
              >
                <Button danger icon={<DeleteOutlined />} loading={batchDeleting}>
                  批量删除
                </Button>
              </Popconfirm>
            )}
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新增</Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="small"
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as number[]),
          }}
          pagination={{
            current: page, total, pageSize: 20,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p) => setPage(p),
          }}
        />
      </Card>

      {/* Create Modal */}
      <Modal
        title="新增供应商"
        open={createOpen}
        onCancel={() => { setCreateOpen(false); createForm.resetFields(); }}
        onOk={handleCreate}
        confirmLoading={creating}
        okText="创建"
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="供应商名称" />
          </Form.Item>
          <Form.Item name="contact_person" label="联系人"><Input /></Form.Item>
          <Form.Item name="phone" label="电话"><Input /></Form.Item>
          <Form.Item name="email" label="邮箱"><Input /></Form.Item>
          <Form.Item name="address" label="地址"><Input /></Form.Item>
          <Form.Item name="supplier_type" label="供应商类型">
            <Select placeholder="选择类型" options={SUPPLIER_TYPES.map((t) => ({ value: t, label: t }))} />
          </Form.Item>
          <Form.Item name="product_lines" label="产品线"><Input.TextArea rows={3} placeholder="描述供应商经营的产品线" /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        title="编辑供应商"
        open={editOpen}
        onCancel={() => { setEditOpen(false); editForm.resetFields(); setEditRecord(null); }}
        onOk={handleEdit}
        confirmLoading={editing}
        okText="保存"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="供应商名称" />
          </Form.Item>
          <Form.Item name="contact_person" label="联系人"><Input /></Form.Item>
          <Form.Item name="phone" label="电话"><Input /></Form.Item>
          <Form.Item name="email" label="邮箱"><Input /></Form.Item>
          <Form.Item name="address" label="地址"><Input /></Form.Item>
          <Form.Item name="supplier_type" label="供应商类型">
            <Select placeholder="选择类型" options={SUPPLIER_TYPES.map((t) => ({ value: t, label: t }))} />
          </Form.Item>
          <Form.Item name="product_lines" label="产品线"><Input.TextArea rows={3} placeholder="描述供应商经营的产品线" /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
