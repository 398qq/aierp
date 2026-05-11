import { useEffect, useState } from "react";
import { Table, Button, Space, message, Card, Modal, Form, Input, Popconfirm, Tooltip, Tag } from "antd";
import { PlusOutlined, ReloadOutlined, DeleteOutlined, EditOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getWarehouses, createWarehouse, updateWarehouse, deleteWarehouse } from "../../api";
import type { Warehouse } from "../../types";
import WarehouseForm from "./WarehouseForm";

interface WarehouseRecord extends Warehouse {
  created_at?: string;
}

export default function WarehouseList() {
  const [data, setData] = useState<WarehouseRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);

  // Edit modal
  const [editOpen, setEditOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<WarehouseRecord | null>(null);
  const [editLoading, setEditLoading] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const resp = await getWarehouses();
      if (resp.data.code === 0) {
        setData(resp.data.data as WarehouseRecord[]);
        setTotal(resp.data.data.length);
      }
    } catch {
      message.error("加载仓库失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, [page]);

  const handleCreate = async (values: { name: string; location?: string; description?: string }) => {
    setCreateLoading(true);
    try {
      await createWarehouse(values);
      message.success("创建成功");
      setCreateOpen(false);
      fetch();
    } catch {
      message.error("创建失败");
    } finally {
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
      fetch();
    } catch {
      message.error("更新失败");
    } finally {
      setEditLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteWarehouse(id);
      message.success("已删除");
      fetch();
    } catch {
      message.error("删除失败");
    }
  };

  const columns: ColumnsType<WarehouseRecord> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "名称", dataIndex: "name", width: 200 },
    { title: "位置", dataIndex: "location", width: 200, render: (v) => v || <Tag>未设置</Tag> },
    { title: "描述", dataIndex: "description", ellipsis: true, render: (v) => v || "-" },
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
            <Button icon={<ReloadOutlined />} onClick={fetch}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新增仓库</Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="small"
          pagination={{
            current: page, total, pageSize: 20,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p) => setPage(p),
          }}
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
