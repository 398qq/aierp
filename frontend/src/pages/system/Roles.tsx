import { useEffect, useState } from "react";
import { Table, Button, Space, Modal, Form, Input, Tree, message, Popconfirm, Card, Tooltip } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";

import client from "../../api/client";
import { getApiErrorMessage } from "../../api";

interface Role {
  id: number; name: string; description: string;
  permission_ids: number[]; user_count: number;
}

interface PermGroup { resource: string; resource_label: string; actions: { id: number; action: string; name: string; description: string }[]; }

export default function Roles() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permGroups, setPermGroups] = useState<PermGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [saving, setSaving] = useState(false);
  const [checkedKeys, setCheckedKeys] = useState<number[]>([]);
  const [form] = Form.useForm();

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const [rResp, pResp] = await Promise.all([
        client.get("/permissions/roles"),
        client.get("/permissions"),
      ]);
      setRoles(rResp.data.data || []);
      const groups = pResp.data.data?.groups || {};
      const resourceLabels: Record<string, string> = {
        customers: "客户", products: "产品", sales: "销售",
        purchases: "采购", finance: "财务", inventory: "库存",
        reports: "报表", system: "系统",
      };
      const grouped: PermGroup[] = Object.entries(groups).map(([res, actions]) => ({
        resource: res,
        resource_label: resourceLabels[res] || res,
        actions: (actions as { id: number; action: string; name: string; description: string }[]),
      }));
      setPermGroups(grouped);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载失败")); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchRoles(); }, []);

  const openCreate = () => { setEditingRole(null); form.resetFields(); setCheckedKeys([]); setModalOpen(true); };
  const openEdit = (r: Role) => { setEditingRole(r); form.setFieldsValue(r); setCheckedKeys(r.permission_ids || []); setModalOpen(true); };

  const handleSave = async () => {
    const vals = await form.validateFields();
    setSaving(true);
    try {
      const body = { ...vals, permission_ids: checkedKeys };
      if (editingRole) {
        await client.put(`/permissions/roles/${editingRole.id}`, body);
      } else {
        await client.post("/permissions/roles", body);
      }
      message.success(editingRole ? "更新成功" : "创建成功");
      setModalOpen(false);
      fetchRoles();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "保存失败")); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    try { await client.delete(`/permissions/roles/${id}`); message.success("已删除"); fetchRoles(); } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
  };

  const treeData = permGroups.map((g) => ({
    key: g.resource,
    title: g.resource_label,
    children: g.actions.map((a) => ({
      key: a.id,
      title: (
        <Tooltip title={a.description || a.name} placement="right">
          <span>{a.name}</span>
        </Tooltip>
      ),
    })),
  }));

  const columns: ColumnsType<Role> = [
    { title: "角色名", dataIndex: "name", key: "name" },
    { title: "描述", dataIndex: "description", key: "description", ellipsis: true },
    { title: "用户数", dataIndex: "user_count", key: "uc", width: 80 },
    {
      title: "权限预览", key: "pc", width: 200,
      render: (_, r) => {
        const perms = r.permission_ids || [];
        const labels = perms.slice(0, 3).map((id) => {
          for (const g of permGroups) {
            const a = g.actions.find((ac) => ac.id === id);
            if (a) return a.name;
          }
          return null;
        }).filter(Boolean);
        const extra = perms.length > 3 ? ` +${perms.length - 3}` : "";
        return <span>{labels.join(", ")}{extra}</span>;
      },
    },
    {
      title: "操作", key: "op", width: 160,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          {r.name !== "admin" && (
            <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card title="角色权限管理" extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建角色</Button>}>
      <Table rowKey="id" columns={columns} dataSource={roles} loading={loading} pagination={false} />
      <Modal
        title={editingRole ? "编辑角色" : "新建角色"}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="角色名" rules={[{ required: true }]}>
            <Input placeholder="如: sales_manager" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="角色用途说明" />
          </Form.Item>
          <Form.Item label="权限">
            <Tree
              checkable
              treeData={treeData}
              checkedKeys={checkedKeys}
              onCheck={(keys) => setCheckedKeys(keys as number[])}
            />
          </Form.Item>
          <div style={{ fontSize: 12, color: "#888", marginTop: 4 }}>
            悬停权限名称可查看权限说明
          </div>
        </Form>
      </Modal>
    </Card>
  );
}
