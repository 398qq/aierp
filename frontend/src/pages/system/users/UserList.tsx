import { useEffect, useState } from "react";
import { Table, Button, Space, Tag, Select, Input, message, Popconfirm, Card, Row, Col } from "antd";
import { PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getUsers, deleteUser } from "../../../api";
import UserForm from "./UserForm";

const ROLE_OPTIONS = [
  { label: "管理员", value: "admin" },
  { label: "销售", value: "sales" },
  { label: "采购", value: "purchase" },
  { label: "仓库", value: "warehouse" },
  { label: "财务", value: "finance" },
];

const roleColor: Record<string, string> = {
  admin: "red",
  sales: "blue",
  purchase: "green",
  warehouse: "orange",
  finance: "purple",
};

const roleLabel: Record<string, string> = {
  admin: "管理员",
  sales: "销售",
  purchase: "采购",
  warehouse: "仓库",
  finance: "财务",
};

interface UserItem {
  id: number;
  username: string;
  role: string;
  created_at: string;
  is_active: boolean;
}

export default function UserList() {
  const [data, setData] = useState<UserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState("");
  const [filterRole, setFilterRole] = useState<string | undefined>();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<UserItem | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (search) params.q = search;
      if (filterRole) params.role = filterRole;
      const resp = await getUsers(params);
      const d = resp.data.data;
      setData((d.list || []) as unknown as UserItem[]);
      setTotal(d.total || 0);
    } catch {
      message.error("加载用户失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, pageSize, filterRole]);

  const handleSearch = () => { setPage(1); load(); };

  const openCreate = () => { setEditing(null); setFormOpen(true); };
  const openEdit = (u: UserItem) => { setEditing(u); setFormOpen(true); };

  const handleDelete = async (id: number) => {
    try {
      await deleteUser(id);
      message.success("删除成功");
      load();
    } catch { message.error("删除失败"); }
  };

  const onFormSuccess = () => { setFormOpen(false); load(); };

  const columns: ColumnsType<UserItem> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "用户名", dataIndex: "username", width: 150 },
    {
      title: "角色",
      dataIndex: "role",
      width: 100,
      render: (v: string) => (
        <Tag color={roleColor[v] || "default"}>{roleLabel[v] || v}</Tag>
      ),
    },
    {
      title: "状态",
      dataIndex: "is_active",
      width: 80,
      render: (v: boolean) => (
        <Tag color={v ? "green" : "red"}>{v ? "启用" : "禁用"}</Tag>
      ),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 120,
      render: (v: string) => v?.slice(0, 10) || "-",
    },
    {
      title: "操作",
      key: "action",
      width: 140,
      render: (_: unknown, r: UserItem) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除该用户？" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
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
            <Input.Search
              placeholder="搜索用户名"
              allowClear
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onSearch={handleSearch}
              style={{ width: 160 }}
            />
            <Select
              placeholder="角色筛选"
              allowClear
              style={{ width: 100 }}
              value={filterRole}
              onChange={(v) => { setFilterRole(v); setPage(1); }}
              options={ROLE_OPTIONS}
            />
            <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增用户</Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          loading={loading}
          dataSource={data}
          columns={columns}
          size="small"
          pagination={{
            current: page,
            total,
            pageSize,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
            showTotal: (t) => `共 ${t} 条`,
          }}
          scroll={{ x: 700 }}
        />
      </Card>

      <UserForm
        open={formOpen}
        editing={editing}
        onClose={() => setFormOpen(false)}
        onSuccess={onFormSuccess}
      />
    </div>
  );
}
