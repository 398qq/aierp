import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { App, Button, Space, Select, Popconfirm } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { theme } from "antd";
import { StatusTag } from "../../ui";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { getApiErrorMessage } from "../../api";
import type { PageData, Ticket } from "@/types";
import { useApiQuery, useApiMutation, useQueryClient } from "@/lib/queries";

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
  const { message } = App.useApp();
  const { token } = theme.useToken();
  const [status, setStatus] = useState<string | undefined>();
  const [priority, setPriority] = useState<string | undefined>();
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const params: Record<string, unknown> = {};
  if (status) params.status = status;
  if (priority) params.priority = priority;

  const query = useApiQuery<PageData<Ticket>>(
    ["tickets", status ?? "", priority ?? ""],
    "/tickets",
    params,
    { staleTime: 30 * 1000 },
  );

  const deleteMut = useApiMutation("delete", (id: number) => `/tickets/${id}`, {
    invalidateKeys: [["tickets"]],
    onSuccess: () => message.success("已删除"),
    onError: (e) => message.error(getApiErrorMessage(e, "删除失败")),
  });

  const handleDelete = (id: number) => {
    deleteMut.mutate(id);
  };

  const handleSearch = () => {
    queryClient.invalidateQueries({ queryKey: ["tickets"] });
  };

  const columns: ProColumns<Ticket>[] = [
    {
      title: "工单号",
      dataIndex: "ticket_no",
      width: 140,
      render: (_, r) => (
        <a onClick={() => navigate(`/tickets/${r.id}`)}>{r.ticket_no || `#${r.id}`}</a>
      ),
    },
    { title: "标题", dataIndex: "title", ellipsis: true, width: 200 },
    {
      title: "状态",
      dataIndex: "status",
      width: 80,
      render: (_, r) => (
        <StatusTag
          status={r.status}
          color={STATUS_MAP[r.status]?.color}
          label={STATUS_MAP[r.status]?.label}
        />
      ),
    },
    {
      title: "优先级",
      dataIndex: "priority",
      width: 60,
      render: (_, r) => (
        <StatusTag
          status={r.priority}
          color={PRIORITY_MAP[r.priority]?.color}
          label={PRIORITY_MAP[r.priority]?.label}
        />
      ),
    },
    { title: "分类", dataIndex: "category", width: 80, render: (_, r) => r.category || "-" },
    {
      title: "SLA",
      dataIndex: "sla_deadline",
      width: 110,
      render: (_, r) =>
        r.sla_deadline ? (
          <span
            style={{
              color: new Date(r.sla_deadline) < new Date() ? token.colorError : token.colorSuccess,
              fontSize: 12,
            }}
          >
            {r.sla_deadline.slice(0, 10)}
          </span>
        ) : (
          "-"
        ),
    },
    {
      title: "根因",
      dataIndex: "root_cause",
      width: 120,
      ellipsis: true,
      render: (_, r) => r.root_cause || "-",
    },
    {
      title: "处理人",
      dataIndex: "assigned_to",
      width: 80,
      render: (_, r) => r.assigned_to || "-",
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 130,
      render: (_, r) => (r.created_at ? r.created_at.slice(0, 19).replace("T", " ") : "-"),
    },
    {
      title: "操作",
      width: 180,
      render: (_, r) => (
        <Space size="small">
          <Button size="small" onClick={() => navigate(`/tickets/${r.id}`)}>
            详情
          </Button>
          <Button size="small" onClick={() => navigate(`/tickets/${r.id}/edit`)}>
            编辑
          </Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/tickets/new")}>
          新建工单
        </Button>
        <Select
          placeholder="状态筛选"
          allowClear
          style={{ width: 120 }}
          value={status}
          onChange={setStatus}
          options={[
            { value: "open", label: "待处理" },
            { value: "in_progress", label: "处理中" },
            { value: "resolved", label: "已解决" },
            { value: "closed", label: "已关闭" },
          ]}
        />
        <Select
          placeholder="优先级筛选"
          allowClear
          style={{ width: 120 }}
          value={priority}
          onChange={setPriority}
          options={[
            { value: "low", label: "低" },
            { value: "medium", label: "中" },
            { value: "high", label: "高" },
          ]}
        />
      </Space>

      <ProTable<Ticket>
        rowKey="id"
        rowSelection={{
          selectedRowKeys: selected,
          onChange: (keys) => setSelected(keys as number[]),
        }}
        columns={columns}
        dataSource={query.data?.list || []}
        loading={query.isLoading || query.isFetching}
        search={false}
        options={{ reload: handleSearch, density: true, setting: true }}
        pagination={{
          total: query.data?.total || 0,
          showSizeChanger: true,
          onChange: () => query.refetch(),
        }}
      />
    </div>
  );
}
