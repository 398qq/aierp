import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Select, message, Popconfirm } from "antd";
import { StatusTag } from "../../ui";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { getTickets, deleteTicket } from "../../api";
import type { Ticket } from "../../types";

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  open: { color: "blue", label: "待处理" },
  in_progress: { color: "orange", label: "处理中" },
  resolved: { color: "green", label: "已解决" },
  closed: { color: "default", label: "已关闭" },
};

const PRIORITY_MAP: Record<string, { color: string; label: string }> = {
  low: { color: "green", label: "低" },
  medium: { color: "orange", label: "中" },
  high: { color: "red", label: "高" },
};

export default function TicketList() {
  const [data, setData] = useState<Ticket[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [priority, setPriority] = useState<string | undefined>();
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      if (priority) params.priority = priority;
      const resp = await getTickets(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, status, priority]);

  const handleDelete = async (id: number) => {
    try {
      await deleteTicket(id);
      message.success("已删除");
      load();
    } catch { message.error("删除失败"); }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/tickets/new")}>新建工单</Button>
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "open", label: "待处理" }, { value: "in_progress", label: "处理中" },
          { value: "resolved", label: "已解决" }, { value: "closed", label: "已关闭" },
        ]} />
        <Select placeholder="优先级筛选" allowClear style={{ width: 120 }} value={priority} onChange={setPriority} options={[
          { value: "low", label: "低" }, { value: "medium", label: "中" }, { value: "high", label: "高" },
        ]} />
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={data}
        rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
        columns={[
          { title: "工单号", dataIndex: "ticket_no", width: 140, render: (v: string | null, r: Ticket) => <a onClick={() => navigate(`/tickets/${r.id}`)}>{v || `#${r.id}`}</a> },
          { title: "标题", dataIndex: "title", ellipsis: true },
          { title: "状态", dataIndex: "status", width: 90, render: (v: string) => <StatusTag status={v} color={STATUS_MAP[v]?.color} label={STATUS_MAP[v]?.label} /> },
          { title: "优先级", dataIndex: "priority", width: 70, render: (v: string) => <StatusTag status={v} color={PRIORITY_MAP[v]?.color} label={PRIORITY_MAP[v]?.label} /> },
          { title: "分类", dataIndex: "category", width: 100, render: (v: string | null) => v || "-" },
          { title: "处理人", dataIndex: "assigned_to", width: 100, render: (v: string | null) => v || "-" },
          { title: "创建时间", dataIndex: "created_at", width: 150, render: (v: string | null) => v ? v.slice(0, 19).replace("T", " ") : "-" },
          {
            title: "操作", width: 180,
            render: (_: unknown, r: Ticket) => (
              <Space size="small">
                <Button size="small" onClick={() => navigate(`/tickets/${r.id}`)}>详情</Button>
                <Button size="small" onClick={() => navigate(`/tickets/${r.id}/edit`)}>编辑</Button>
                <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
    </div>
  );
}
