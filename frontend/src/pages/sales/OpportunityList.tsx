import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Col, Row, Segmented, Select, Space, Spin, Switch, Table, Tag, Typography, message } from "antd";
import { FileTextOutlined, PlusOutlined, ReloadOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { batchUpdateOpportunities, getOpportunities } from "../../api";
import PipelineBoard from "../../components/sales/PipelineBoard";
import type { Opportunity, OpportunityAI } from "../../types";
import { CustomerLink, MetricBand, SalesModuleShell, SalesQuickActions, money, shortDate, stageLabel } from "./salesUi";

const STAGE_OPTIONS = [
  { value: "lead", label: "线索" },
  { value: "qualified", label: "需求确认" },
  { value: "proposal", label: "报价中" },
  { value: "negotiation", label: "谈判" },
];

export default function OpportunityList() {
  const [data, setData] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | undefined>();
  const [stage, setStage] = useState<string | undefined>();
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
  }, [status, stage, includeAi]);

  const stats = useMemo(() => {
    const amount = data.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    const highValue = data.filter((item) => Number(item.amount || 0) >= 100000).length;
    const avgWin = data.length ? data.reduce((sum, item) => sum + Number(item.win_probability || 0), 0) / data.length : 0;
    return { amount, highValue, avgWin };
  }, [data]);

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
          { title: "预计金额", value: stats.amount, prefix: "¥", precision: 0 },
          { title: "大额商机", value: stats.highValue, suffix: "个" },
          { title: "平均赢率", value: stats.avgWin, suffix: "%", precision: 1 },
        ]}
      />

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/opportunities/new")}>新建商机</Button>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Segmented
            value={view}
            onChange={(v) => setView(v as "board" | "list")}
            options={[
              { label: "看板", value: "board" },
              { label: "列表", value: "list" },
            ]}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 128 }}
            value={status}
            onChange={setStatus}
            options={[
              { value: "active", label: "活跃" },
              { value: "won", label: "已赢单" },
              { value: "lost", label: "已输单" },
            ]}
          />
          <Select
            placeholder="阶段"
            allowClear
            style={{ width: 140 }}
            value={stage}
            onChange={setStage}
            options={STAGE_OPTIONS}
          />
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
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
        <Card>
          <Table
            rowKey="id"
            dataSource={data}
            rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
            columns={[
              {
                title: "商机",
                dataIndex: "title",
                ellipsis: true,
                render: (value: string, record: Opportunity) => (
                  <Space direction="vertical" size={0}>
                    <a onClick={() => navigate(`/sales/opportunities/${record.id}`)}>{value}</a>
                    <CustomerLink id={record.customer_id} />
                  </Space>
                ),
              },
              { title: "阶段", dataIndex: "stage", width: 120, render: (value: string) => <Tag color="blue">{stageLabel[value] || value || "-"}</Tag> },
              { title: "金额", dataIndex: "amount", width: 120, render: money },
              { title: "赢率", dataIndex: "win_probability", width: 110, render: (value: number | null) => `${value ?? 0}%` },
              { title: "预计成交", dataIndex: "expected_close_date", width: 120, render: shortDate },
              { title: "负责人", dataIndex: "assigned_to", width: 120, render: (value: string | null) => value || "-" },
              {
                title: "操作",
                width: 170,
                render: (_: unknown, record: Opportunity) => (
                  <Space size="small">
                    <Button size="small" onClick={() => navigate(`/sales/opportunities/${record.id}`)}>详情</Button>
                    <Button size="small" icon={<FileTextOutlined />} onClick={() => navigate(`/sales/quotations/new?customer_id=${record.customer_id}&opportunity_id=${record.id}`)}>报价</Button>
                  </Space>
                ),
              },
            ]}
            pagination={false}
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
