import { useEffect, useState } from "react";
import { List, Button, Tag, Space, message, Card, Empty } from "antd";
import { ClockCircleOutlined, DollarOutlined, ExclamationCircleOutlined, CarOutlined } from "@ant-design/icons";
import { getNotifications, markNotificationsRead } from "../../api";
import type { NotificationItem } from "../../types";

const typeIcons: Record<string, React.ReactNode> = {
  delivery: <CarOutlined />,
  payment: <DollarOutlined />,
  followup: <ClockCircleOutlined />,
  expiry: <ExclamationCircleOutlined />,
};

const typeLabels: Record<string, string> = {
  delivery: "交期提醒", payment: "回款到期", followup: "跟进待处理", expiry: "合同到期",
};

export default function NotificationList() {
  const [data, setData] = useState<NotificationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const resp = await getNotifications({ page: p, page_size: 20 });
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
      setUnread(resp.data.data.unread_count);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [page]);

  const handleMarkAll = async () => {
    try {
      await markNotificationsRead({ all: true });
      message.success("已全部标记为已读");
      fetch(1);
    } catch { message.error("操作失败"); }
  };

  const handleMarkOne = async (id: number) => {
    try {
      await markNotificationsRead({ ids: [id] });
      fetch(page);
    } catch { message.error("操作失败"); }
  };

  return (
    <Card title={`消息提醒 ${unread > 0 ? `(${unread}条未读)` : ""}`} extra={
      <Space>
        {unread > 0 && <Button onClick={handleMarkAll}>全部已读</Button>}
      </Space>
    }>
      {data.length === 0 ? <Empty description="暂无消息" /> : (
        <List loading={loading} pagination={{ current: page, total, pageSize: 20, onChange: setPage }}
          dataSource={data} renderItem={(item: NotificationItem) => (
            <List.Item extra={
              !item.is_read && <Button type="link" size="small" onClick={() => handleMarkOne(item.id)}>标为已读</Button>
            }>
              <List.Item.Meta
                avatar={<span style={{ fontSize: 20 }}>{typeIcons[item.type] || <ClockCircleOutlined />}</span>}
                title={
                  <Space>
                    <Tag>{typeLabels[item.type] || item.type}</Tag>
                    <span style={{ fontWeight: item.is_read ? "normal" : "bold" }}>{item.title}</span>
                    {!item.is_read && <Tag color="red">未读</Tag>}
                  </Space>
                }
                description={<span>{item.content} <span style={{ color: "#999", marginLeft: 12 }}>{item.created_at}</span></span>}
              />
            </List.Item>
          )} />
      )}
    </Card>
  );
}
