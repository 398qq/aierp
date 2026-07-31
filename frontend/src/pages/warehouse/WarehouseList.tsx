import { useState } from "react";
import { App, Button, Card, Popconfirm, Space, Tag, Tooltip } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { getApiErrorMessage } from "../../api";
import { useApiMutation, useApiQuery, useQueryClient } from "@/lib/queries";
import type { Warehouse } from "@/types";
import WarehouseForm from "./WarehouseForm";

interface WarehouseRecord extends Warehouse {
  created_at?: string;
}

export default function WarehouseList() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const query = useApiQuery<{ list: WarehouseRecord[]; total: number }>(
    ["warehouses"],
    "/warehouses",
    undefined,
    { staleTime: 30 * 1000 },
  );

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);

  // Edit modal
  const [editOpen, setEditOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<WarehouseRecord | null>(null);
  const [editLoading, setEditLoading] = useState(false);

  const createMut = useApiMutation<
    unknown,
    { name: string; location?: string; description?: string }
  >("post", "/warehouses", {
    invalidateKeys: [["warehouses"]],
    onSuccess: () => {
      message.success("创建成功");
      setCreateOpen(false);
    },
    onError: (e) => message.error(getApiErrorMessage(e, "创建失败")),
  });

  const updateMut = useApiMutation<
    unknown,
    { id: number; name: string; location?: string; description?: string }
  >("put", (v) => `/warehouses/${v.id}`, {
    invalidateKeys: [["warehouses"]],
    onSuccess: () => {
      message.success("更新成功");
      setEditOpen(false);
      setEditRecord(null);
    },
    onError: (e) => message.error(getApiErrorMessage(e, "更新失败")),
  });

  const deleteMut = useApiMutation<unknown, number>("delete", (id) => `/warehouses/${id}`, {
    invalidateKeys: [["warehouses"]],
    onSuccess: () => message.success("已删除"),
    onError: (e) => message.error(getApiErrorMessage(e, "删除失败")),
  });

  const handleCreate = (values: { name: string; location?: string; description?: string }) => {
    setCreateLoading(true);
    createMut.mutate(values, { onSettled: () => setCreateLoading(false) });
  };

  const openEdit = (record: WarehouseRecord) => {
    setEditRecord(record);
    setEditOpen(true);
  };

  const handleEdit = (values: { name: string; location?: string; description?: string }) => {
    if (!editRecord) return;
    setEditLoading(true);
    updateMut.mutate({ id: editRecord.id, ...values }, { onSettled: () => setEditLoading(false) });
  };

  const handleDelete = (id: number) => {
    deleteMut.mutate(id);
  };

  const handleSearch = () => {
    queryClient.invalidateQueries({ queryKey: ["warehouses"] });
  };

  const columns: ProColumns<WarehouseRecord>[] = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "名称", dataIndex: "name", width: 200 },
    {
      title: "位置",
      dataIndex: "location",
      width: 200,
      render: (_, r) => r.location || <Tag>未设置</Tag>,
    },
    {
      title: "描述",
      dataIndex: "description",
      ellipsis: true,
      render: (_, r) => r.description || "-",
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 100,
      render: (_, r) => r.created_at?.slice(0, 10) || "-",
    },
    {
      title: "操作",
      key: "actions",
      width: 120,
      render: (_, r) => (
        <Space size={4}>
          <Tooltip title="编辑">
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          </Tooltip>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="仓库管理"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleSearch}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              新增仓库
            </Button>
          </Space>
        }
      >
        <ProTable<WarehouseRecord>
          rowKey="id"
          columns={columns}
          dataSource={query.data?.list || []}
          loading={query.isLoading || query.isFetching}
          search={false}
          options={{ reload: handleSearch, density: true, setting: true }}
          size="small"
          pagination={{
            total: query.data?.total || 0,
            showSizeChanger: true,
            onChange: () => query.refetch(),
          }}
        />
      </Card>

      <WarehouseForm
        open={createOpen}
        loading={createLoading}
        onCancel={() => setCreateOpen(false)}
        onSubmit={handleCreate}
        mode="create"
      />

      {editRecord && (
        <WarehouseForm
          open={editOpen}
          loading={editLoading}
          initialValues={editRecord}
          onCancel={() => {
            setEditOpen(false);
            setEditRecord(null);
          }}
          onSubmit={handleEdit}
          mode="edit"
        />
      )}
    </div>
  );
}
