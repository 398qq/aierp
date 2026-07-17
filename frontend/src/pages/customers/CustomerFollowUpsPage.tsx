import { useCallback, useEffect, useState } from "react";
import { Button, Empty, Input, message, Select, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PlusOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { getApiErrorMessage, getGlobalFollowUps } from "@/api";
import type { GlobalFollowUp } from "@/types";
import CustomerModuleShell from "./CustomerModuleShell";
import { erpPagination } from "@/ui/pagination";
import { FollowUpMethodTag, FollowUpPriorityTag, FollowUpStatusTag } from "./customerUi";
import { getGlobalFollowUpDueMeta, GLOBAL_FOLLOW_UP_BUCKETS, type GlobalFollowUpBucket } from "./constants";

const { Text } = Typography;

const PAGE_SIZE = 20;

export default function CustomerFollowUpsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<GlobalFollowUp[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [status, setStatus] = useState<string | undefined>();
  const [priority, setPriority] = useState<string | undefined>();
  const [dueBucket, setDueBucket] = useState<GlobalFollowUpBucket>("all");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(timer);
  }, [q]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
        q: debouncedQ || undefined,
        status,
        priority,
      };
      if (dueBucket !== "all") params.due_bucket = dueBucket;
      const resp = await getGlobalFollowUps(params);
      const payload = resp.data.data;
      setData(payload.list || []);
      setTotal(payload.total || 0);
      setCounts(payload.counts || {});
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "加载跟进记录失败"));
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedQ, status, priority, dueBucket]);

  useEffect(() => {
    load();
  }, [load]);

  const columns: ColumnsType<GlobalFollowUp> = [
    {
      title: "客户",
      dataIndex: "customer_name",
      width: 220,
      fixed: "left",
      render: (name: string, record) => (
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
      render: (_: string, record) => {
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
      render: (_: unknown, record) => (
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
              onChange={(event) => { setQ(event.target.value); setPage(1); }}
              style={{ width: 300 }}
            />
            <Select
              allowClear
              placeholder="状态"
              value={status}
              onChange={(value) => { setStatus(value); setPage(1); }}
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
              onChange={(value) => { setPriority(value); setPage(1); }}
              style={{ width: 120 }}
              options={[
                { value: "high", label: "高" },
                { value: "medium", label: "中" },
                { value: "low", label: "低" },
              ]}
            />
            <Select
              value={dueBucket}
              onChange={(value) => { setDueBucket(value); setPage(1); }}
              style={{ width: 130 }}
              options={GLOBAL_FOLLOW_UP_BUCKETS.map((item) => ({ value: item.key, label: item.label }))}
            />
          </Space>
          <Space wrap>
            <Button icon={<ReloadOutlined />} loading={loading} onClick={load}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/customers")}>选择客户新建</Button>
          </Space>
        </div>

        <div className="followup-ledger-metrics">
          <div><span>全部记录</span><strong>{counts.all ?? total}</strong></div>
          <div className="is-danger"><span>逾期</span><strong>{counts.overdue ?? 0}</strong></div>
          <div className="is-warning"><span>今日</span><strong>{counts.today ?? 0}</strong></div>
          <div><span>未来</span><strong>{counts.upcoming ?? 0}</strong></div>
          <div><span>未排期</span><strong>{counts.unscheduled ?? 0}</strong></div>
          <div><span>已关闭</span><strong>{counts.closed ?? 0}</strong></div>
        </div>

        <Table<GlobalFollowUp>
          className="erp-table followup-ledger-table"
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="small"
          bordered
          tableLayout="fixed"
          scroll={{ x: 1500 }}
          rowClassName={(record) => record.due_bucket === "overdue" ? "followup-row-overdue" : ""}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无跟进记录" /> }}
          pagination={erpPagination({
            current: page,
            pageSize,
            total,
            onChange: (nextPage, nextSize) => { setPage(nextSize !== pageSize ? 1 : nextPage); setPageSize(nextSize); },
          })}
        />
      </div>
    </CustomerModuleShell>
  );
}
