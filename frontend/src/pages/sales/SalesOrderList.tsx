import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Input, Popconfirm, Select, Space, Switch, Table, Typography, message } from "antd";
import { CarOutlined, DeleteOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { batchDeleteSalesOrders, convertSalesOrderToDelivery, deleteSalesOrder, getSalesOrders } from "../../api";
import AIInlineBadge from "../../components/sales/AIInlineBadge";
import type { SalesOrder } from "../../types";
import { CustomerLink, CustomerSelect, MetricBand, SalesModuleShell, SalesQuickActions, SalesStatusTag, money, shortDate } from "./salesUi";

export default function SalesOrderList() {
  const [data, setData] = useState<SalesOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [searchText, setSearchText] = useState("");
  const [q, setQ] = useState("");
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, { delivery_risk?: string; flag?: string }>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      if (customerId) params.customer_id = customerId;
      if (q.trim()) params.q = q.trim();
      if (includeAi) params.include_ai = true;
      const resp = await getSalesOrders(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      setAiMap(includeAi ? ((resp.data.data as unknown as { ai?: Record<number, { delivery_risk?: string; flag?: string }> }).ai || {}) : {});
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [page, status, customerId, q, includeAi]);

  const stats = useMemo(() => {
    const amount = data.reduce((sum, item) => sum + Number(item.total_amount || 0), 0);
    const confirmed = data.filter((item) => item.status === "confirmed").length;
    const pending = data.filter((item) => item.status === "pending").length;
    const itemCount = data.reduce((sum, item) => sum + (item.items?.length || 0), 0);
    return { amount, confirmed, pending, itemCount };
  }, [data]);

  const handleBatchDelete = async () => {
    try {
      await batchDeleteSalesOrders(selected);
      message.success("已批量删除");
      setSelected([]);
      load();
    } catch {
      message.error("删除失败");
    }
  };

  return (
    <SalesModuleShell
      title="销售订单"
      subtitle="承接报价成交，管理产品明细、交付风险和执行状态"
      activeKey="orders"
      extra={<SalesQuickActions />}
    >
      <MetricBand
        items={[
          { title: "订单数", value: total, suffix: "单" },
          { title: "本页金额", value: stats.amount, prefix: "¥", precision: 0 },
          { title: "待确认", value: stats.pending, suffix: "单" },
          { title: "已确认", value: stats.confirmed, suffix: "单" },
          { title: "产品行", value: stats.itemCount, suffix: "项" },
        ]}
      />

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/orders/new")}>新建订单</Button>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Input.Search
            allowClear
            placeholder="搜索客户 / 订单号 / 产品"
            value={searchText}
            onChange={(event) => {
              setSearchText(event.target.value);
              if (!event.target.value) {
                setPage(1);
                setQ("");
              }
            }}
            onSearch={(value) => {
              setPage(1);
              setQ(value);
            }}
            style={{ width: 260 }}
          />
          <div style={{ width: 260 }}>
            <CustomerSelect value={customerId} onChange={(next) => { setCustomerId(next); setPage(1); }} />
          </div>
          {selected.length > 0 ? (
            <Popconfirm title="确定批量删除?" onConfirm={handleBatchDelete}>
              <Button danger icon={<DeleteOutlined />}>删除 {selected.length}</Button>
            </Popconfirm>
          ) : null}
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 128 }}
            value={status}
            onChange={(next) => {
              setPage(1);
              setStatus(next);
            }}
            options={[
              { value: "pending", label: "待确认" },
              { value: "confirmed", label: "已确认" },
              { value: "shipped", label: "已发货" },
              { value: "delivered", label: "已完成" },
            ]}
          />
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </Space>
      </Card>

      <Card>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={data}
          rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
          columns={[
            {
              title: "订单",
              dataIndex: "order_no",
              minWidth: 220,
              render: (value: string | null, record: SalesOrder) => (
                <Space direction="vertical" size={0}>
                  <a onClick={() => navigate(`/sales/orders/${record.id}`)}>{value || `#${record.id}`}</a>
                  <Space size={8}>
                    <CustomerLink id={record.customer_id} />
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>产品行 {record.items?.length || 0}</Typography.Text>
                  </Space>
                </Space>
              ),
            },
            { title: "金额", dataIndex: "total_amount", width: 130, render: money },
            { title: "状态", dataIndex: "status", width: 100, render: (value: string) => <SalesStatusTag value={value} /> },
            { title: "下单", dataIndex: "order_date", width: 120, render: shortDate },
            { title: "交付", dataIndex: "delivery_date", width: 120, render: shortDate },
            {
              title: "AI",
              width: 100,
              render: (_: unknown, record: SalesOrder) => <AIInlineBadge riskLevel={aiMap[record.id]?.delivery_risk} flag={aiMap[record.id]?.flag} />,
            },
            {
              title: "操作",
              width: 230,
              render: (_: unknown, record: SalesOrder) => (
                <Space size="small">
                  <Button size="small" onClick={() => navigate(`/sales/orders/${record.id}`)}>详情</Button>
                  <Popconfirm title="转为发货单?" onConfirm={async () => {
                    try {
                      await convertSalesOrderToDelivery(record.id);
                      message.success("已转为发货单");
                      load();
                    } catch {
                      message.error("转换失败");
                    }
                  }}>
                    <Button size="small" type="primary" icon={<CarOutlined />}>发货</Button>
                  </Popconfirm>
                  <Popconfirm title="确定删除?" onConfirm={async () => {
                    try {
                      await deleteSalesOrder(record.id);
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
