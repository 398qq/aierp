import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Input, Space, message, Card, Modal, Form } from "antd";
import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getSuppliers, createSupplier } from "../../api";
import type { Supplier } from "../../types";

export default function SupplierList() {
  const [data, setData] = useState<Supplier[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [form] = Form.useForm();
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const fetch = async (p = page, q = search) => {
    setLoading(true);
    try {
      const resp = await getSuppliers({ page: p, page_size: 20, q: q || undefined });
      setData(resp.data.data.list as Supplier[]);
      setTotal(resp.data.data.total as number);
    } catch { message.error("加载供应商失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [page]);

  const handleCreate = async () => {
    setCreating(true);
    try {
      await createSupplier(form.getFieldsValue());
      message.success("创建成功");
      setCreateOpen(false);
      form.resetFields();
      fetch(1);
    } catch { message.error("创建失败"); }
    finally { setCreating(false); }
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
      title: "创建时间", dataIndex: "created_at", width: 100,
      render: (v: string) => v?.slice(0, 10) || "-",
    },
    {
      title: "更新时间", dataIndex: "updated_at", width: 100,
      render: (v: string | null) => v?.slice(0, 10) || "-",
    },
  ];

  return (
    <div>
      <Card
        title="供应商管理"
        extra={
          <Space>
            <Input.Search
              placeholder="搜索供应商" allowClear
              value={search} onChange={(e) => setSearch(e.target.value)}
              onSearch={(v) => { setPage(1); fetch(1, v); }}
              style={{ width: 200 }}
            />
            <Button icon={<ReloadOutlined />} onClick={() => fetch()}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新增</Button>
          </Space>
        }
      >
        <Table
          rowKey="id" columns={columns} dataSource={data}
          loading={loading} size="small"
          pagination={{
            current: page, total, pageSize: 20,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p) => setPage(p),
          }}
        />
      </Card>

      <Modal
        title="新增供应商" open={createOpen} onCancel={() => setCreateOpen(false)}
        onOk={handleCreate} confirmLoading={creating} okText="创建"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="供应商名称" />
          </Form.Item>
          <Form.Item name="contact_person" label="联系人"><Input /></Form.Item>
          <Form.Item name="phone" label="电话"><Input /></Form.Item>
          <Form.Item name="email" label="邮箱"><Input /></Form.Item>
          <Form.Item name="address" label="地址"><Input /></Form.Item>
          <Form.Item name="product_lines" label="产品线"><Input.TextArea rows={3} placeholder="描述供应商经营的产品线" /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
