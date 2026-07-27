import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "@/router";
import { Button, Card, Dropdown, Input, Modal, Popconfirm, Select, Space, Switch, Tag, Typography, message } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import type { MenuProps } from "antd";
import { DeleteOutlined, EditOutlined, EllipsisOutlined, EyeOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { batchDeleteDeliveryNotes, deleteDeliveryNote, getDeliveryNotes, getPayments, getApiErrorMessage } from "../../api";
import AIInlineBadge from "../../components/sales/AIInlineBadge";
import type { DeliveryNote, PaymentRecord } from "../../types";
import { Link } from "@/router";
import { CustomerLink, CustomerSelect, ErpExportButton, MetricBand, SalesModuleShell, SalesStatusTag, erpRowClass, money, shortDate, statusDot, ERP_STATUS_DOT } from "./salesUi";

const PAYMENT_STATUS: Record<string, { color: string; label: string }> = {
  completed: { color: "green", label: "已收款" },
  partial: { color: "orange", label: "部分收款" },
  none: { color: "default", label: "未收款" },
};

export default function DeliveryNoteList() {
  const [data, setData] = useState<DeliveryNote[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [status, setStatus] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [searchText, setSearchText] = useState("");
  const [q, setQ] = useState("");
  const [paymentMap, setPaymentMap] = useState<Record<number, { status: string; total: number; received: number }>>({});
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, { completion_risk?: string; flag?: string }>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (status) params.status = status;
      if (customerId) params.customer_id = customerId;
      if (q.trim()) params.q = q.trim();
      if (includeAi) params.include_ai = true;

      // 并行请求：发货单 + 回款列表
      const [resp, payResp] = await Promise.all([
        getDeliveryNotes(params),
        getPayments({ page: 1, page_size: 100 }),
      ]);
      const notes = resp.data.data.list || [];
      setData(notes);
      setTotal(resp.data.data.total || 0);
      setAiMap(includeAi ? ((resp.data.data as unknown as { ai?: Record<number, { completion_risk?: string; flag?: string }> }).ai || {}) : {});

      const dnIds = notes.map((n: DeliveryNote) => n.id);
      if (dnIds.length > 0) {
        const allPayments: PaymentRecord[] = payResp.data.data.list || [];
        const map: Record<number, { status: string; total: number; received: number }> = {};
        for (const dnId of dnIds) {
          const related = allPayments.filter((p) => p.delivery_note_id === dnId);
          if (related.length === 0) {
            map[dnId] = { status: "none", total: 0, received: 0 };
          } else {
            const totalAmt = related.reduce((s, p) => s + p.amount, 0);
            const receivedAmt = related.filter((p) => p.status === "completed").reduce((s, p) => s + p.amount, 0);
            const allCompleted = related.every((p) => p.status === "completed");
            map[dnId] = { status: allCompleted ? "completed" : "partial", total: totalAmt, received: receivedAmt };
          }
        }
        setPaymentMap(map);
      }
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载失败")); } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, pageSize, status, customerId, q, includeAi]);

  const stats = useMemo(() => {
    const pending = data.filter((item) => item.status === "pending").length;
    const shipped = data.filter((item) => item.status === "shipped").length;
    const linkedCustomers = new Set(data.map((item) => item.customer_id).filter(Boolean)).size;
    const lineCount = data.reduce((sum, item) => sum + (item.items?.length || 0), 0);
    return { pending, shipped, linkedCustomers, lineCount };
  }, [data]);

  const exportData = useMemo(() =>
    data.map((r) => ({
      delivery_no: r.delivery_no || `#${r.id}`,
      sales_order_id: r.sales_order_id,
      customer_id: r.customer_id,
      status: r.status,
      delivery_date: r.delivery_date?.slice(0, 10) || "",
      received_date: r.received_date?.slice(0, 10) || "",
      items_count: r.items?.length || 0,
      payment_status: paymentMap[r.id] ? (PAYMENT_STATUS[paymentMap[r.id].status]?.label || paymentMap[r.id].status) : "",
    })),
  [data, paymentMap]);

  const handleBatchDelete = async () => {
    try {
      await batchDeleteDeliveryNotes(selected);
      message.success("已批量删除");
      setSelected([]);
      load();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
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

      <Card className="erp-table">
        <Space style={{ marginBottom: 16 }} wrap>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Input.Search
            allowClear
            placeholder="搜索客户 / 发货单 / 订单 / 产品"
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
            style={{ width: 280 }}
          />
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
          <ErpExportButton
            data={exportData}
            columns={[
              { key: "delivery_no", title: "发货单" },
              { key: "sales_order_id", title: "订单号" },
              { key: "customer_id", title: "客户ID" },
              { key: "status", title: "状态" },
              { key: "delivery_date", title: "发货日期" },
              { key: "received_date", title: "签收日期" },
              { key: "items_count", title: "明细行数" },
              { key: "payment_status", title: "回款状态" },
            ]}
            filename="delivery_notes_export.csv"
          />
        </Space>

        <ProTable search={false} options={false}
          rowKey="id"
          loading={loading}
          dataSource={data}
          rowClassName={erpRowClass}
          rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
          scroll={{ x: "max-content" }}
            columns={[
            {
              title: "#", width: 45, fixed: "left",
              render: (_: unknown, __: DeliveryNote, index: number) => (page - 1) * 20 + index + 1,
            },
            {
              title: "发货单",
              dataIndex: "delivery_no",
              width: 180,
              fixed: "left",
              render: (value: string, record: DeliveryNote) => (
                <div>
                  <div className="erp-cell-primary">
                    <Typography.Link strong onClick={() => navigate(`/sales/delivery-notes/${record.id}`)}>{value || `#${record.id}`}</Typography.Link>
                  </div>
                  <div className="erp-cell-secondary">订单 #{record.sales_order_id}</div>
                </div>
              ),
            },
            { title: "客户", dataIndex: "customer_name", width: 180, render: (v: string | null | undefined, r: DeliveryNote) =>
              v ? <Link to={`/customers/${r.customer_id}`}>{v}</Link> : <CustomerLink id={r.customer_id} /> },
            {
              title: "状态", dataIndex: "status", width: 110,
              sorter: (a: any, b: any) => (a.status || "").localeCompare(b.status || ""),
              render: (value: string) => (
                <>
                  {statusDot(ERP_STATUS_DOT[value] || "#d9d9d9")}
                  <SalesStatusTag value={value} />
                </>
              ),
            },
            { title: "发货日期", dataIndex: "delivery_date", width: 120, sorter: (a: any, b: any) => (a.delivery_date || "").localeCompare(b.delivery_date || ""), render: shortDate },
            { title: "签收日期", dataIndex: "received_date", width: 120, sorter: (a: any, b: any) => (a.received_date || "").localeCompare(b.received_date || ""), render: shortDate },
            { title: "明细", width: 80, align: "right", render: (_: unknown, record: DeliveryNote) => record.items?.length || 0 },
            {
              title: "回款", width: 100,
              render: (_: unknown, record: DeliveryNote) => {
                const ps = paymentMap[record.id];
                if (!ps) return <StatusTag>--</StatusTag>;
                return <StatusTag tone={PAYMENT_STATUS[ps.status]?.color}>{PAYMENT_STATUS[ps.status]?.label}</StatusTag>;
              },
            },
            {
              title: "AI",
              width: 90,
              render: (_: unknown, record: DeliveryNote) => <AIInlineBadge riskLevel={aiMap[record.id]?.completion_risk} flag={aiMap[record.id]?.flag} />,
            },
            {
              title: "操作", width: 60, fixed: "right",
              render: (_: unknown, record: DeliveryNote) => {
                const items: MenuProps["items"] = [
                  { key: "view", icon: <EyeOutlined />, label: "查看详情", onClick: () => navigate(`/sales/delivery-notes/${record.id}`) },
                  { key: "edit", icon: <EditOutlined />, label: "编辑", onClick: () => navigate(`/sales/delivery-notes/${record.id}/edit`) },
                  { type: "divider" as const },
                  { key: "delete", icon: <DeleteOutlined />, label: "删除", danger: true, onClick: () => {
                    Modal.confirm({ title: "确定删除?", content: `删除发货单 #${record.id}？`, onOk: async () => {
                      try { await deleteDeliveryNote(record.id); message.success("已删除"); load(); } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
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
          ] as any}
          summary={(pageData: readonly DeliveryNote[]) => {
            const itemCount = pageData.reduce((s, r) => s + (r.items?.length || 0), 0);
            return (
              <ProTable.Summary.Row>
                <ProTable.Summary.Cell index={0}>合计</ProTable.Summary.Cell>
                <ProTable.Summary.Cell index={1}><Typography.Text strong>{pageData.length} 项</Typography.Text></ProTable.Summary.Cell>
                <ProTable.Summary.Cell index={2} colSpan={4} />
                <ProTable.Summary.Cell index={6} align="right"><Typography.Text strong>{itemCount} 行</Typography.Text></ProTable.Summary.Cell>
                <ProTable.Summary.Cell index={7} colSpan={3} />
              </ProTable.Summary.Row>
            );
          }}
          pagination={{ current: page, pageSize, total, showSizeChanger: true, pageSizeOptions: [20, 50, 100], showQuickJumper: true, showTotal: (total: number, range: [number, number]) => `第 ${range[0]}-${range[1]} 条 / 共 ${total} 条`, locale: { items_per_page: "条/页", jump_to: "跳至", page: "页" }, onChange: (nextPage: number, nextSize: number) => { setPage(nextSize !== pageSize ? 1 : nextPage); setPageSize(nextSize); } }}
        />
      </Card>
    </SalesModuleShell>
  );
}
