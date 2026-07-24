import { useState, useRef } from "react";
import { Button, Space, Select, Input, message, Popconfirm, Card, Modal, Checkbox } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType } from "@ant-design/pro-components";
import { StatusTag, type StatusTone } from "../../../ui";
import { PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { getUsers, deleteUser, getApiErrorMessage } from "../../../api";
import client from "../../../api/client";
import UserForm from "./UserForm";

const ROLE_OPTIONS = [
  { label: "管理员", value: "admin" },
  { label: "销售", value: "sales" },
  { label: "采购", value: "purchase" },
  { label: "仓库", value: "warehouse" },
  { label: "财务", value: "finance" },
];

const roleColor: Record<string, StatusTone> = {
  admin: "danger", sales: "info", purchase: "success", warehouse: "warning", finance: "info",
};

const roleLabel: Record<string, string> = {
  admin: "管理员", sales: "销售", purchase: "采购", warehouse: "仓库", finance: "财务",
};

interface UserItem {
  id: number; username: string; role: string; created_at: string; is_active: boolean;
}

interface RbacRole { id: number; name: string; description: string; }

export default function UserList() {
  const actionRef = useRef<ActionType>(null);
  const [search, setSearch] = useState("");
  const [filterRole, setFilterRole] = useState<string | undefined>();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<UserItem | null>(null);

  // RBAC role assignment
  const [roleModalOpen, setRoleModalOpen] = useState(false);
  const [roleUser, setRoleUser] = useState<UserItem | null>(null);
  const [allRoles, setAllRoles] = useState<RbacRole[]>([]);
  const [assignedRoleIds, setAssignedRoleIds] = useState<number[]>([]);
  const [roleSaving, setRoleSaving] = useState(false);

  const handleSearch = () => { actionRef.current?.reload(); };

  const openCreate = () => { setEditing(null); setFormOpen(true); };
  const openEdit = (u: UserItem) => { setEditing(u); setFormOpen(true); };

  const handleDelete = async (id: number) => {
    try { await deleteUser(id); message.success("删除成功"); actionRef.current?.reload(); } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
  };

  const onFormSuccess = () => { setFormOpen(false); actionRef.current?.reload(); };

  const openRoleAssign = async (u: UserItem) => {
    setRoleUser(u);
    setRoleModalOpen(true);
    try {
      const [rolesResp, userRolesResp] = await Promise.all([
        client.get("/permissions/roles"),
        client.get(`/permissions/users/${u.id}/roles`),
      ]);
      setAllRoles(rolesResp.data.data || []);
      setAssignedRoleIds(userRolesResp.data.data?.role_ids || []);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载角色失败")); }
  };

  const saveRoleAssign = async () => {
    if (!roleUser) return;
    setRoleSaving(true);
    try {
      await client.put(`/permissions/users/${roleUser.id}/roles`, { role_ids: assignedRoleIds });
      message.success("角色分配成功");
      setRoleModalOpen(false);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "保存失败")); }
    finally { setRoleSaving(false); }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "用户名", dataIndex: "username", width: 120 },
    {
      title: "角色", dataIndex: "role", width: 80,
      render: (v: string) => <StatusTag status={roleLabel[v] || v} tone={roleColor[v] || "neutral"} />,
    },
    {
      title: "状态", dataIndex: "is_active", width: 60,
      render: (v: boolean) => <StatusTag status={v ? "启用" : "禁用"} tone={v ? "success" : "danger"} />,
    },
    {
      title: "创建时间", dataIndex: "created_at", width: 100,
      render: (v: string) => v?.slice(0, 10) || "-",
    },
    {
      title: "操作", key: "action", width: 200,
      render: (_: unknown, r: UserItem) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Button size="small" icon={<SafetyCertificateOutlined />} onClick={() => openRoleAssign(r)}>角色</Button>
          <Popconfirm title="确认删除该用户？" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="用户管理"
        extra={
          <Space wrap>
            <Input.Search placeholder="搜索用户名" allowClear value={search}
              onChange={(e) => setSearch(e.target.value)} onSearch={handleSearch} style={{ width: 160 }} />
            <Select placeholder="角色筛选" allowClear style={{ width: 100 }} value={filterRole}
              onChange={(v) => { setFilterRole(v); actionRef.current?.reload(); }} options={ROLE_OPTIONS} />
            <Button icon={<ReloadOutlined />} onClick={() => actionRef.current?.reload()}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增用户</Button>
          </Space>
        }
      >
        <ProTable rowKey="id" actionRef={actionRef} search={false} options={{ reload: true }}
          columns={columns as any} size="small" scroll={{ x: 700 }}
          request={async (params) => {
            const queryParams: Record<string, unknown> = { page: params.current, page_size: params.pageSize };
            if (search) queryParams.q = search;
            if (filterRole) queryParams.role = filterRole;
            const resp = await getUsers(queryParams);
            const d = resp.data.data;
            return { data: (d.list || []) as unknown as UserItem[], success: true, total: d.total || 0 };
          }} />
      </Card>

      <UserForm open={formOpen} editing={editing} onClose={() => setFormOpen(false)} onSuccess={onFormSuccess} />

      <Modal title={`分配角色 — ${roleUser?.username || ""}`} open={roleModalOpen}
        onOk={saveRoleAssign} onCancel={() => setRoleModalOpen(false)} confirmLoading={roleSaving}>
        <Checkbox.Group value={assignedRoleIds} onChange={(v) => setAssignedRoleIds(v as number[])}>
          <Space direction="vertical">
            {allRoles.map(r => (
              <Checkbox key={r.id} value={r.id}>
                <strong>{r.name}</strong> — {r.description || ""}
              </Checkbox>
            ))}
          </Space>
        </Checkbox.Group>
      </Modal>
    </div>
  );
}
