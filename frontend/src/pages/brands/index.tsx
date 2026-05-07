import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Input, Space, message, Card, Modal, Form, Tag, Popconfirm, Typography } from "antd";
import { PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, ImportOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getBrands, createBrand, updateBrand, deleteBrand, importBrandFromText } from "../../api";
import type { Brand } from "../../types";

const { Text } = Typography;

export default function BrandList() {
  const [data, setData] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Brand | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const [importLoading, setImportLoading] = useState(false);
  const navigate = useNavigate();

  const fetch = async (q = search) => {
    setLoading(true);
    try {
      const resp = await getBrands(q ? { q } : undefined);
      setData(resp.data.data as Brand[]);
    } catch { message.error("加载品牌失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (b: Brand) => {
    setEditing(b);
    form.setFieldsValue(b);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      if (editing) {
        await updateBrand(editing.id, form.getFieldsValue());
        message.success("更新成功");
      } else {
        await createBrand(form.getFieldsValue());
        message.success("创建成功");
      }
      setModalOpen(false);
      fetch();
    } catch { message.error("操作失败"); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteBrand(id);
      message.success("删除成功");
      fetch();
    } catch { message.error("删除失败"); }
  };

  const handleImport = async () => {
    setImportLoading(true);
    try {
      const resp = await importBrandFromText(importText, true);
      const data = resp.data.data as unknown as Record<string, unknown>;
      if (data.created_id) {
        message.success(`已创建品牌: ${data.name}`);
        navigate(`/brands/${data.created_id}`);
      } else {
        message.success(`已解析: ${data.name}`);
      }
      setImportOpen(false);
      setImportText("");
    } catch { message.error("导入失败"); }
    finally { setImportLoading(false); }
  };

  const columns: ColumnsType<Brand> = [
    { title: "ID", dataIndex: "id", width: 60 },
    {
      title: "名称", dataIndex: "name", width: 150,
      render: (v, r) => <a onClick={() => navigate(`/brands/${r.id}`)}>{v}</a>,
    },
    { title: "中文名", dataIndex: "name_cn", width: 120 },
    {
      title: "分类", dataIndex: "category", width: 100,
      render: (v) => v ? <Tag color="blue">{v}</Tag> : null,
    },
    { title: "官网", dataIndex: "website", width: 200, ellipsis: true,
      render: (v) => v ? <a href={v} target="_blank" rel="noopener noreferrer">{v}</a> : "-",
    },
    { title: "备注", dataIndex: "notes", width: 150, ellipsis: true },
    {
      title: "创建时间", dataIndex: "created_at", width: 100,
      render: (v: string) => v?.slice(0, 10) || "-",
    },
    {
      title: "更新时间", dataIndex: "updated_at", width: 100,
      render: (v: string | null) => v?.slice(0, 10) || "-",
    },
    {
      title: "操作", key: "action", width: 120,
      render: (_: unknown, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="品牌管理"
        extra={
          <Space>
            <Input.Search
              placeholder="搜索品牌" allowClear
              value={search} onChange={(e) => setSearch(e.target.value)}
              onSearch={(v) => fetch(v)} style={{ width: 200 }}
            />
            <Button icon={<ReloadOutlined />} onClick={() => fetch()}>刷新</Button>
            <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>AI 导入</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增</Button>
          </Space>
        }
      >
        <Table
          rowKey="id" columns={columns} dataSource={data}
          loading={loading} size="small" pagination={false}
        />
      </Card>

      <Modal
        title={editing ? "编辑品牌" : "新增品牌"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        okText={editing ? "保存" : "创建"}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入品牌名称" }]}>
            <Input placeholder="如 TI / STMicroelectronics" />
          </Form.Item>
          <Form.Item name="name_cn" label="中文名"><Input placeholder="如 德州仪器" /></Form.Item>
          <Form.Item name="category" label="分类"><Input placeholder="如 半导体/被动器件" /></Form.Item>
          <Form.Item name="website" label="官网"><Input placeholder="https://..." /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal
        title="AI 品牌导入"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        onOk={handleImport}
        confirmLoading={importLoading}
        okText="导入"
      >
        <Text>粘贴品牌描述文本（公司介绍、官网About、供应商目录等），AI 自动提取品牌信息：</Text>
        <Input.TextArea
          rows={6} value={importText}
          onChange={(e) => setImportText(e.target.value)}
          placeholder="例如：意法半导体 (STMicroelectronics) 是全球领先的半导体公司，专注于MCU、电源管理、传感器等产品线..."
          style={{ marginTop: 8 }}
        />
      </Modal>
    </div>
  );
}
