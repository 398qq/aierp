import { useEffect, useState } from "react";
import { Button, Empty, Input, message, Select, Space, Tag, Typography } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";

import { PlusOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { getApiErrorMessage, getGlobalFollowUps } from "@/api";
import type { GlobalFollowUp, PageData } from "@/types";
import CustomerModuleShell from "./CustomerModuleShell";
import { FollowUpMethodTag, FollowUpPriorityTag, FollowUpStatusTag } from "./customerUi";
import { getGlobalFollowUpDueMeta, GLOBAL_FOLLOW_UP_BUCKETS, type GlobalFollowUpBucket } from "./constants";
import { useApiQuery } from "@/lib/queries";

const { Text } = Typography;

interface FollowUpResponse {
  list: GlobalFollowUp[];
  total: number;
  counts: Record<string, number>;
}

export default function CustomerFollowUpsPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [status, setStatus] = useState<string | undefined>();
  const [priority, setPriority] = useState<string | undefined>();
  const [dueBucket, setDueBucket] = useState<GlobalFollowUpBucket>("all");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(timer);
  }, [q]);

  const params: Record<string, unknown> = {};
  if (debouncedQ) params.q = debouncedQ;
  if (status) params.status = status;
  if (priority) params.priority = priority;
  if (dueBucket !== "all") params.due_bucket = dueBucket;

  const query = useApiQuery<FollowUpResponse>(
    ["global-follow-ups", debouncedQ, status ?? "", priority ?? "", dueBucket],
    "/customers/follow-ups-global",
    params,
    { staleTime: 30 * 1000 },
  );

  const counts = query.data?.counts || {};
  const dataList = query.data?.list || [];

  const columns: ProColumns<GlobalFollowUp>[] = [
    {
      title: "客户",
      dataIndex: "customer_name",
      width: 220,
      fixed: "left",
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Button type="link" size="small" onClick={() => navigate(`/customers/${record.customer_id}`)}>
            {record.customer_name}
          </Button>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.owner || "未分配"}</Text>
        </Space>
      ),
    },
    {
      title: "到期",
      dataIndex: "due_bucket",
      width: 120,
      render: (_, record) => {
        const meta = getGlobalFollowUpDueMeta(record);
        return <Tag color={meta.color}>{meta.text}</Tag>;
      },
    },
    {
      title: "关联商机",
      dataIndex: "opportunity_id",
      width: 120,
      render: (_, r) => r.opportunity_id ? (
        <Button type="link" size="small" onClick={() => navigate(`/sales/opportunities/${r.opportunity_id}`)}>
          OPP-{String(r.opportunity_id).padStart(6, "0")}
        </Button>
      ) : <Text type="secondary">-</Text>,
    },
    {
      title: "方式",
      dataIndex: "method",
      width: 100,
      render: (_, r) => <FollowUpMethodTag method={r.method} />,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (_, r) => <FollowUpStatusTag status={r.status} />,
    },
    {
      title: "优先级",
      dataIndex: "priority",
      width: 90,
      render: (_, r) => <FollowUpPriorityTag priority={r.priority} />,
    },
    {
      title: "计划时间",
      dataIndex: "planned_at",
      width: 150,
      render: (_, r) => r.planned_at ? r.planned_at.slice(0, 16) : <Text type="secondary">未排期</Text>,
    },
    {
      title: "负责人",
      dataIndex: "assigned_to",
      width: 120,
      render: (_, r) => r.assigned_to || <Text type="secondary">未分配</Text>,
    },
    {
      title: "跟进内容",
      dataIndex: "content",
      ellipsis: true,
      render: (_, r) => r.content || <Text type="secondary">-</Text>,
    },
    {
      title: "结果",
      dataIndex: "result",
      ellipsis: true,
      render: (_, r) => r.result || <Text type="secondary">-</Text>,
    },
    {
      title: "操作",
      key: "actions",
      width: 170,
      fixed: "right",
      render: (_, record) => (
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
              onChange={setStatus}
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
              onChange={setPriority}
              style={{ width: 120 }}
              options={[
                { value: "high", label: "高" },
                { value: "medium", label: "中" },
                { value: "low", label: "低" },
              ]}
            />
            <Select
              value={dueBucket}
              onChange={setDueBucket}
              style={{ width: 130 }}
              options={GLOBAL_FOLLOW_UP_BUCKETS.map((item) => ({ value: item.key, label: item.label }))}
            />
          </Space>
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => query.refetch()}>刷新</Button>
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
          rowKey="id"
          columns={columns}
          dataSource={dataList}
          loading={query.isLoading || query.isFetching}
          search={false}
          options={{ reload: () => query.refetch(), density: true, setting: true }}
          size="small"
          bordered
          tableLayout="fixed"
          scroll={{ x: 1500 }}
          rowClassName={(record) => record.due_bucket === "overdue" ? "followup-row-overdue" : ""}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无跟进记录" /> }}
          pagination={{
            total: query.data?.total || 0,
            showSizeChanger: true,
            onChange: () => query.refetch(),
          }}
        />
      </div>
    </CustomerModuleShell>
  );
}