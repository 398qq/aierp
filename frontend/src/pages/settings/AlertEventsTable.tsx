import { useRef, useState } from "react";
import { Badge, Button, Select, Space, message } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType, ProColumns } from "@ant-design/pro-components";
import { ThunderboltOutlined } from "@ant-design/icons";
import { StatusTag } from "../../ui";
import { SEVERITY_TONES } from "./constants";
import {
  getAlertEvents,
  markAlertRead,
  markAllAlertsRead,
  checkAlerts,
  getApiErrorMessage,
} from "../../api";
import type { AlertEvent } from "../../types";

export default function AlertEventsTable() {
  const actionRef = useRef<ActionType>(null);
  const [readFilter, setReadFilter] = useState<boolean | undefined>();
  const [checkLoading, setCheckLoading] = useState(false);

  const handleMarkRead = async (id: number) => {
    try {
      await markAlertRead(id);
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "操作失败"));
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllAlertsRead();
      message.success("已全部标记已读");
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "操作失败"));
    }
  };

  const handleCheckAlerts = async () => {
    setCheckLoading(true);
    try {
      const resp = await checkAlerts();
      message.success(`预警检查完成，生成 ${resp.data.data.generated} 条预警`);
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "预警检查失败"));
    } finally {
      setCheckLoading(false);
    }
  };

  const columns: ProColumns<AlertEvent>[] = [
    { title: "客户ID", dataIndex: "customer_id", width: 80 },
    { title: "规则名称", dataIndex: "rule_name", width: 120 },
    {
      title: "严重级别",
      dataIndex: "severity",
      width: 80,
      render: (_, r) => (
        <StatusTag status={r.severity} tone={SEVERITY_TONES[r.severity] || "neutral"} />
      ),
    },
    { title: "预警消息", dataIndex: "message", ellipsis: true },
    {
      title: "时间",
      dataIndex: "created_at",
      width: 160,
      render: (_, r) => r.created_at?.slice(0, 19),
    },
    {
      title: "状态",
      dataIndex: "is_read",
      width: 70,
      render: (_, r) =>
        r.is_read ? (
          <StatusTag status="已读" tone="neutral" />
        ) : (
          <Badge status="processing" text="未读" />
        ),
    },
    {
      title: "操作",
      key: "actions",
      width: 80,
      render: (_, r) =>
        r.is_read ? null : (
          <Button size="small" onClick={() => handleMarkRead(r.id)}>
            已读
          </Button>
        ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<ThunderboltOutlined />}
          loading={checkLoading}
          onClick={handleCheckAlerts}
        >
          执行预警检查
        </Button>
        <Select
          allowClear
          placeholder="读取状态"
          style={{ width: 110 }}
          value={readFilter}
          onChange={setReadFilter}
          options={[
            { value: false, label: "未读" },
            { value: true, label: "已读" },
          ]}
        />
        <Button onClick={handleMarkAllRead}>全部标记已读</Button>
      </Space>
      <ProTable<AlertEvent>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        options={{ reload: true, density: true, setting: true }}
        size="small"
        params={{ isRead: readFilter }}
        request={async (params) => {
          const apiParams: Record<string, unknown> = {
            page: params.current,
            page_size: params.pageSize,
          };
          if (readFilter !== undefined) apiParams.is_read = readFilter;
          const r = await getAlertEvents(apiParams);
          const list = r.data.data?.list || [];
          const total = r.data.data?.total || 0;
          return { data: list, success: true, total };
        }}
        pagination={{ defaultPageSize: 20, showSizeChanger: true }}
      />
    </div>
  );
}
