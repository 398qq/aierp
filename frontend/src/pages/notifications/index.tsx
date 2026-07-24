import { useEffect, useRef, useState } from "react";
import { Button, Space, Tag, message, Card, Popconfirm } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { CheckOutlined, DeleteOutlined } from "@ant-design/icons";
import { getNotifications, markNotificationsRead, getApiErrorMessage } from "../../api";
import type { NotificationItem } from "../../types";

const TYPE: Record<string, { color: string; label: string }> = {
  followup: { color: "blue", label: "跟进" },
  risk_alert: { color: "red", label: "风险" },
  overdue: { color: "orange", label: "逾期" },
  target_warning: { color: "gold", label: "目标" },
  contract_expiry: { color: "purple", label: "合同" },
  system: { color: "default", label: "系统" },
};

export default function NotificationList() {
  const actionRef = useRef<ActionType>(null);
  const [unreadOnly, setUnreadOnly] = useState(false);

  useEffect(() => {
    actionRef.current?.reload();
  }, [unreadOnly]);

  const handleMarkAllRead = async () => {
    try {
      await markNotificationsRead({ all: true });
      message.success("全部已读");
      actionRef.current?.reload();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "操作失败")); }
  };

  const handleMarkRead = async (ids: number[]) => {
    try {
      await markNotificationsRead({ ids });
      actionRef.current?.reload();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "操作失败")); }
  };

  return (
    <Card
      title="通知中心"
      extra={
        <Space>
          <Button size="small" type={unreadOnly ? "primary" : "default"} onClick={() => { setUnreadOnly(!unreadOnly); }}>
            {unreadOnly ? "显示全部" : "仅未读"}
          </Button>
          <Button size="small" icon={<CheckOutlined />} onClick={handleMarkAllRead}>全部已读</Button>
        </Space>
      }
    >
      <ProTable
        actionRef={actionRef}
        rowKey="id"
        rowClassName={(r: NotificationItem) => r.is_read ? "" : "ant-table-row-highlight"}
        request={async (params) => {
          const p: Record<string, unknown> = { page: params.current, page_size: params.pageSize };
          if (unreadOnly) p.unread_only = true;
          const resp = await getNotifications(p);
          return { data: resp.data.data.list || [], success: true, total: resp.data.data.total || 0 };
        }}
        search={false}
        options={{ reload: true, density: true, setting: true }}
        columns={[
          {
            title: "类型", dataIndex: "type", width: 80,
            render: (v: string) => <StatusTag tone={TYPE[v]?.color}>{TYPE[v]?.label || v}</StatusTag>,
          },
          { title: "标题", dataIndex: "title", ellipsis: true },
          { title: "内容", dataIndex: "content", ellipsis: true, render: (v: string | null) => v || "-" },
          {
            title: "状态", dataIndex: "is_read", width: 80,
            render: (v: boolean) => v ? <StatusTag>已读</StatusTag> : <StatusTag tone="info">未读</StatusTag>,
          },
          {
            title: "时间", dataIndex: "created_at", width: 160,
            render: (v: string) => new Date(v).toLocaleString(),
          },
          {
            title: "操作", width: 80,
            render: (_: unknown, r: NotificationItem) => (
              <Space size="small">
                {!r.is_read && (
                  <Button size="small" type="link" onClick={() => handleMarkRead([r.id])}>已读</Button>
                )}
              </Space>
            ),
          },
          ] as any}
      />
    </Card>
  );
}
