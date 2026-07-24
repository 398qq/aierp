import { useRef, useState } from "react";
import { Button, Space, message, Card, Popconfirm, Tooltip, Tag } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType } from "@ant-design/pro-components";
import { PlusOutlined, ReloadOutlined, DeleteOutlined, EditOutlined } from "@ant-design/icons";
import { getWarehouses, createWarehouse, updateWarehouse, deleteWarehouse, getApiErrorMessage } from "../../api";
import type { Warehouse } from "../../types";
import WarehouseForm from "./WarehouseForm";

interface WarehouseRecord extends Warehouse {
  created_at?: string;
}

export default function WarehouseList() {
  const actionRef = useRef<ActionType>(null);

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);

  // Edit modal
  const [editOpen, setEditOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<WarehouseRecord | null>(null);
  const [editLoading, setEditLoading] = useState(false);

  const handleCreate = async (values: { name: string; location?: string; description?: string }) => {
    setCreateLoading(true);
    try {
      await createWarehouse(values);
      message.success("创建成功");
      setCreateOpen(false);
      actionRef.current?.reload();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "创建失败")); } finally {
      setCreateLoading(false);
    }
  };

  const openEdit = (record: WarehouseRecord) => {
    setEditRecord(record);
    setEditOpen(true);
  };

  const handleEdit = async (values: { name: string; location?: string; description?: string }) => {
    if (!editRecord) return;
    setEditLoading(true);
    try {
      await updateWarehouse(editRecord.id, values);
      message.success("更新成功");
      setEditOpen(false);
      setEditRecord(null);
      actionRef.current?.reload();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "更新失败")); } finally {
      setEditLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteWarehouse(id);
      message.success("已删除");
      actionRef.current?.reload();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
  };

  const columns: any = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "名称", dataIndex: "name", width: 200 },
    { title: "位置", dataIndex: "location", width: 200, render: (v: string | null) => v || <Tag>未设置</Tag> },
    { title: "描述", dataIndex: "description", ellipsis: true, render: (v: string | null) => v || "-" },
    { title: "创建时间", dataIndex: "created_at", width: 100, render: (v: string) => v?.slice(0, 10) || "-" },
    {
      title: "操作", key: "actions", width: 120, render: (_: unknown, r: WarehouseRecord) => (
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
            <Button icon={<ReloadOutlined />} onClick={() => actionRef.current?.reload()}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新增仓库</Button>
          </Space>
        }
      >
        <ProTable
          actionRef={actionRef}
          rowKey="id"
          columns={columns}
          request={async (params) => {
            const resp = await getWarehouses({ page: params.current, page_size: params.pageSize });
            if (resp.data.code === 0) {
              return { data: resp.data.data.list as WarehouseRecord[], success: true, total: resp.data.data.total };
            }
            return { data: [], success: false, total: 0 };
          }}
          search={false}
          options={{ reload: true, density: true, setting: true }}
          size="small"
        />
      </Card>

      {/* Create Modal */}
      <WarehouseForm
        open={createOpen}
        loading={createLoading}
        onCancel={() => setCreateOpen(false)}
        onSubmit={handleCreate}
        mode="create"
      />

      {/* Edit Modal */}
      {editRecord && (
        <WarehouseForm
          open={editOpen}
          loading={editLoading}
          initialValues={editRecord}
          onCancel={() => { setEditOpen(false); setEditRecord(null); }}
          onSubmit={handleEdit}
          mode="edit"
        />
      )}
    </div>
  );
}
