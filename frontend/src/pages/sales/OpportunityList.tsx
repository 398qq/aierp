import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Col, Dropdown, Input, Modal, Progress, Row, Segmented, Select, Space, Spin, Switch, Table, Tag, Typography, message } from "antd";
import type { MenuProps } from "antd";
import { AppstoreOutlined, BarsOutlined, DeleteOutlined, EditOutlined, EllipsisOutlined, EyeOutlined, FileTextOutlined, PlusOutlined, ReloadOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { batchUpdateOpportunities, deleteOpportunity, getOpportunities } from "../../api";
import PipelineBoard from "../../components/sales/PipelineBoard";
import type { Opportunity, OpportunityAI } from "../../types";
import { CustomerLink, CustomerSelect, ErpExportButton, MetricBand, SalesModuleShell, SalesQuickActions, SalesStatusTag, erpRowClass, money, shortDate, stageLabel, statusDot, ERP_STATUS_DOT } from "./salesUi";

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
  const [data, setData] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | undefined>();
  const [stage, setStage] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [searchText, setSearchText] = useState("");
  const [q, setQ] = useState("");
  const [view, setView] = useState<"board" | "list">("board");
  const [includeAi, setIncludeAi] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [aiMap, setAiMap] = useState<Record<number, OpportunityAI>>({});
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page_size: 100 };
      if (status) params.status = status;
      if (stage) params.stage = stage;
      if (customerId) params.customer_id = customerId;
      if (q.trim()) params.q = q.trim();
      if (includeAi) params.include_ai = true;
      const resp = await getOpportunities(params);
      setData(resp.data.data.list || []);
      setAiMap(includeAi ? ((resp.data.data as unknown as { ai?: Record<number, OpportunityAI> }).ai || {}) : {});
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [status, stage, customerId, q, includeAi]);

  const stats = useMemo(() => {
    const amount = data.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    const weightedAmount = data.reduce((sum, item) => sum + Number(item.amount || 0) * Number(item.win_probability || 0) / 100, 0);
    const avgWin = data.length ? data.reduce((sum, item) => sum + Number(item.win_probability || 0), 0) / data.length : 0;
    const active = data.filter((item) => item.status === "active").length;
    const dueSoon = data.filter((item) => {
      if (!item.expected_close_date || item.status !== "active") return false;
      const due = new Date(item.expected_close_date).getTime();
      if (Number.isNaN(due)) return false;
      const diffDays = Math.ceil((due - Date.now()) / (24 * 60 * 60 * 1000));
      return diffDays >= 0 && diffDays <= 14;
    }).length;
    const atRisk = includeAi ? Object.values(aiMap).filter((item) => item.risk_level === "high").length : 0;
    return { amount, weightedAmount, avgWin, active, dueSoon, atRisk };
  }, [aiMap, data, includeAi]);

  const clearFilters = () => {
    setStatus(undefined);
    setStage(undefined);
    setCustomerId(undefined);
    setSearchText("");
    setQ("");
  };

  const exportData = useMemo(() =>
    data.map((r) => ({
      id: r.id,
      title: r.title,
      customer_id: r.customer_id,
      stage: r.stage ? (stageLabel[r.stage] || r.stage) : "",
      status: STATUS_OPTIONS.find((s) => s.value === r.status)?.label || r.status,
      amount: r.amount || 0,
      win_probability: r.win_probability ?? 0,
      expected_close_date: r.expected_close_date?.slice(0, 10) || "",
      assigned_to: r.assigned_to || "",
      source: r.source || "",
    })),
  [data]);

  const batchStage = async (nextStage: string) => {
    if (!selected.length) return;
    try {
      await batchUpdateOpportunities(selected, nextStage);
      message.success("阶段已更新");
      setSelected([]);
      load();
    } catch {
      message.error("批量更新失败");
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
          { title: "14天内预计成交", value: stats.dueSoon, suffix: "个" },
          { title: "高风险", value: includeAi ? stats.atRisk : "-", suffix: includeAi ? "个" : undefined },
        ]}
      />

      <Card
        size="small"
        style={{ marginBottom: 16 }}
        title={<Typography.Text strong>商机筛选</Typography.Text>}
        extra={(
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/opportunities/new")}>新建商机</Button>
          </Space>
        )}
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
              { label: <><AppstoreOutlined /> 看板</>, value: "board" },
              { label: <><BarsOutlined /> 列表</>, value: "list" },
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
              { key: "win_probability", title: "赢率(%)" },
              { key: "expected_close_date", title: "预计成交" },
              { key: "assigned_to", title: "负责人" },
              { key: "source", title: "来源" },
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
        <PipelineBoard opportunities={data} aiMap={aiMap} loading={loading} onRefresh={load} />
      ) : (
        <Card size="small" title="商机清单">
          <Table
            rowKey="id"
            dataSource={data}
            rowClassName={erpRowClass}
            rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
            scroll={{ x: "max-content" }}
            columns={[
              {
                title: "#", width: 45, fixed: "left",
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
                      <Typography.Link strong onClick={() => navigate(`/sales/opportunities/${record.id}`)}>{value || `#${record.id}`}</Typography.Link>
                    </div>
                    <div className="erp-cell-secondary"><CustomerLink id={record.customer_id} /></div>
                  </div>
                ),
              },
              {
                title: "阶段",
                dataIndex: "stage",
                width: 110,
                sorter: (a, b) => (a.stage || "").localeCompare(b.stage || ""),
                render: (value: string) => (
                  <Tag color="blue" style={{ margin: 0 }}>{stageLabel[value] || value || "-"}</Tag>
                ),
              },
              {
                title: "状态",
                dataIndex: "status",
                width: 100,
                sorter: (a, b) => (a.status || "").localeCompare(b.status || ""),
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
                sorter: (a, b) => Number(a.amount || 0) - Number(b.amount || 0),
                render: (value: number | null) => <Typography.Text strong>{money(value)}</Typography.Text>,
              },
              {
                title: "赢率",
                dataIndex: "win_probability",
                width: 150,
                sorter: (a, b) => Number(a.win_probability || 0) - Number(b.win_probability || 0),
                render: (value: number | null) => (
                  <Space direction="vertical" size={0} style={{ width: "100%" }}>
                    <Progress percent={Number(value || 0)} size="small" showInfo={false} />
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{value ?? 0}%</Typography.Text>
                  </Space>
                ),
              },
              { title: "预计成交", dataIndex: "expected_close_date", width: 120, sorter: (a, b) => (a.expected_close_date || "").localeCompare(b.expected_close_date || ""), render: shortDate },
              { title: "负责人", dataIndex: "assigned_to", width: 120, render: (value: string | null) => value || "-" },
              { title: "来源", dataIndex: "source", width: 120, ellipsis: true, render: (value: string | null) => value || "-" },
              {
                title: "操作", width: 60, fixed: "right",
                render: (_: unknown, record: Opportunity) => {
                  const items: MenuProps["items"] = [
                    { key: "view", icon: <EyeOutlined />, label: "查看详情", onClick: () => navigate(`/sales/opportunities/${record.id}`) },
                    { key: "quote", icon: <FileTextOutlined />, label: "创建报价", onClick: () => navigate(`/sales/quotations/new?customer_id=${record.customer_id}&opportunity_id=${record.id}`) },
                    { type: "divider" as const },
                    { key: "delete", icon: <DeleteOutlined />, label: "删除", danger: true, onClick: () => {
                      Modal.confirm({ title: "确定删除?", content: `删除商机 #${record.id}？`, onOk: async () => {
                        try { await deleteOpportunity(record.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                      }});
                    }},
                  ];
                  return (
                    <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
                      <Button size="small" icon={<EllipsisOutlined />} type="text" />
                    </Dropdown>
                  );
                },
              },
            ]}
            summary={(pageData: readonly Opportunity[]) => {
              const totalAmt = pageData.reduce((s, r) => s + Number(r.amount || 0), 0);
              return (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0}>合计</Table.Summary.Cell>
                  <Table.Summary.Cell index={1}><Typography.Text strong>{pageData.length} 项</Typography.Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={2} colSpan={2} />
                  <Table.Summary.Cell index={4} align="right"><Typography.Text strong>{money(totalAmt)}</Typography.Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={5} colSpan={5} />
                </Table.Summary.Row>
              );
            }}
            pagination={{ pageSize: 20, showSizeChanger: false }}
          />
        </Card>
      )}

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={8}>
          <Card size="small">
            <Typography.Text type="secondary">客户推进</Typography.Text>
            <Typography.Paragraph style={{ marginBottom: 0 }}>优先处理大额、临近预计成交日期且未进入报价阶段的商机。</Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small">
            <Typography.Text type="secondary">产品联动</Typography.Text>
            <Typography.Paragraph style={{ marginBottom: 0 }}>在商机表单选择客户后，用产品选择器把推荐产品沉淀到报价。</Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small">
            <Typography.Text type="secondary">成交闭环</Typography.Text>
            <Typography.Paragraph style={{ marginBottom: 0 }}>商机进入报价中后，从商机直接创建报价并转订单。</Typography.Paragraph>
          </Card>
        </Col>
      </Row>
    </SalesModuleShell>
  );
}
