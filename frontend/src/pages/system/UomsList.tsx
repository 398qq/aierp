import { useEffect, useState } from "react";
import { Button, Space, Modal, Form, Input, Select, InputNumber, message, Card } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import client from "../../api/client";
import { getApiErrorMessage } from "../../api";

interface UomItem {
  code: string;
  name: string;
  uom_type: "count" | "package";
  category: string | null;
  description: string | null;
  sort_order: number;
}

const typeLabels: Record<string, string> = { count: "计数单位", package: "包装单位" };
const typeColors: Record<string, string> = { count: "blue", package: "green" };

export default function UomsList() {
  const [data, setData] = useState<UomItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<UomItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetch = async () => {
    setLoading(true);
    try {
      const resp = await client.get<{ code: number; data: UomItem[] }>("/uoms");
      setData(resp.data.data || []);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载计量单位失败")); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setDrawerOpen(true);
  };

  const openEdit = (item: UomItem) => {
    setEditing(item);
    form.setFieldsValue(item);
    setDrawerOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editing) {
        await client.put(`/uoms/${editing.code}`, values);
        message.success("更新成功");
      } else {
        await client.post("/uoms", values);
        message.success("创建成功");
      }
      setDrawerOpen(false);
      fetch();
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return;
      message.error(getApiErrorMessage(e, "操作失败"));
    } finally { setSubmitting(false); }
  };

  const handleDelete = (item: UomItem) => {
    Modal.confirm({
      title: `确认删除计量单位「${item.name} (${item.code})」？`,
      content: "删除后该单位将不再显示在选项中",
      okText: "删除",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          await client.delete(`/uoms/${item.code}`);
          message.success("已删除");
          fetch();
        } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
      },
    });
  };

  const columns: any = [
    { title: "编码", dataIndex: "code", width: 100 },
    { title: "名称", dataIndex: "name", width: 120 },
    {
      title: "类型", dataIndex: "uom_type", width: 100,
      render: (v: string) => typeLabels[v] || v,
    },
    { title: "分类", dataIndex: "category", width: 100, render: (v: string | null) => v || "-" },
    { title: "排序", dataIndex: "sort_order", width: 60 },
    {
      title: "操作", key: "op", width: 120,
      render: (_: unknown, r: UomItem) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <Card title="计量单位管理" extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增单位</Button>}>
      <ProTable
        rowKey="code"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={false}
        search={false}
        options={{ reload: true, density: true, setting: true }}
        size="middle"
      />

      <Modal
        title={editing ? "编辑计量单位" : "新增计量单位"}
        open={drawerOpen}
        onOk={handleSubmit}
        onCancel={() => setDrawerOpen(false)}
        confirmLoading={submitting}
        okText={editing ? "保存" : "创建"}
        cancelText="取消"
        width={480}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="code" label="编码" rules={[{ required: true, message: "请输入编码" }, { max: 20 }]}>
            <Input placeholder="如 PCS / REEL / BOX" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }, { max: 50 }]}>
            <Input placeholder="如 个 / 盘装 / 箱" />
          </Form.Item>
          <Form.Item name="uom_type" label="类型" rules={[{ required: true, message: "请选择类型" }]}>
            <Select>
              <Select.Option value="count">计数单位</Select.Option>
              <Select.Option value="package">包装单位</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Input placeholder="如 count / reel / box" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
