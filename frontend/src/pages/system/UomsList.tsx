import { useState } from "react";
import { App, Button, Card, Form, Input, InputNumber, Modal, Select, Space } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { useApiMutation, useApiQuery, useQueryClient } from "@/lib/queries";
import { uomsApi } from "@/api/uoms";
import type { UomItem } from "@/api/uoms";

const typeLabels: Record<string, string> = { count: "计数单位", package: "包装单位" };

export default function UomsList() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<UomItem | null>(null);
  const [form] = Form.useForm();

  const query = useApiQuery<UomItem[]>(["uoms"], "/uoms");

  const createMut = useApiMutation("post", "/uoms", {
    invalidateKeys: [["uoms"]],
    onError: (err) => message.error(err.message || "创建失败"),
    onSuccess: () => {
      message.success("创建成功");
      setDrawerOpen(false);
    },
  });

  // TVariables must be the full body object so useApiMutation can pass it as the request body.
  // The URL fn extracts `code` from the object to build the path — TypeScript verifies compatibility.
  const updateMut = useApiMutation<unknown, { code: string; [key: string]: unknown }>(
    "put",
    (vars) => `/uoms/${vars.code}`,
    {
      invalidateKeys: [["uoms"]],
      onError: (err) => message.error(err.message || "更新失败"),
      onSuccess: () => {
        message.success("更新成功");
        setDrawerOpen(false);
      },
    },
  );

  const deleteMut = useApiMutation<unknown, { code: string }>(
    "delete",
    (vars) => `/uoms/${vars.code}`,
    {
      invalidateKeys: [["uoms"]],
      onError: (err) => message.error(err.message || "删除失败"),
      onSuccess: () => message.success("已删除"),
    },
  );

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
    const values = await form.validateFields();
    if (editing) {
      updateMut.mutate({ code: editing.code, ...values });
    } else {
      createMut.mutate(values);
    }
  };

  const handleDelete = (item: UomItem) => {
    Modal.confirm({
      title: `确认删除计量单位「${item.name} (${item.code})」？`,
      content: "删除后该单位将不再显示在选项中",
      okText: "删除",
      okType: "danger",
      cancelText: "取消",
      onOk: () => deleteMut.mutate({ code: item.code }),
    });
  };

  const handleSearch = () => {
    queryClient.invalidateQueries({ queryKey: ["uoms"] });
  };

  const columns: ProColumns<UomItem>[] = [
    { title: "编码", dataIndex: "code", width: 100 },
    { title: "名称", dataIndex: "name", width: 120 },
    {
      title: "类型",
      dataIndex: "uom_type",
      width: 100,
      render: (_, r) => typeLabels[r.uom_type] || r.uom_type,
    },
    {
      title: "分类",
      dataIndex: "category",
      width: 100,
      render: (v) => v || "-",
    },
    { title: "排序", dataIndex: "sort_order", width: 60 },
    {
      title: "操作",
      key: "op",
      width: 120,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>
            编辑
          </Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="计量单位管理"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新增单位
        </Button>
      }
    >
      <ProTable<UomItem>
        rowKey="code"
        columns={columns}
        dataSource={query.data || []}
        loading={query.isLoading || query.isFetching}
        pagination={false}
        search={false}
        options={{ reload: handleSearch, density: true, setting: true }}
        size="middle"
      />

      <Modal
        title={editing ? "编辑计量单位" : "新增计量单位"}
        open={drawerOpen}
        onOk={handleSubmit}
        onCancel={() => setDrawerOpen(false)}
        confirmLoading={createMut.isPending || updateMut.isPending}
        okText={editing ? "保存" : "创建"}
        cancelText="取消"
        width={480}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="code"
            label="编码"
            rules={[{ required: true, message: "请输入编码" }, { max: 20 }]}
          >
            <Input placeholder="如 PCS / REEL / BOX" disabled={!!editing} />
          </Form.Item>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: "请输入名称" }, { max: 50 }]}
          >
            <Input placeholder="如 个 / 盘装 / 箱" />
          </Form.Item>
          <Form.Item
            name="uom_type"
            label="类型"
            rules={[{ required: true, message: "请选择类型" }]}
          >
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
