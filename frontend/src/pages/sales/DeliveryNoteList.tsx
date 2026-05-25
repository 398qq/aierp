import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Popconfirm, Select, Space, Switch, Table, Typography, message } from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { batchDeleteDeliveryNotes, deleteDeliveryNote, getDeliveryNotes } from "../../api";
import AIInlineBadge from "../../components/sales/AIInlineBadge";
import type { DeliveryNote } from "../../types";
import { CustomerLink, CustomerSelect, MetricBand, SalesModuleShell, SalesStatusTag, shortDate } from "./salesUi";

export default function DeliveryNoteList() {
  const [data, setData] = useState<DeliveryNote[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, { completion_risk?: string; flag?: string }>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      if (customerId) params.customer_id = customerId;
      if (includeAi) params.include_ai = true;
      const resp = await getDeliveryNotes(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      setAiMap(includeAi ? ((resp.data.data as unknown as { ai?: Record<number, { completion_risk?: string; flag?: string }> }).ai || {}) : {});
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, status, customerId, includeAi]);

  const stats = useMemo(() => {
    const pending = data.filter((item) => item.status === "pending").length;
    const shipped = data.filter((item) => item.status === "shipped").length;
    const linkedCustomers = new Set(data.map((item) => item.customer_id).filter(Boolean)).size;
    const lineCount = data.reduce((sum, item) => sum + (item.items?.length || 0), 0);
    return { pending, shipped, linkedCustomers, lineCount };
  }, [data]);

  const handleBatchDelete = async () => {
    try {
      await batchDeleteDeliveryNotes(selected);
      message.success("已批量删除");
      setSelected([]);
      load();
    } catch {
      message.error("删除失败");
    }
  };

  return (
    <SalesModuleShell
      title="发货管理"
      subtitle="按销售订单执行发货，客户关联跟随订单，支持客户筛选和发货状态追踪"
      activeKey="delivery"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/delivery-notes/new")}>新增发货单</Button>}
    >
      <MetricBand items={[
        { title: "当前发货单", value: total },
        { title: "待发货", value: stats.pending },
        { title: "已发货", value: stats.shipped },
        { title: "关联客户", value: stats.linkedCustomers },
        { title: "发货行数", value: stats.lineCount },
      ]} />

      <Card>
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 140 }}
            value={status}
            onChange={(next) => { setStatus(next); setPage(1); }}
            options={[
              { value: "pending", label: "待发货" },
              { value: "shipped", label: "已发货" },
              { value: "delivered", label: "已签收" },
              { value: "returned", label: "已退回" },
            ]}
          />
          <div style={{ width: 280 }}>
            <CustomerSelect value={customerId} onChange={(next) => { setCustomerId(next); setPage(1); }} />
          </div>
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
          {selected.length > 0 && (
            <Popconfirm title="确定批量删除?" onConfirm={handleBatchDelete}>
              <Button danger icon={<DeleteOutlined />}>删除({selected.length})</Button>
            </Popconfirm>
          )}
        </Space>

        <Table
          rowKey="id"
          loading={loading}
          dataSource={data}
          rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
          columns={[
            {
              title: "发货单",
              dataIndex: "delivery_no",
              width: 180,
              render: (value: string, record: DeliveryNote) => (
                <Space direction="vertical" size={0}>
                  <Typography.Link onClick={() => navigate(`/sales/delivery-notes/${record.id}`)}>{value || `#${record.id}`}</Typography.Link>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>订单 #{record.sales_order_id}</Typography.Text>
                </Space>
              ),
            },
            { title: "客户", dataIndex: "customer_id", width: 180, render: (value: number) => <CustomerLink id={value} /> },
            { title: "状态", dataIndex: "status", width: 110, render: (value: string) => <SalesStatusTag value={value} /> },
            { title: "发货日期", dataIndex: "delivery_date", width: 120, render: shortDate },
            { title: "签收日期", dataIndex: "received_date", width: 120, render: shortDate },
            { title: "明细", width: 90, render: (_: unknown, record: DeliveryNote) => record.items?.length || 0 },
            {
              title: "AI",
              width: 90,
              render: (_: unknown, record: DeliveryNote) => <AIInlineBadge riskLevel={aiMap[record.id]?.completion_risk} flag={aiMap[record.id]?.flag} />,
            },
            {
              title: "操作",
              width: 140,
              render: (_: unknown, record: DeliveryNote) => (
                <Space size="small">
                  <Button size="small" onClick={() => navigate(`/sales/delivery-notes/${record.id}`)}>详情</Button>
                  <Popconfirm title="确定删除?" onConfirm={async () => {
                    try {
                      await deleteDeliveryNote(record.id);
                      message.success("已删除");
                      load();
                    } catch {
                      message.error("删除失败");
                    }
                  }}>
                    <Button size="small" danger>删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
          pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (count) => `共 ${count} 条` }}
        />
      </Card>
    </SalesModuleShell>
  );
}
