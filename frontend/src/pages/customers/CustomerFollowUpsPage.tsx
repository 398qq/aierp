import { useEffect, useRef, useState } from "react";
import { Button, Empty, Input, message, Select, Space, Tag, Typography } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType } from "@ant-design/pro-components";

import { PlusOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router";
import { getApiErrorMessage, getGlobalFollowUps } from "@/api";
import type { GlobalFollowUp } from "@/types";
import CustomerModuleShell from "./CustomerModuleShell";
import { FollowUpMethodTag, FollowUpPriorityTag, FollowUpStatusTag } from "./customerUi";
import { getGlobalFollowUpDueMeta, GLOBAL_FOLLOW_UP_BUCKETS, type GlobalFollowUpBucket } from "./constants";

const { Text } = Typography;

export default function CustomerFollowUpsPage() {
  const navigate = useNavigate();
  const actionRef = useRef<ActionType>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [status, setStatus] = useState<string | undefined>();
  const [priority, setPriority] = useState<string | undefined>();
  const [dueBucket, setDueBucket] = useState<GlobalFollowUpBucket>("all");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(timer);
  }, [q]);

  const columns: any = [
    {
      title: "客户",
      dataIndex: "customer_name",
      width: 220,
      fixed: "left",
      render: (name: string, record: any) => (
        <Space direction="vertical" size={0}>
          <Button type="link" size="small" onClick={() => navigate(`/customers/${record.customer_id}`)}>
            {name}
          </Button>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.owner || "未分配"}</Text>
        </Space>
      ),
    },
    {
      title: "到期",
      dataIndex: "due_bucket",
      width: 120,
      render: (_: string, record: any) => {
        const meta = getGlobalFollowUpDueMeta(record);
        return <Tag color={meta.color}>{meta.text}</Tag>;
      },
    },
    {
      title: "关联商机",
      dataIndex: "opportunity_id",
      width: 120,
      render: (value: number | null | undefined) => value ? (
        <Button type="link" size="small" onClick={() => navigate(`/sales/opportunities/${value}`)}>
          OPP-{String(value).padStart(6, "0")}
        </Button>
      ) : <Text type="secondary">-</Text>,
    },
    {
      title: "方式",
      dataIndex: "method",
      width: 100,
      render: (method: string | null) => <FollowUpMethodTag method={method} />,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (value: string | null) => <FollowUpStatusTag status={value} />,
    },
    {
      title: "优先级",
      dataIndex: "priority",
      width: 90,
      render: (value: string | null) => <FollowUpPriorityTag priority={value} />,
    },
    {
      title: "计划时间",
      dataIndex: "planned_at",
      width: 150,
      render: (value: string | null) => value ? value.slice(0, 16) : <Text type="secondary">未排期</Text>,
    },
    {
      title: "负责人",
      dataIndex: "assigned_to",
      width: 120,
      render: (value: string | null) => value || <Text type="secondary">未分配</Text>,
    },
    {
      title: "跟进内容",
      dataIndex: "content",
      ellipsis: true,
      render: (value: string | null) => value || <Text type="secondary">-</Text>,
    },
    {
      title: "结果",
      dataIndex: "result",
      ellipsis: true,
      render: (value: string | null) => value || <Text type="secondary">-</Text>,
    },
    {
      title: "操作",
      key: "actions",
      width: 170,
      fixed: "right",
      render: (_: unknown, record: any) => (
        <Space size={4}>
          {record.opportunity_id ? (
            <Button size="small" onClick={() => navigate(`/sales/opportunities/${record.opportunity_id}`)}>商机</Button>
          ) : null}
          <Button size="small" onClick={() => navigate(`/customers/${record.customer_id}/follow-ups`)}>
            客户跟进
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <CustomerModuleShell title="跟进记录" subtitle="全局客户跟进台账、逾期提醒与后续行动">
      <div className="followup-ledger">
        <div className="followup-ledger-command">
          <Space wrap>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="客户、联系人、内容、负责人"
              value={q}
              onChange={(event) => { setQ(event.target.value); }}
              style={{ width: 300 }}
            />
            <Select
              allowClear
              placeholder="状态"
              value={status}
              onChange={(value) => { setStatus(value); }}
              style={{ width: 130 }}
              options={[
                { value: "planned", label: "计划中" },
                { value: "in_progress", label: "进行中" },
                { value: "completed", label: "已完成" },
                { value: "cancelled", label: "已取消" },
              ]}
            />
            <Select
              allowClear
              placeholder="优先级"
              value={priority}
              onChange={(value) => { setPriority(value); }}
              style={{ width: 120 }}
              options={[
                { value: "high", label: "高" },
                { value: "medium", label: "中" },
                { value: "low", label: "低" },
              ]}
            />
            <Select
              value={dueBucket}
              onChange={(value) => { setDueBucket(value); }}
              style={{ width: 130 }}
              options={GLOBAL_FOLLOW_UP_BUCKETS.map((item) => ({ value: item.key, label: item.label }))}
            />
          </Space>
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => actionRef.current?.reload()}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/customers")}>选择客户新建</Button>
          </Space>
        </div>

        <div className="followup-ledger-metrics">
          <div><span>全部记录</span><strong>{counts.all ?? 0}</strong></div>
          <div className="is-danger"><span>逾期</span><strong>{counts.overdue ?? 0}</strong></div>
          <div className="is-warning"><span>今日</span><strong>{counts.today ?? 0}</strong></div>
          <div><span>未来</span><strong>{counts.upcoming ?? 0}</strong></div>
          <div><span>未排期</span><strong>{counts.unscheduled ?? 0}</strong></div>
          <div><span>已关闭</span><strong>{counts.closed ?? 0}</strong></div>
        </div>

        <ProTable<GlobalFollowUp>
          className="erp-table followup-ledger-table"
          actionRef={actionRef}
          rowKey="id"
          columns={columns}
          request={async (params) => {
            try {
              const resp = await getGlobalFollowUps({
                page: params.current,
                page_size: params.pageSize,
                q: params.q || undefined,
                status: params.status,
                priority: params.priority,
                ...(params.due_bucket ? { due_bucket: params.due_bucket } : {}),
              });
              const payload = resp.data.data;
              setCounts(payload.counts || {});
              return { data: payload.list || [], total: payload.total || 0, success: true };
            } catch {
              return { data: [], total: 0, success: false };
            }
          }}
          params={{ q: debouncedQ || undefined, status, priority, due_bucket: dueBucket !== "all" ? dueBucket : undefined }}
          search={false}
          options={{ reload: true, density: true, setting: true }}
          size="small"
          bordered
          tableLayout="fixed"
          scroll={{ x: 1500 }}
          rowClassName={(record) => record.due_bucket === "overdue" ? "followup-row-overdue" : ""}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无跟进记录" /> }}
        />
      </div>
    </CustomerModuleShell>
  );
}
