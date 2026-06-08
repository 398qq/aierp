// CustomerReminderDrawer — right-side drawer showing follow-up reminders
// (overdue / today / upcoming), with complete / postpone / view actions.

import { useNavigate } from "react-router-dom";
import {
  Button,
  Drawer,
  Empty,
  List,
  Segmented,
  Space,
  Typography,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { StatusTag } from "../../ui";
import type { FollowUpReminder } from "../../types";
import {
  formatDateTime,
  formatReminderRefreshTime,
  getReminderDueMeta,
  ReminderBucket,
  REMINDER_BUCKETS,
} from "./constants";

interface Props {
  open: boolean;
  loading: boolean;
  bucket: ReminderBucket;
  reminderCounts: Record<ReminderBucket, number>;
  visibleReminders: FollowUpReminder[];
  refreshedAt: Date | null;
  overdueOnly: boolean;
  actionKey: string | null;
  onClose: () => void;
  onReload: () => void;
  onToggleOverdueOnly: () => void;
  onChangeBucket: (bucket: ReminderBucket) => void;
  onComplete: (item: FollowUpReminder) => void;
  onPostpone: (item: FollowUpReminder) => void;
}

export default function CustomerReminderDrawer({
  open,
  loading,
  bucket,
  reminderCounts,
  visibleReminders,
  refreshedAt,
  overdueOnly,
  actionKey,
  onClose,
  onReload,
  onToggleOverdueOnly,
  onChangeBucket,
  onComplete,
  onPostpone,
}: Props) {
  const navigate = useNavigate();
  return (
    <Drawer
      title="跟进提醒"
      width={620}
      open={open}
      onClose={onClose}
      extra={(
        <Space>
          <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={onReload}>
            刷新
          </Button>
          <Button
            size="small"
            type={overdueOnly ? "primary" : "default"}
            onClick={onToggleOverdueOnly}
          >
            {overdueOnly ? "取消逾期筛选" : "只看逾期客户"}
          </Button>
        </Space>
      )}
    >
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        <Segmented
          value={bucket}
          options={REMINDER_BUCKETS.map((item) => ({
            value: item.key,
            label: `${item.label} ${reminderCounts[item.key] ?? 0}`,
          }))}
          onChange={(value) => onChangeBucket(value as ReminderBucket)}
        />
        <Typography.Text type="secondary">{formatReminderRefreshTime(refreshedAt)}</Typography.Text>
        {visibleReminders.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待处理跟进提醒" />
        ) : (
          <List
            loading={loading}
            dataSource={visibleReminders}
            renderItem={(item) => {
              const due = getReminderDueMeta(item);
              return (
                <List.Item
                  actions={[
                    <Button
                      key="complete"
                      size="small"
                      type="link"
                      loading={actionKey === `complete-${item.id}`}
                      onClick={() => onComplete(item)}
                    >
                      完成
                    </Button>,
                    <Button
                      key="postpone"
                      size="small"
                      type="link"
                      loading={actionKey === `postpone-${item.id}`}
                      onClick={() => onPostpone(item)}
                    >
                      延期1天
                    </Button>,
                    <Button
                      key="customer"
                      size="small"
                      type="link"
                      onClick={() => navigate(`/customers/${item.customer_id}`)}
                    >
                      查看客户
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={(
                      <Space size={6} wrap>
                        <Typography.Link onClick={() => navigate(`/customers/${item.customer_id}`)}>
                          {item.customer_name}
                        </Typography.Link>
                        <StatusTag tone={due.color}>{due.text}</StatusTag>
                        {item.priority && <StatusTag>{item.priority}</StatusTag>}
                        {item.owner && <Typography.Text type="secondary">{item.owner}</Typography.Text>}
                      </Space>
                    )}
                    description={`${item.method || "跟进"} | 计划 ${formatDateTime(item.planned_at)}${item.content ? ` | ${item.content}` : ""}`}
                  />
                </List.Item>
              );
            }}
          />
        )}
      </Space>
    </Drawer>
  );
}
