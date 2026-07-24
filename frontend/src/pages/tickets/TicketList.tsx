import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Space, Select, message, Popconfirm } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { getTickets, deleteTicket, getApiErrorMessage } from "../../api";
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
  const actionRef = useRef<ActionType>(null);
  const [status, setStatus] = useState<string | undefined>();
  const [priority, setPriority] = useState<string | undefined>();
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    actionRef.current?.reload();
  }, [status, priority]);

  const handleDelete = async (id: number) => {
    try {
      await deleteTicket(id);
      message.success("已删除");
      actionRef.current?.reload();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
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

      <ProTable
        actionRef={actionRef}
        rowKey="id"
        rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
        request={async (params) => {
          const p: Record<string, unknown> = { page: params.current, page_size: params.pageSize };
          if (status) p.status = status;
          if (priority) p.priority = priority;
          const resp = await getTickets(p);
          return { data: resp.data.data.list || [], success: true, total: resp.data.data.total || 0 };
        }}
        search={false}
        options={{ reload: true, density: true, setting: true }}
        columns={[
          { title: "工单号", dataIndex: "ticket_no", width: 140, render: (v: string | null, r: Ticket) => <a onClick={() => navigate(`/tickets/${r.id}`)}>{v || `#${r.id}`}</a> },
          { title: "标题", dataIndex: "title", ellipsis: true, width: 200 },
          { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <StatusTag status={v} color={STATUS_MAP[v]?.color} label={STATUS_MAP[v]?.label} /> },
          { title: "优先级", dataIndex: "priority", width: 60, render: (v: string) => <StatusTag status={v} color={PRIORITY_MAP[v]?.color} label={PRIORITY_MAP[v]?.label} /> },
          { title: "分类", dataIndex: "category", width: 80, render: (v: string | null) => v || "-" },
          { title: "SLA", dataIndex: "sla_deadline", width: 110, render: (v: string | null) => v ? <span style={{ color: new Date(v) < new Date() ? "#ff4d4f" : "#52c41a", fontSize: 12 }}>{v.slice(0, 10)}</span> : "-" },
          { title: "根因", dataIndex: "root_cause", width: 120, ellipsis: true, render: (v: string | null) => v || "-" },
          { title: "处理人", dataIndex: "assigned_to", width: 80, render: (v: string | null) => v || "-" },
          { title: "创建时间", dataIndex: "created_at", width: 130, render: (v: string | null) => v ? v.slice(0, 19).replace("T", " ") : "-" },
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
        ] as any}
      />
    </div>
  );
}
