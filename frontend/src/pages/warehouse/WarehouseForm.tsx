import { Form, Input, Modal } from "antd";

interface WarehouseFormProps {
  open: boolean;
  loading?: boolean;
  initialValues?: { name: string; location?: string | null; description?: string | null };
  onCancel: () => void;
  onSubmit: (values: { name: string; location?: string; description?: string }) => void;
  mode: "create" | "edit";
}

export default function WarehouseForm({ open, loading, initialValues, onCancel, onSubmit, mode }: WarehouseFormProps) {
  const [form] = Form.useForm();

  const normalizedValues = initialValues ? {
    name: initialValues.name,
    location: initialValues.location ?? undefined,
    description: initialValues.description ?? undefined,
  } : undefined;

  return (
    <Modal
      title={mode === "create" ? "新增仓库" : "编辑仓库"}
      open={open}
      onCancel={onCancel}
      onOk={() => form.validateFields().then((vals) => onSubmit({
        name: vals.name,
        location: vals.location || undefined,
        description: vals.description || undefined,
      }))}
      confirmLoading={loading}
      okText={mode === "create" ? "创建" : "保存"}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={normalizedValues}
      >
        <Form.Item
          name="name"
          label="仓库名称"
          rules={[{ required: true, message: "请输入仓库名称" }]}
        >
          <Input placeholder="请输入仓库名称" maxLength={100} />
        </Form.Item>
        <Form.Item name="location" label="位置">
          <Input placeholder="请输入仓库位置" />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <Input.TextArea rows={3} placeholder="请输入仓库描述" />
        </Form.Item>
      </Form>
    </Modal>
  );
}
