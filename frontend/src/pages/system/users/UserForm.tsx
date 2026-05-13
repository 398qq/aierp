import { useState, useEffect } from "react";
import { Modal, Form, Input, Select, message } from "antd";
import { createUser, updateUser } from "../../../api";
import client from "../../../api/client";

interface Role {
  id: number;
  name: string;
  description: string;
}

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
  const [roles, setRoles] = useState<Role[]>([]);
  const [loadingRoles, setLoadingRoles] = useState(false);

  useEffect(() => {
    if (open) {
      setLoadingRoles(true);
      client
        .get<{ data: Role[] }>("/permissions/roles")
        .then((r) => setRoles(r.data.data || []))
        .catch(() => setRoles([]))
        .finally(() => setLoadingRoles(false));
    }
  }, [open]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editing) {
        await updateUser(editing.id, {
          role: values.role || "",
          ...(values.password ? { password: values.password } : {}),
          role_ids: values.role_ids ?? [],
        });
        message.success("更新成功");
      } else {
        await createUser({
          username: values.username,
          password: values.password,
          role: values.role || "",
          role_ids: values.role_ids ?? [],
        });
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

  const roleOptions = roles.map((r) => ({
    label: `${r.name}${r.description ? ` - ${r.description}` : ""}`,
    value: r.id,
  }));

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
      <Form
        form={form}
        layout="vertical"
        initialValues={editing ? { username: editing.username, role: editing.role } : undefined}
      >
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
          name="role_ids"
          label="角色"
          rules={[{ required: true, message: "请选择角色" }]}
        >
          <Select
            placeholder="选择角色"
            options={roleOptions}
            loading={loadingRoles}
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? "").toLowerCase().includes(input.toLowerCase())
            }
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
