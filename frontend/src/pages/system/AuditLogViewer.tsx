/** AuditLogViewer — field change history (Stage 11 Day 3).

Three tabs:
- Recent (last N across all tables)
- Filtered (by table/record/field/actor)
- Summary (aggregated counts)

Used by system admin / owner to answer "who changed what when".
*/

import { useEffect, useState } from "react";
import { Table, Tabs, Form, Input, InputNumber, Select, Space, Button, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";

import { PageHeader } from "@/ui/PageHeader";
import { ErrorBoundary } from "@/ui/ErrorBoundary";

import {
  listFieldChanges,
  recentFieldChanges,
  fieldChangesSummary,
  type FieldChange,
  type AuditSummary,
} from "@/api/audit";

const TABLE_OPTIONS = [
  { value: "customer", label: "客户 (customer)" },
  { value: "sales_order", label: "销售订单 (sales_order)" },
  { value: "product", label: "产品 (product)" },
  { value: "supplier", label: "供应商 (supplier)" },
  { value: "commission", label: "佣金 (commission)" },
  { value: "invoice", label: "发票 (invoice)" },
];

function RecentTab() {
  const [items, setItems] = useState<FieldChange[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    recentFieldChanges(50)
      .then((res) => setItems(res.data.items))
      .finally(() => setLoading(false));
  }, []);

  const columns: ColumnsType<FieldChange> = [
    { title: "时间", dataIndex: "changed_at", width: 170 },
    { title: "表", dataIndex: "table_name", width: 110,
      render: (t) => <Tag color="blue">{t}</Tag> },
    { title: "记录 ID", dataIndex: "record_id", width: 90 },
    { title: "字段", dataIndex: "field_name", width: 110,
      render: (f) => <Tag>{f}</Tag> },
    { title: "旧值", dataIndex: "old_value", ellipsis: true },
    { title: "新值", dataIndex: "new_value", ellipsis: true,
      render: (v) => <span style={{ color: "#1677ff" }}>{v}</span> },
    { title: "操作人", dataIndex: "actor", width: 100 },
  ];

  return (
    <Table
      size="small"
      rowKey="id"
      loading={loading}
      dataSource={items}
      columns={columns}
      pagination={{ pageSize: 20 }}
    />
  );
}

function FilteredTab() {
  const [form] = Form.useForm();
  const [items, setItems] = useState<FieldChange[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  const onSearch = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const res = await listFieldChanges({
        ...values,
        page,
        page_size: 20,
      });
      setItems(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    onSearch({ days_back: 30 });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const columns: ColumnsType<FieldChange> = [
    { title: "时间", dataIndex: "changed_at", width: 170 },
    { title: "表", dataIndex: "table_name", width: 110,
      render: (t) => <Tag color="blue">{t}</Tag> },
    { title: "记录 ID", dataIndex: "record_id", width: 90 },
    { title: "字段", dataIndex: "field_name", width: 110,
      render: (f) => <Tag>{f}</Tag> },
    { title: "旧值", dataIndex: "old_value", ellipsis: true,
      render: (v) => <span style={{ color: "#999" }}>{v ?? "—"}</span> },
    { title: "新值", dataIndex: "new_value", ellipsis: true,
      render: (v) => <span style={{ color: "#1677ff" }}>{v ?? "—"}</span> },
    { title: "操作人", dataIndex: "actor", width: 100 },
  ];

  return (
    <>
      <Form
        form={form}
        layout="inline"
        onFinish={onSearch}
        style={{ marginBottom: 16 }}
      >
        <Form.Item name="table_name" label="表">
          <Select allowClear style={{ width: 180 }}
            options={TABLE_OPTIONS} placeholder="不限" />
        </Form.Item>
        <Form.Item name="record_id" label="记录 ID">
          <InputNumber min={1} style={{ width: 100 }} />
        </Form.Item>
        <Form.Item name="field_name" label="字段">
          <Input placeholder="email" allowClear style={{ width: 120 }} />
        </Form.Item>
        <Form.Item name="actor" label="操作人">
          <Input placeholder="alice" allowClear style={{ width: 100 }} />
        </Form.Item>
        <Form.Item name="days_back" label="天数" initialValue={30}>
          <InputNumber min={1} max={365} style={{ width: 80 }} />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">查询</Button>
            <Button onClick={() => { form.resetFields(); onSearch({ days_back: 30 }); }}>
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>
      <Table
        size="small"
        rowKey="id"
        loading={loading}
        dataSource={items}
        columns={columns}
        pagination={{
          current: page,
          pageSize: 20,
          total,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 条`,
        }}
      />
    </>
  );
}

function SummaryTab() {
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(30);

  useEffect(() => {
    setLoading(true);
    fieldChangesSummary(days)
      .then((res) => setSummary(res.data))
      .finally(() => setLoading(false));
  }, [days]);

  if (!summary) return <div style={{ padding: 24 }}>加载中...</div>;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <span>统计窗口：</span>
        <Select
          value={days}
          onChange={setDays}
          style={{ width: 120 }}
          options={[
            { value: 7, label: "7 天" },
            { value: 30, label: "30 天" },
            { value: 90, label: "90 天" },
          ]}
        />
      </Space>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <div>
          <h3>按表</h3>
          <Table
            size="small"
            loading={loading}
            rowKey="name"
            pagination={false}
            dataSource={Object.entries(summary.by_table).map(([name, count]) => ({
              name, count,
            }))}
            columns={[
              { title: "表", dataIndex: "name", render: (n) => <Tag color="blue">{n}</Tag> },
              { title: "变更次数", dataIndex: "count" },
            ]}
          />
        </div>
        <div>
          <h3>按操作人</h3>
          <Table
            size="small"
            loading={loading}
            rowKey="name"
            pagination={false}
            dataSource={Object.entries(summary.by_actor).map(([name, count]) => ({
              name, count,
            }))}
            columns={[
              { title: "操作人", dataIndex: "name" },
              { title: "变更次数", dataIndex: "count" },
            ]}
          />
        </div>
      </div>
      <h3 style={{ marginTop: 24 }}>最常变动的字段（Top 20）</h3>
      <Table
        size="small"
        rowKey={(r) => `${r.table}.${r.field}`}
        loading={loading}
        pagination={false}
        dataSource={summary.top_fields}
        columns={[
          { title: "表.字段", render: (_, r) => <span><Tag color="blue">{r.table}</Tag>.<Tag>{r.field}</Tag></span> },
          { title: "变更次数", dataIndex: "count" },
        ]}
      />
    </div>
  );
}

export default function AuditLogViewer() {
  return (
    <ErrorBoundary>
      <PageHeader
        title="审计日志"
        description="字段级变更追踪 — 谁在什么时候改了什么"
      />
      <Tabs
        defaultActiveKey="recent"
        items={[
          { key: "recent", label: "最近变更", children: <RecentTab /> },
          { key: "filtered", label: "按条件查询", children: <FilteredTab /> },
          { key: "summary", label: "汇总统计", children: <SummaryTab /> },
        ]}
      />
    </ErrorBoundary>
  );
}
