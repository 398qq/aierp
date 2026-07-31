import { useState } from "react";
import { App, Button, Space, Card } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { CheckOutlined } from "@ant-design/icons";
import { markNotificationsRead, getApiErrorMessage } from "../../api";
import type { NotificationItem, PageData } from "@/types";
import { useApiQuery, useQueryClient } from "@/lib/queries";

const TYPE: Record<string, { color: string; label: string }> = {
  followup: { color: "blue", label: "跟进" },
  risk_alert: { color: "red", label: "风险" },
  overdue: { color: "orange", label: "逾期" },
  target_warning: { color: "gold", label: "目标" },
  contract_expiry: { color: "purple", label: "合同" },
  system: { color: "default", label: "系统" },
};

export default function NotificationList() {
  const { message } = App.useApp();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const queryClient = useQueryClient();

  const query = useApiQuery<PageData<NotificationItem>>(
    ["notifications", unreadOnly],
    "/notifications",
    unreadOnly ? { unread_only: true } : undefined,
    { staleTime: 30 * 1000 },
  );

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["notifications"] });

  const handleMarkAllRead = async () => {
    try {
      await markNotificationsRead({ all: true });
      message.success("全部已读");
      invalidate();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "操作失败"));
    }
  };

  const handleMarkRead = async (ids: number[]) => {
    try {
      await markNotificationsRead({ ids });
      invalidate();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "操作失败"));
    }
  };

  const columns: ProColumns<NotificationItem>[] = [
    {
      title: "类型",
      dataIndex: "type",
      width: 80,
      render: (_, r) => (
        <StatusTag tone={TYPE[r.type]?.color}>{TYPE[r.type]?.label || r.type}</StatusTag>
      ),
    },
    { title: "标题", dataIndex: "title", ellipsis: true },
    { title: "内容", dataIndex: "content", ellipsis: true, render: (_, r) => r.content || "-" },
    {
      title: "状态",
      dataIndex: "is_read",
      width: 80,
      render: (_, r) =>
        r.is_read ? <StatusTag>已读</StatusTag> : <StatusTag tone="info">未读</StatusTag>,
    },
    {
      title: "时间",
      dataIndex: "created_at",
      width: 160,
      render: (_, r) => new Date(r.created_at).toLocaleString(),
    },
    {
      title: "操作",
      width: 80,
      render: (_, r) => (
        <Space size="small">
          {!r.is_read && (
            <Button size="small" type="link" onClick={() => handleMarkRead([r.id])}>
              已读
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="通知中心"
      extra={
        <Space>
          <Button
            size="small"
            type={unreadOnly ? "primary" : "default"}
            onClick={() => setUnreadOnly(!unreadOnly)}
          >
            {unreadOnly ? "显示全部" : "仅未读"}
          </Button>
          <Button size="small" icon={<CheckOutlined />} onClick={handleMarkAllRead}>
            全部已读
          </Button>
        </Space>
      }
    >
      <ProTable<NotificationItem>
        rowKey="id"
        rowClassName={(r) => (r?.is_read ? "" : "ant-table-row-highlight")}
        columns={columns}
        dataSource={query.data?.list || []}
        loading={query.isLoading || query.isFetching}
        search={false}
        options={{ reload: () => query.refetch(), density: true, setting: true }}
        pagination={{
          total: query.data?.total || 0,
          showSizeChanger: true,
          onChange: () => query.refetch(),
        }}
      />
    </Card>
  );
}
