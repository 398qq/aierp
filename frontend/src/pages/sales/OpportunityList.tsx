/**
 * 商机列表（看板 + 列表双视图）
 *
 * 服务端化版本——useApiQuery + 受控 ProTable + 共享数据源。
 * Spec: docs/frontend/opportunity-list-design.md
 */
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  App,
  Button,
  Card,
  Dropdown,
  Input,
  Modal,
  Progress,
  Segmented,
  Select,
  Space,
  Switch,
  Typography,
  message as staticMessage,
} from "antd";
import type { ProColumns } from "@ant-design/pro-components";
import { ProTable } from "@ant-design/pro-components";
import type { MenuProps } from "antd";
import {
  AppstoreOutlined,
  BarsOutlined,
  DeleteOutlined,
  EllipsisOutlined,
  EyeOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

import {
  batchUpdateOpportunities,
  deleteOpportunity,
  getApiErrorMessage,
  type OpportunityCounts,
  type OpportunityListResp,
} from "../../api";
import PipelineBoard from "../../components/sales/PipelineBoard";
import type { Opportunity, OpportunityAI } from "../../types";
import { useApiQuery, useQueryClient } from "@/lib/queries";
import {
  CustomerLink,
  CustomerSelect,
  ErpExportButton,
  MetricBand,
  SalesModuleShell,
  SalesQuickActions,
  SalesStatusTag,
  erpRowClass,
  money,
  shortDate,
  stageLabel,
  statusDot,
  ERP_STATUS_DOT,
} from "./salesUi";
import { StatusTag } from "../../ui";

const STAGE_OPTIONS = [
  { value: "lead", label: "线索" },
  { value: "qualified", label: "需求确认" },
  { value: "proposal", label: "报价中" },
  { value: "negotiation", label: "谈判" },
  { value: "closed_won", label: "赢单" },
  { value: "closed_lost", label: "输单" },
];

const STATUS_OPTIONS = [
  { value: "active", label: "活跃" },
  { value: "won", label: "已赢单" },
  { value: "lost", label: "已输单" },
];

const KANBAN_CAP = 200;
const PAGE_SIZE = 20;

export default function OpportunityList() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [view, setView] = useState<"board" | "list">("board");
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [stage, setStage] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [searchText, setSearchText] = useState("");
  const [q, setQ] = useState("");
  const [includeAi, setIncludeAi] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [aiEnabled, setAiEnabled] = useState(false);

  // Shared query: board + list views read from this single useApiQuery.
  // view is in key so toggling board/list isn't free, but params change is.
  const apiParams = useMemo<Record<string, unknown>>(() => {
    const p: Record<string, unknown> = view === "board"
      ? { kanban: "true" } // board mode caps at 200 + bypasses pagination
      : { page, page_size: PAGE_SIZE };
    if (status) p.status = status;
    if (stage) p.stage = stage;
    if (q.trim()) p.q = q.trim();
    if (customerId) p.customer_id = customerId;
    if (aiEnabled) p.include_ai = "true";
    return p;
  }, [view, page, status, stage, q, customerId, aiEnabled]);

  const query = useApiQuery<OpportunityListResp>(
    [
      "opportunities",
      view,
      page,
      status ?? "",
      stage ?? "",
      q,
      customerId ?? "",
      aiEnabled,
    ],
    "/opportunities",
    apiParams,
    { staleTime: 30 * 1000 },
  );

  const list = query.data?.list ?? [];
  const total = query.data?.total ?? 0;
  const counts: OpportunityCounts = query.data?.counts ?? {
    count: 0, amount: 0, weightedAmount: 0, active: 0,
    overdue: 0, dueSoon: 0, atRisk: 0,
  };
  const aiMap: Record<number, OpportunityAI> = query.data?.ai ?? {};
  const showKanbanCap = view === "board" && total > KANBAN_CAP;

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["opportunities"] });

  // Reset page to 1 whenever any filter or view changes
  const onFilterChange = (setter: () => void) => () => {
    setter();
    setPage(1);
  };

  const exportData = useMemo(
    () =>
      list.map((r) => ({
        id: r.id,
        title: r.title,
        customer_id: r.customer_id,
        stage: r.stage ? stageLabel[r.stage] || r.stage : "",
        status: STATUS_OPTIONS.find((s) => s.value === r.status)?.label || r.status,
        amount: r.amount || 0,
        weighted_amount: (Number(r.amount || 0) * Number(r.win_probability || 0)) / 100,
        win_probability: r.win_probability ?? 0,
        expected_close_date: r.expected_close_date?.slice(0, 10) || "",
        assigned_to: r.assigned_to || "",
        source: r.source || "",
        updated_at: r.updated_at?.slice(0, 10) || r.created_at?.slice(0, 10) || "",
      })),
    [list],
  );

  const batchStage = async (nextStage: string) => {
    if (!selected.length) return;
    try {
      await batchUpdateOpportunities(selected, nextStage);
      message.success("阶段已更新");
      setSelected([]);
      invalidate();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "批量更新失败"));
    }
  };

  const handleRefresh = () => query.refetch();

  // Inline: only the columns that need `r` access use record-form
  const columns: ProColumns<Opportunity>[] = [
    {
      title: "#",
      width: 45,
      fixed: "left",
      render: (_, __, index) => index + 1,
    },
    {
      title: "商机",
      dataIndex: "title",
      ellipsis: true,
      fixed: "left",
      render: (_, record) => (
        <div>
          <div className="erp-cell-primary">
            <Typography.Link
              strong
              onClick={() => navigate(`/sales/opportunities/${record.id}`)}
            >
              {record.title || `#${record.id}`}
            </Typography.Link>
          </div>
          <div className="erp-cell-secondary">
            <CustomerLink id={record.customer_id} />
          </div>
        </div>
      ),
    },
    {
      title: "阶段",
      dataIndex: "stage",
      width: 110,
      sorter: (a, b) => (a.stage || "").localeCompare(b.stage || ""),
      render: (_, r) => (
        <StatusTag
          status={r.stage || "-"}
          color="blue"
          label={stageLabel[r.stage || ""] || r.stage || "-"}
        />
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      sorter: (a, b) => (a.status || "").localeCompare(b.status || ""),
      render: (_, r) => (
        <>
          {statusDot(ERP_STATUS_DOT[r.status || ""] || "#d9d9d9")}
          <SalesStatusTag value={r.status} />
        </>
      ),
    },
    {
      title: "金额",
      dataIndex: "amount",
      width: 130,
      align: "right",
      sorter: (a, b) => Number(a.amount || 0) - Number(b.amount || 0),
      render: (_, r) => (
        <Typography.Text strong>{money(r.amount)}</Typography.Text>
      ),
    },
    {
      title: "加权金额",
      key: "weighted_amount",
      width: 130,
      align: "right",
      sorter: (a, b) =>
        Number(a.amount || 0) * Number(a.win_probability || 0) -
        Number(b.amount || 0) * Number(b.win_probability || 0),
      render: (_, r) => (
        <Typography.Text>
          {money(
            (Number(r.amount || 0) * Number(r.win_probability || 0)) / 100,
          )}
        </Typography.Text>
      ),
    },
    {
      title: "赢率",
      dataIndex: "win_probability",
      width: 150,
      sorter: (a, b) => Number(a.win_probability || 0) - Number(b.win_probability || 0),
      render: (_, r) => (
        <Space direction="vertical" size={0} style={{ width: "100%" }}>
          <Progress percent={Number(r.win_probability || 0)} size="small" showInfo={false} />
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {r.win_probability ?? 0}%
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "预计成交",
      dataIndex: "expected_close_date",
      width: 120,
      sorter: (a, b) =>
        (a.expected_close_date || "").localeCompare(b.expected_close_date || ""),
      render: (_, r) => shortDate(r.expected_close_date || r.created_at),
    },
    {
      title: "负责人",
      dataIndex: "assigned_to",
      width: 120,
      render: (_, r) => r.assigned_to || "-",
    },
    {
      title: "来源",
      dataIndex: "source",
      width: 120,
      ellipsis: true,
      render: (_, r) => r.source || "-",
    },
    {
      title: "最近更新",
      dataIndex: "updated_at",
      width: 120,
      sorter: (a, b) =>
        (a.updated_at || a.created_at || "").localeCompare(
          b.updated_at || b.created_at || "",
        ),
      render: (_, r) => shortDate(r.updated_at || r.created_at),
    },
    {
      title: "风险",
      key: "risk",
      width: 90,
      render: (_, r) => {
        const risk = aiMap[r.id]?.risk_level ?? counts.atRisk > 0 ? null : null;
        const riskFromMap = aiMap[r.id]?.risk_level;
        if (!riskFromMap) return <Typography.Text type="secondary">未分析</Typography.Text>;
        return (
          <StatusTag
            tone={
              riskFromMap === "high" ? "danger" :
              riskFromMap === "medium" ? "warning" : "success"
            }
          >
            {riskFromMap === "high" ? "高风险" : riskFromMap === "medium" ? "关注" : "正常"}
          </StatusTag>
        );
      },
    },
    {
      title: "操作",
      width: 60,
      fixed: "right",
      render: (_, record) => {
        const items: MenuProps["items"] = [
          {
            key: "view",
            icon: <EyeOutlined />,
            label: "查看详情",
            onClick: () => navigate(`/sales/opportunities/${record.id}`),
          },
          {
            key: "quote",
            icon: <FileTextOutlined />,
            label: "创建报价",
            onClick: () =>
              navigate(
                `/sales/quotations/new?customer_id=${record.customer_id}&opportunity_id=${record.id}`,
              ),
          },
          { type: "divider" as const },
          {
            key: "delete",
            icon: <DeleteOutlined />,
            label: "删除",
            danger: true,
            onClick: () => {
              Modal.confirm({
                title: "确定删除?",
                content: `删除商机 #${record.id}？`,
                okText: "删除",
                cancelText: "取消",
                okButtonProps: { danger: true },
                onOk: async () => {
                  try {
                    await deleteOpportunity(record.id);
                    message.success("已删除");
                    invalidate();
                  } catch (e: unknown) {
                    message.error(getApiErrorMessage(e, "删除失败"));
                  }
                },
              });
            },
          },
        ];
        return (
          <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
            <Button size="small" icon={<EllipsisOutlined />} type="text" />
          </Dropdown>
        );
      },
    },
  ];

  return (
    <SalesModuleShell
      title="商机管理"
      subtitle="以客户需求为入口，推动产品推荐、报价和订单转化"
      activeKey="opportunities"
      extra={<SalesQuickActions />}
    >
      <MetricBand
        items={[
          { title: "商机数", value: counts.count, suffix: "个", prefix: <ThunderboltOutlined /> },
          { title: "活跃商机", value: counts.active, suffix: "个" },
          { title: "预计金额", value: counts.amount, prefix: "¥", precision: 0 },
          { title: "加权金额", value: counts.weightedAmount, prefix: "¥", precision: 0 },
          { title: "已超期", value: counts.overdue, suffix: "个" },
          { title: "14天内预计成交", value: counts.dueSoon, suffix: "个" },
          {
            title: "高风险",
            value: aiEnabled ? counts.atRisk : "-",
            suffix: aiEnabled ? "个" : undefined,
          },
        ]}
      />

      <Card
        size="small"
        style={{ marginBottom: 16 }}
        title={<Typography.Text strong>商机筛选</Typography.Text>}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate("/sales/opportunities/new")}
            >
              新建商机
            </Button>
          </Space>
        }
      >
        <Space wrap size={[8, 10]}>
          <Input.Search
            allowClear
            placeholder="搜索客户 / 商机 / 负责人 / 来源"
            value={searchText}
            onChange={(event) => {
              setSearchText(event.target.value);
              if (!event.target.value) setQ("");
            }}
            onSearch={(value) => setQ(value)}
            style={{ width: 300 }}
          />
          <div style={{ width: 260 }}>
            <CustomerSelect value={customerId} onChange={onFilterChange(() => setCustomerId(undefined))} />
          </div>
          <Segmented
            value={view}
            onChange={(v) => {
              setView(v as "board" | "list");
              setPage(1);
            }}
            options={[
              { label: (<><AppstoreOutlined /> 看板</>), value: "board" },
              { label: (<><BarsOutlined /> 列表</>), value: "list" },
            ]}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 128 }}
            value={status}
            onChange={onFilterChange(() => setStatus(undefined))}
            options={STATUS_OPTIONS}
          />
          <Select
            placeholder="阶段"
            allowClear
            style={{ width: 140 }}
            value={stage}
            onChange={onFilterChange(() => setStage(undefined))}
            options={STAGE_OPTIONS}
          />
          <Button onClick={() => {
            setStatus(undefined);
            setStage(undefined);
            setCustomerId(undefined);
            setSearchText("");
            setQ("");
            setPage(1);
          }}>清空筛选</Button>
          <Space>
            <Switch
              checked={aiEnabled}
              onChange={setAiEnabled}
              size="small"
            />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
          <ErpExportButton
            data={exportData}
            columns={[
              { key: "id", title: "ID" },
              { key: "title", title: "商机" },
              { key: "customer_id", title: "客户ID" },
              { key: "stage", title: "阶段" },
              { key: "status", title: "状态" },
              { key: "amount", title: "金额" },
              { key: "weighted_amount", title: "加权金额" },
              { key: "win_probability", title: "赢率(%)" },
              { key: "expected_close_date", title: "预计成交" },
              { key: "assigned_to", title: "负责人" },
              { key: "source", title: "来源" },
              { key: "updated_at", title: "最近更新" },
            ]}
            filename="opportunities_export.csv"
          />
          {selected.length ? (
            <Select
              placeholder={`批量推进 ${selected.length} 个`}
              style={{ width: 180 }}
              onChange={(nextStage) => batchStage(nextStage)}
              options={STAGE_OPTIONS}
            />
          ) : null}
        </Space>
      </Card>

      {showKanbanCap && (
        <Card size="small" style={{ marginBottom: 12, borderColor: "#faad14" }}>
          <Space>
            <Typography.Text type="warning">
              当前商机数 {total} 超过看板展示上限 {KANBAN_CAP}。看板仅显示前 {KANBAN_CAP} 条；建议切换列表视图以查看全部。
            </Typography.Text>
            <Button size="small" onClick={() => { setView("list"); setPage(1); }}>
              切到列表视图
            </Button>
          </Space>
        </Card>
      )}

      {view === "board" ? (
        <PipelineBoard
          opportunities={list}
          aiMap={aiMap}
          loading={query.isLoading || query.isFetching}
          onRefresh={invalidate}
        />
      ) : (
        <Card size="small" title="商机清单" className="erp-table">
          <ProTable<Opportunity>
            rowKey="id"
            search={false}
            options={{ reload: () => query.refetch(), density: true, setting: true }}
            rowClassName={erpRowClass}
            rowSelection={{
              selectedRowKeys: selected,
              onChange: (keys) => setSelected(keys as number[]),
            }}
            scroll={{ x: "max-content" }}
            columns={columns}
            dataSource={list}
            loading={query.isLoading || query.isFetching}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total,
              showSizeChanger: false,
              onChange: (p) => setPage(p),
            }}
          />
        </Card>
      )}

      <Card size="small" style={{ marginTop: 16 }} type="inner">
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          指标（金额、加权金额、活跃数、已超期、14天内预计成交、高风险）现在由后端在
          与列表相同的过滤集上聚合计算，不再受单页数据量限制（之前的 100 条上限被打破）。
        </Typography.Paragraph>
      </Card>
    </SalesModuleShell>
  );
}
