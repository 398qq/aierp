import { useState } from "react";
import { Modal, Form, Input, Select, message } from "antd";
import { createUser, updateUser } from "../../../api";

const ROLE_OPTIONS = [
  { label: "管理员", value: "admin" },
  { label: "销售", value: "sales" },
  { label: "采购", value: "purchase" },
  { label: "仓库", value: "warehouse" },
  { label: "财务", value: "finance" },
];

interface UserItem {
  id: number;
  username: string;
  role: string;
  created_at: string;
  is_active: boolean;
}

interface Props {
  open: boolean;
  editing: UserItem | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function UserForm({ open, editing, onClose, onSuccess }: Props) {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editing) {
        await updateUser(editing.id, {
          role: values.role,
          ...(values.password ? { password: values.password } : {}),
        });
        message.success("更新成功");
      } else {
        await createUser(values);
        message.success("创建成功");
      }
      form.resetFields();
      onSuccess();
    } catch (e: unknown) {
      if (e instanceof Error && e.message) {
        message.error(e.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    form.resetFields();
    onClose();
  };

  return (
    <Modal
      title={editing ? "编辑用户" : "新增用户"}
      open={open}
      onCancel={handleClose}
      onOk={handleSubmit}
      confirmLoading={submitting}
      okText={editing ? "保存" : "创建"}
      width={480}
    >
      <Form form={form} layout="vertical" initialValues={editing ? { username: editing.username, role: editing.role } : undefined}>
        <Form.Item
          name="username"
          label="用户名"
          rules={[{ required: true, message: "请输入用户名" }]}
        >
          <Input placeholder="登录用户名" disabled={!!editing} />
        </Form.Item>

        <Form.Item
          name="password"
          label={editing ? "新密码（留空则不修改）" : "密码"}
          rules={editing ? [] : [{ required: true, message: "请输入密码" }]}
        >
          <Input.Password placeholder={editing ? "不修改请留空" : "请输入密码"} />
        </Form.Item>

        <Form.Item
          name="role"
          label="角色"
          rules={[{ required: true, message: "请选择角色" }]}
        >
          <Select placeholder="选择角色" options={ROLE_OPTIONS} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
