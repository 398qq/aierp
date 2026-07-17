import { useEffect, useState } from "react";
import { Table, Button, Space, Tag, message, Card, Popconfirm } from "antd";
import { StatusTag } from "../../ui";
import { erpPagination } from "../../ui/pagination";
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
  const [data, setData] = useState<NotificationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (unreadOnly) params.unread_only = true;
      const resp = await getNotifications(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载失败")); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, pageSize, unreadOnly]);

  const handleMarkAllRead = async () => {
    try {
      await markNotificationsRead({ all: true });
      message.success("全部已读");
      load();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "操作失败")); }
  };

  const handleMarkRead = async (ids: number[]) => {
    try {
      await markNotificationsRead({ ids });
      load();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "操作失败")); }
  };

  return (
    <Card
      title="通知中心"
      extra={
        <Space>
          <Button size="small" type={unreadOnly ? "primary" : "default"} onClick={() => { setUnreadOnly(!unreadOnly); setPage(1); }}>
            {unreadOnly ? "显示全部" : "仅未读"}
          </Button>
          <Button size="small" icon={<CheckOutlined />} onClick={handleMarkAllRead}>全部已读</Button>
        </Space>
      }
    >
      <Table
        rowKey="id"
        loading={loading}
        dataSource={data}
        rowClassName={(r) => r.is_read ? "" : "ant-table-row-highlight"}
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
        ]}
        pagination={erpPagination({ current: page, total, pageSize, onChange: (nextPage, nextSize) => { setPage(nextSize !== pageSize ? 1 : nextPage); setPageSize(nextSize); } })}
      />
    </Card>
  );
}
