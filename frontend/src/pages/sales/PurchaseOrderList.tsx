import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, message, Card, Modal, InputNumber, Dropdown, Select, DatePicker, Typography, Input, Popconfirm } from "antd";
import { StatusTag, type StatusTone } from "../../ui";
import { erpPagination } from "../../ui/pagination";
import type { ColumnsType } from "antd/es/table";
import type { MenuProps } from "antd";
import { ReloadOutlined, CheckCircleOutlined, PlusOutlined, EditOutlined, DeleteOutlined, MoreOutlined, ClearOutlined } from "@ant-design/icons";
import { getPurchaseOrders, getSuppliers, receivePurchaseOrder, deletePurchaseOrder, batchDeletePurchaseOrders, getApiErrorMessage } from "../../api";
import type { PurchaseOrder } from "../../types";
import dayjs from "dayjs";
import { ErpExportButton, MetricBand, SalesModuleShell, shortDate } from "./salesUi";

const STATUS: Record<string, { tone: StatusTone; label: string }> = {
  draft: { tone: "neutral", label: "草稿" },
  received: { tone: "success", label: "已收货" },
  cancelled: { tone: "danger", label: "已取消" },
};

export default function PurchaseOrderList() {
  const navigate = useNavigate();
  const [data, setData] = useState<PurchaseOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [receiveModalOpen, setReceiveModalOpen] = useState(false);
  const [receivePO, setReceivePO] = useState<PurchaseOrder | null>(null);
  const [receiveWarehouseId, setReceiveWarehouseId] = useState(1);
  const [receiving, setReceiving] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [searchText, setSearchText] = useState("");
  const [q, setQ] = useState("");

  // Filters
  const [filterSupplierId, setFilterSupplierId] = useState<number | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterDateFrom, setFilterDateFrom] = useState<string | undefined>();
  const [filterDateTo, setFilterDateTo] = useState<string | undefined>();
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: pageSize };
      if (filterSupplierId) params.supplier_id = filterSupplierId;
      if (filterStatus) params.status = filterStatus;
      if (filterDateFrom) params.date_from = filterDateFrom;
      if (filterDateTo) params.date_to = filterDateTo;
      if (q.trim()) params.q = q.trim();
      const r = await getPurchaseOrders(params);
      setData((r.data.data?.list || []) as PurchaseOrder[]);
      setTotal((r.data.data?.total || 0) as number);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载采购订单失败")); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [page, pageSize, filterSupplierId, filterStatus, filterDateFrom, filterDateTo, q]);

  useEffect(() => {
    getSuppliers({ page: 1, page_size: 200 }).then((r) =>
      setSuppliers((r.data.data?.list || []) as { id: number; name: string }[])
    ).catch(() => {});
  }, []);

  const stats = useMemo(() => {
    const amount = data.reduce((sum, item) => sum + Number(item.total_amount || 0), 0);
    const draft = data.filter((item) => item.status === "draft").length;
    const received = data.filter((item) => item.status === "received").length;
    const cancelled = data.filter((item) => item.status === "cancelled").length;
    return { amount, draft, received, cancelled };
  }, [data]);

  const clearFilters = () => {
    setFilterSupplierId(undefined);
    setFilterStatus(undefined);
    setFilterDateFrom(undefined);
    setFilterDateTo(undefined);
    setPage(1);
  };

  const handleBatchDelete = async () => {
    try {
      await batchDeletePurchaseOrders(selected);
      message.success("已批量删除");
      setSelected([]);
      fetch();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "批量删除失败")); }
  };

  const handleReceive = async () => {
    if (!receivePO) return;
    setReceiving(true);
    try {
      await receivePurchaseOrder(receivePO.id, receiveWarehouseId);
      message.success(`PO #${receivePO.order_no || receivePO.id} 已收货，库存已自动入库`);
      setReceiveModalOpen(false);
      fetch();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "收货失败")); }
    finally { setReceiving(false); }
  };

  const handleDelete = async (po: PurchaseOrder) => {
    try {
      await deletePurchaseOrder(po.id);
      message.success(`PO ${po.order_no || `#${po.id}`} 已删除`);
      setSelected((prev) => prev.filter((id) => id !== po.id));
      fetch();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
  };

  const exportData = useMemo(() => data.map((item) => ({
    order_no: item.order_no || "-",
    supplier: item.supplier_name || `#${item.supplier_id}`,
    status: STATUS[item.status]?.label || item.status,
    total_amount: `¥${item.total_amount?.toLocaleString() ?? 0}`,
    expected_date: item.expected_date?.slice(0, 10) || "-",
    notes: item.notes || "-",
    created_at: item.created_at?.slice(0, 10) || "-",
  })), [data]);

  const columns: ColumnsType<PurchaseOrder> = [
    { title: "#", width: 40, fixed: "left" as const, render: (_: unknown, __: PurchaseOrder, index: number) => (page - 1) * 20 + index + 1 },
    {
      title: "采购单", dataIndex: "order_no", minWidth: 200,
      render: (v: string | null, r: PurchaseOrder) => (
        <Space direction="vertical" size={0}>
          <a onClick={() => navigate(`/sales/purchase-orders/${r.id}`)}>{v || `PO#${r.id}`}</a>
          <Space size={8}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{r.supplier_name || `#${r.supplier_id}`}</Typography.Text>
          </Space>
        </Space>
      ),
    },
    {
      title: "状态", dataIndex: "status", width: 80,
      render: (s: string) => <StatusTag status={s} tone={STATUS[s]?.tone || "neutral"} label={STATUS[s]?.label || s} />,
    },
    {
      title: "金额", dataIndex: "total_amount", width: 120,
      render: (v: number) => `¥${v?.toLocaleString() ?? 0}`,
    },
    { title: "预计到货", dataIndex: "expected_date", width: 100, render: (v: string | null) => shortDate(v) },
    { title: "备注", dataIndex: "notes", ellipsis: true },
    { title: "创建时间", dataIndex: "created_at", width: 100, render: (v: string) => shortDate(v) },
    {
      title: "操作", key: "action", width: 60, fixed: "right" as const,
      render: (_: unknown, r: PurchaseOrder) => {
        const items: MenuProps["items"] = [
          { key: "view", label: "查看详情", onClick: () => navigate(`/sales/purchase-orders/${r.id}`) },
          ...(r.status === "draft" ? [
            { key: "receive", icon: <CheckCircleOutlined />, label: "收货",
              onClick: () => { setReceivePO(r); setReceiveModalOpen(true); } },
            { key: "edit", icon: <EditOutlined />, label: "编辑",
              onClick: () => navigate(`/sales/purchase-orders/${r.id}/edit`) },
            { type: "divider" as const },
            { key: "delete", icon: <DeleteOutlined />, label: "删除", danger: true,
              onClick: () => Modal.confirm({
                title: "确认删除",
                content: `确定要删除 ${r.order_no || `PO#${r.id}`} 吗？`,
                onOk: () => handleDelete(r),
                okText: "删除",
                cancelText: "取消",
                okButtonProps: { danger: true },
              }) },
          ] : []),
        ];
        return (
          <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
            <Button size="small" icon={<MoreOutlined />} type="text" />
          </Dropdown>
        );
      },
    },
  ];

  return (
    <SalesModuleShell
      title="采购订单"
      subtitle="管理供应商采购，跟踪到货和入库"
      activeKey="procurement"
      extra={(
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/purchase-orders/new")}>新建采购单</Button>
          <Button icon={<ReloadOutlined />} onClick={() => fetch()}>刷新</Button>
        </Space>
      )}
    >
      <MetricBand
        items={[
          { title: "采购单数", value: total, suffix: "单" },
          { title: "本页金额", value: stats.amount, prefix: "¥", precision: 0 },
          { title: "草稿", value: stats.draft, suffix: "单" },
          { title: "已收货", value: stats.received, suffix: "单" },
          { title: "已取消", value: stats.cancelled, suffix: "单" },
        ]}
      />

      <Card size="small" className="sales-erp-toolbar" style={{ marginBottom: 12 }}>
        <Space wrap>
          <ErpExportButton
            data={exportData as unknown as Record<string, unknown>[]}
            columns={[
              { key: "order_no", title: "订单号" },
              { key: "supplier", title: "供应商" },
              { key: "status", title: "状态" },
              { key: "total_amount", title: "金额" },
              { key: "expected_date", title: "预计到货" },
              { key: "notes", title: "备注" },
              { key: "created_at", title: "创建时间" },
            ]}
            filename={`采购订单_${dayjs().format("YYYYMMDD")}.csv`}
          />
          <Input.Search
            allowClear
            placeholder="搜索订单号 / 供应商 / 产品"
            value={searchText}
            onChange={(e) => {
              setSearchText(e.target.value);
              if (!e.target.value) {
                setPage(1);
                setQ("");
              }
            }}
            onSearch={(value) => {
              setPage(1);
              setQ(value);
            }}
            style={{ width: 240 }}
          />
          <Select
            allowClear
            showSearch
            placeholder="供应商"
            optionFilterProp="label"
            style={{ width: 160 }}
            value={filterSupplierId}
            onChange={(v) => { setFilterSupplierId(v); setPage(1); }}
            options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
          />
          <Select
            allowClear
            placeholder="状态"
            style={{ width: 120 }}
            value={filterStatus}
            onChange={(v) => { setFilterStatus(v); setPage(1); }}
            options={[
              { value: "draft", label: "草稿" },
              { value: "received", label: "已收货" },
              { value: "cancelled", label: "已取消" },
            ]}
          />
          <DatePicker
            placeholder="创建日期-从"
            value={filterDateFrom ? dayjs(filterDateFrom) : null}
            onChange={(d) => { setFilterDateFrom(d?.format("YYYY-MM-DD")); setPage(1); }}
          />
          <DatePicker
            placeholder="创建日期-至"
            value={filterDateTo ? dayjs(filterDateTo) : null}
            onChange={(d) => { setFilterDateTo(d?.format("YYYY-MM-DD")); setPage(1); }}
          />
          <Button icon={<ClearOutlined />} onClick={clearFilters} disabled={!filterSupplierId && !filterStatus && !filterDateFrom && !filterDateTo}>
            清除筛选
          </Button>
          {selected.length > 0 ? (
            <Popconfirm title="确定批量删除?" onConfirm={handleBatchDelete}>
              <Button danger icon={<DeleteOutlined />}>删除 {selected.length}</Button>
            </Popconfirm>
          ) : null}
        </Space>
      </Card>

      <Card
        size="small"
        className="sales-erp-table-card"
        title={(
          <Space size={8} wrap>
            <Typography.Text strong>采购订单单据</Typography.Text>
            <Typography.Text type="secondary">{data.length} / {total} 单</Typography.Text>
            {selected.length > 0 && <StatusTag status={`已选 ${selected.length}`} tone="info" />}
          </Space>
        )}
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="small"
          bordered
          rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
          scroll={{ x: 900 }}
          pagination={erpPagination({
            current: page, total, pageSize,
            onChange: (p, ps) => { setPage(ps !== pageSize ? 1 : p); setPageSize(ps); },
          })}
        />
      </Card>

      <Modal
        title="采购收货"
        open={receiveModalOpen}
        onCancel={() => setReceiveModalOpen(false)}
        onOk={handleReceive}
        confirmLoading={receiving}
        okText="确认收货"
      >
        {receivePO && (
          <>
            <p><strong>订单号:</strong> {receivePO.order_no || `#${receivePO.id}`}</p>
            <p><strong>供应商:</strong> {receivePO.supplier_name || `#${receivePO.supplier_id}`}</p>
            <p>
              <strong>入库仓库:</strong>
              <InputNumber min={1} value={receiveWarehouseId} onChange={(v) => setReceiveWarehouseId(v || 1)} style={{ marginLeft: 8, width: 80 }} />
            </p>
            <p style={{ color: "#52c41a" }}>确认收货后，系统将自动为每个采购项增加库存。</p>
          </>
        )}
      </Modal>
    </SalesModuleShell>
  );
}
