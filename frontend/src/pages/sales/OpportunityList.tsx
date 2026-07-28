import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  Col,
  Dropdown,
  Input,
  Modal,
  Progress,
  Row,
  Segmented,
  Select,
  Space,
  Spin,
  Switch,
  Typography,
  message,
} from "antd";
import { StatusTag } from "../../ui";
import type { ActionType, ProColumns } from "@ant-design/pro-components";
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
  getOpportunities,
  getApiErrorMessage,
} from "../../api";
import PipelineBoard from "../../components/sales/PipelineBoard";
import type { Opportunity, OpportunityAI } from "../../types";
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

export default function OpportunityList() {
  const actionRef = useRef<ActionType>(null);
  const [data, setData] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | undefined>();
  const [stage, setStage] = useState<string | undefined>();
  const [assignedTo, setAssignedTo] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [searchText, setSearchText] = useState("");
  const [q, setQ] = useState("");
  const [view, setView] = useState<"board" | "list">("board");
  const [includeAi, setIncludeAi] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [aiMap, setAiMap] = useState<Record<number, OpportunityAI>>({});
  const navigate = useNavigate();

  const tableParams = useMemo(() => {
    const p: Record<string, unknown> = {};
    if (status) p.status = status;
    if (stage) p.stage = stage;
    if (assignedTo) p.assigned_to = assignedTo;
    if (customerId) p.customer_id = customerId;
    if (q) p.q = q;
    if (includeAi) p.include_ai = true;
    return p;
  }, [status, stage, assignedTo, customerId, q, includeAi]);

  const doFetch = useCallback(
    async (extraParams: Record<string, unknown> = {}) => {
      setLoading(true);
      try {
        const params: Record<string, unknown> = { page_size: 100, ...extraParams };
        if (status) params.status = status;
        if (stage) params.stage = stage;
        if (assignedTo) params.assigned_to = assignedTo;
        if (customerId) params.customer_id = customerId;
        if (q.trim()) params.q = q.trim();
        if (includeAi) params.include_ai = true;
        const resp = await getOpportunities(params);
        const list: Opportunity[] = resp.data.data.list || [];
        setData(list);
        setAiMap(
          includeAi
            ? (resp.data.data as unknown as { ai?: Record<number, OpportunityAI> }).ai || {}
            : {},
        );
        return list;
      } catch (e: unknown) {
        message.error(getApiErrorMessage(e, "加载失败"));
        return [];
      } finally {
        setLoading(false);
      }
    },
    [status, stage, assignedTo, customerId, q, includeAi],
  );

  // Load data on mount and when filters change (used for board view and list view initial state)
  useEffect(() => {
    doFetch();
  }, [doFetch]);

  const ownerOptions = useMemo(
    () =>
      Array.from(new Set(data.map((item) => item.assigned_to).filter(Boolean) as string[]))
        .sort((a, b) => a.localeCompare(b, "zh-CN"))
        .map((value) => ({ value, label: value })),
    [data],
  );

  const stats = useMemo(() => {
    const amount = data.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    const weightedAmount = data.reduce(
      (sum, item) => sum + (Number(item.amount || 0) * Number(item.win_probability || 0)) / 100,
      0,
    );
    const avgWin = data.length
      ? data.reduce((sum, item) => sum + Number(item.win_probability || 0), 0) / data.length
      : 0;
    const active = data.filter((item) => item.status === "active").length;
    const dueSoon = data.filter((item) => {
      if (!item.expected_close_date || item.status !== "active") return false;
      const due = new Date(item.expected_close_date).getTime();
      if (Number.isNaN(due)) return false;
      const diffDays = Math.ceil((due - Date.now()) / (24 * 60 * 60 * 1000));
      return diffDays >= 0 && diffDays <= 14;
    }).length;
    const overdue = data.filter((item) => {
      if (!item.expected_close_date || item.status !== "active") return false;
      const due = new Date(item.expected_close_date).getTime();
      return !Number.isNaN(due) && due < Date.now();
    }).length;
    const atRisk = includeAi
      ? Object.values(aiMap).filter((item) => item.risk_level === "high").length
      : 0;
    return { amount, weightedAmount, avgWin, active, dueSoon, overdue, atRisk };
  }, [aiMap, data, includeAi]);

  const clearFilters = () => {
    setStatus(undefined);
    setStage(undefined);
    setAssignedTo(undefined);
    setCustomerId(undefined);
    setSearchText("");
    setQ("");
  };

  const exportData = useMemo(
    () =>
      data.map((r) => ({
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
    [data],
  );

  const batchStage = async (nextStage: string) => {
    if (!selected.length) return;
    try {
      await batchUpdateOpportunities(selected, nextStage);
      message.success("阶段已更新");
      setSelected([]);
      doFetch();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "批量更新失败"));
    }
  };

  const handleRefresh = () => {
    if (view === "board") {
      doFetch();
    } else {
      actionRef.current?.reload();
    }
  };

  return (
    <SalesModuleShell
      title="商机管理"
      subtitle="以客户需求为入口，推动产品推荐、报价和订单转化"
      activeKey="opportunities"
      extra={<SalesQuickActions />}
    >
      <MetricBand
        items={[
          { title: "商机数", value: data.length, suffix: "个", prefix: <ThunderboltOutlined /> },
          { title: "活跃商机", value: stats.active, suffix: "个" },
          { title: "预计金额", value: stats.amount, prefix: "¥", precision: 0 },
          { title: "加权金额", value: stats.weightedAmount, prefix: "¥", precision: 0 },
          { title: "平均赢率", value: stats.avgWin, suffix: "%", precision: 1 },
          { title: "已超期", value: stats.overdue, suffix: "个" },
          { title: "14天内预计成交", value: stats.dueSoon, suffix: "个" },
          {
            title: "高风险",
            value: includeAi ? stats.atRisk : "-",
            suffix: includeAi ? "个" : undefined,
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
            <CustomerSelect value={customerId} onChange={setCustomerId} />
          </div>
          <Segmented
            value={view}
            onChange={(v) => setView(v as "board" | "list")}
            options={[
              {
                label: (
                  <>
                    <AppstoreOutlined /> 看板
                  </>
                ),
                value: "board",
              },
              {
                label: (
                  <>
                    <BarsOutlined /> 列表
                  </>
                ),
                value: "list",
              },
            ]}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 128 }}
            value={status}
            onChange={setStatus}
            options={STATUS_OPTIONS}
          />
          <Select
            placeholder="阶段"
            allowClear
            style={{ width: 140 }}
            value={stage}
            onChange={setStage}
            options={STAGE_OPTIONS}
          />
          <Select
            placeholder="负责人"
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: 140 }}
            value={assignedTo}
            onChange={setAssignedTo}
            options={ownerOptions}
          />
          <Button onClick={clearFilters}>清空筛选</Button>
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
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
              onChange={batchStage}
              options={STAGE_OPTIONS}
            />
          ) : null}
        </Space>
      </Card>

      {loading ? (
        <div style={{ textAlign: "center", padding: 60 }}>
          <Spin size="large" />
        </div>
      ) : view === "board" ? (
        <PipelineBoard opportunities={data} aiMap={aiMap} loading={loading} onRefresh={doFetch} />
      ) : (
        <Card size="small" title="商机清单" className="erp-table">
          <ProTable<Opportunity>
            actionRef={actionRef}
            rowKey="id"
            search={false}
            options={{ reload: true, density: true, setting: true }}
            rowClassName={erpRowClass}
            rowSelection={{
              selectedRowKeys: selected,
              onChange: (keys) => setSelected(keys as number[]),
            }}
            scroll={{ x: "max-content" }}
            params={tableParams}
            request={async (params) => {
              const queryParams: Record<string, unknown> = { page_size: 100 };
              if (params.status) queryParams.status = params.status;
              if (params.stage) queryParams.stage = params.stage;
              if (params.assigned_to) queryParams.assigned_to = params.assigned_to;
              if (params.customer_id) queryParams.customer_id = params.customer_id;
              if (params.q?.trim()) queryParams.q = params.q.trim();
              if (params.include_ai) queryParams.include_ai = true;
              const resp = await getOpportunities(queryParams);
              const list: Opportunity[] = resp.data.data.list || [];
              setData(list);
              setAiMap(
                params.include_ai
                  ? (resp.data.data as unknown as { ai?: Record<number, OpportunityAI> }).ai || {}
                  : {},
              );
              return { data: list, success: true, total: list.length };
            }}
            columns={
              [
                {
                  title: "#",
                  width: 45,
                  fixed: "left",
                  render: (_: unknown, __: Opportunity, index: number) => index + 1,
                },
                {
                  title: "商机",
                  dataIndex: "title",
                  ellipsis: true,
                  fixed: "left",
                  render: (value: string, record: Opportunity) => (
                    <div>
                      <div className="erp-cell-primary">
                        <Typography.Link
                          strong
                          onClick={() => navigate(`/sales/opportunities/${record.id}`)}
                        >
                          {value || `#${record.id}`}
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
                  sorter: (a: any, b: any) => (a.stage || "").localeCompare(b.stage || ""),
                  render: (value: string) => (
                    <StatusTag
                      status={value || "-"}
                      color="blue"
                      label={stageLabel[value] || value || "-"}
                    />
                  ),
                },
                {
                  title: "状态",
                  dataIndex: "status",
                  width: 100,
                  sorter: (a: any, b: any) => (a.status || "").localeCompare(b.status || ""),
                  render: (value: string) => (
                    <>
                      {statusDot(ERP_STATUS_DOT[value] || "#d9d9d9")}
                      <SalesStatusTag value={value} />
                    </>
                  ),
                },
                {
                  title: "金额",
                  dataIndex: "amount",
                  width: 130,
                  align: "right",
                  sorter: (a: any, b: any) => Number(a.amount || 0) - Number(b.amount || 0),
                  render: (value: number | null) => (
                    <Typography.Text strong>{money(value)}</Typography.Text>
                  ),
                },
                {
                  title: "加权金额",
                  key: "weighted_amount",
                  width: 130,
                  align: "right",
                  sorter: (a: any, b: any) =>
                    Number(a.amount || 0) * Number(a.win_probability || 0) -
                    Number(b.amount || 0) * Number(b.win_probability || 0),
                  render: (_: unknown, record: Opportunity) => (
                    <Typography.Text>
                      {money(
                        (Number(record.amount || 0) * Number(record.win_probability || 0)) / 100,
                      )}
                    </Typography.Text>
                  ),
                },
                {
                  title: "赢率",
                  dataIndex: "win_probability",
                  width: 150,
                  sorter: (a: any, b: any) =>
                    Number(a.win_probability || 0) - Number(b.win_probability || 0),
                  render: (value: number | null) => (
                    <Space direction="vertical" size={0} style={{ width: "100%" }}>
                      <Progress percent={Number(value || 0)} size="small" showInfo={false} />
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {value ?? 0}%
                      </Typography.Text>
                    </Space>
                  ),
                },
                {
                  title: "预计成交",
                  dataIndex: "expected_close_date",
                  width: 120,
                  sorter: (a: any, b: any) =>
                    (a.expected_close_date || "").localeCompare(b.expected_close_date || ""),
                  render: shortDate,
                },
                {
                  title: "负责人",
                  dataIndex: "assigned_to",
                  width: 120,
                  render: (value: string | null) => value || "-",
                },
                {
                  title: "来源",
                  dataIndex: "source",
                  width: 120,
                  ellipsis: true,
                  render: (value: string | null) => value || "-",
                },
                {
                  title: "最近更新",
                  dataIndex: "updated_at",
                  width: 120,
                  sorter: (a: any, b: any) =>
                    (a.updated_at || a.created_at || "").localeCompare(
                      b.updated_at || b.created_at || "",
                    ),
                  render: (value: string | null, record: Opportunity) =>
                    shortDate(value || record.created_at),
                },
                {
                  title: "风险",
                  key: "risk",
                  width: 90,
                  render: (_: unknown, record: Opportunity) => {
                    const risk = aiMap[record.id]?.risk_level;
                    if (!risk) return <Typography.Text type="secondary">未分析</Typography.Text>;
                    return (
                      <StatusTag
                        tone={
                          risk === "high" ? "danger" : risk === "medium" ? "warning" : "success"
                        }
                      >
                        {risk === "high" ? "高风险" : risk === "medium" ? "关注" : "正常"}
                      </StatusTag>
                    );
                  },
                },
                {
                  title: "操作",
                  width: 60,
                  fixed: "right",
                  render: (_: unknown, record: Opportunity) => {
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
                            onOk: async () => {
                              try {
                                await deleteOpportunity(record.id);
                                message.success("已删除");
                                handleRefresh();
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
              ] as ProColumns<Opportunity>[]
            }
            summary={(pageData: readonly Opportunity[]) => {
              const totalAmt = pageData.reduce((s, r) => s + Number(r.amount || 0), 0);
              const weightedAmt = pageData.reduce(
                (s, r) => s + (Number(r.amount || 0) * Number(r.win_probability || 0)) / 100,
                0,
              );
              return (
                <ProTable.Summary.Row>
                  <ProTable.Summary.Cell index={0} colSpan={2}>
                    合计 <Typography.Text strong>{pageData.length} 项</Typography.Text>
                  </ProTable.Summary.Cell>
                  <ProTable.Summary.Cell index={2} colSpan={2} />
                  <ProTable.Summary.Cell index={4} align="right">
                    <Typography.Text strong>{money(totalAmt)}</Typography.Text>
                  </ProTable.Summary.Cell>
                  <ProTable.Summary.Cell index={5} align="right">
                    <Typography.Text strong>{money(weightedAmt)}</Typography.Text>
                  </ProTable.Summary.Cell>
                  <ProTable.Summary.Cell index={6} colSpan={7} />
                </ProTable.Summary.Row>
              );
            }}
          />
        </Card>
      )}

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={8}>
          <Card size="small">
            <Typography.Text type="secondary">客户推进</Typography.Text>
            <Typography.Paragraph style={{ marginBottom: 0 }}>
              优先处理大额、临近预计成交日期且未进入报价阶段的商机。
            </Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small">
            <Typography.Text type="secondary">产品联动</Typography.Text>
            <Typography.Paragraph style={{ marginBottom: 0 }}>
              在商机表单选择客户后，用产品选择器把推荐产品沉淀到报价。
            </Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small">
            <Typography.Text type="secondary">成交闭环</Typography.Text>
            <Typography.Paragraph style={{ marginBottom: 0 }}>
              商机进入报价中后，从商机直接创建报价并转订单。
            </Typography.Paragraph>
          </Card>
        </Col>
      </Row>
    </SalesModuleShell>
  );
}
