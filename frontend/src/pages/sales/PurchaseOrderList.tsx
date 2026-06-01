import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Tag, Button, Space, message, Card, Modal, InputNumber, Dropdown, Select, DatePicker, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { ReloadOutlined, CheckCircleOutlined, PlusOutlined, EditOutlined, DeleteOutlined, MoreOutlined, ClearOutlined } from "@ant-design/icons";
import { getPurchaseOrders, getSuppliers, receivePurchaseOrder, deletePurchaseOrder } from "../../api";
import type { PurchaseOrder } from "../../types";
import dayjs from "dayjs";
import { ErpExportButton, MetricBand, SalesModuleShell } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" },
  received: { color: "green", label: "已收货" },
  cancelled: { color: "red", label: "已取消" },
};

export default function PurchaseOrderList() {
  const navigate = useNavigate();
  const [data, setData] = useState<PurchaseOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [receiveModalOpen, setReceiveModalOpen] = useState(false);
  const [receivePO, setReceivePO] = useState<PurchaseOrder | null>(null);
  const [receiveWarehouseId, setReceiveWarehouseId] = useState(1);
  const [receiving, setReceiving] = useState(false);

  // Filters
  const [filterSupplierId, setFilterSupplierId] = useState<number | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterDateFrom, setFilterDateFrom] = useState<string | undefined>();
  const [filterDateTo, setFilterDateTo] = useState<string | undefined>();
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (filterSupplierId) params.supplier_id = filterSupplierId;
      if (filterStatus) params.status = filterStatus;
      if (filterDateFrom) params.date_from = filterDateFrom;
      if (filterDateTo) params.date_to = filterDateTo;
      const r = await getPurchaseOrders(params);
      setData((r.data.data?.list || []) as PurchaseOrder[]);
      setTotal((r.data.data?.total || 0) as number);
    } catch { message.error("加载采购订单失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [page, filterSupplierId, filterStatus, filterDateFrom, filterDateTo]);

  useEffect(() => {
    getSuppliers({ page: 1, page_size: 100 }).then((r) =>
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

  const handleReceive = async () => {
    if (!receivePO) return;
    setReceiving(true);
    try {
      await receivePurchaseOrder(receivePO.id, receiveWarehouseId);
      message.success(`PO #${receivePO.order_no || receivePO.id} 已收货，库存已自动入库`);
      setReceiveModalOpen(false);
      fetch();
    } catch { message.error("收货失败"); }
    finally { setReceiving(false); }
  };

  const handleDelete = async (po: PurchaseOrder) => {
    try {
      await deletePurchaseOrder(po.id);
      message.success(`PO ${po.order_no || `#${po.id}`} 已删除`);
      fetch();
    } catch { message.error("删除失败"); }
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
      title: "订单号", dataIndex: "order_no", width: 150,
      render: (v: string | null, r: PurchaseOrder) => (
        <a onClick={() => navigate(`/sales/purchase-orders/${r.id}`)}>{v || "-"}</a>
      ),
    },
    { title: "供应商", dataIndex: "supplier_name", width: 120, render: (v: string | null, r: PurchaseOrder) => v || `#${r.supplier_id}` },
    {
      title: "状态", dataIndex: "status", width: 80,
      render: (s: string) => <Tag color={STATUS[s]?.color}>{STATUS[s]?.label || s}</Tag>,
    },
    {
      title: "金额", dataIndex: "total_amount", width: 100,
      render: (v: number) => `¥${v?.toLocaleString() ?? 0}`,
    },
    { title: "预计到货", dataIndex: "expected_date", width: 100, render: (v: string | null) => v?.slice(0, 10) || "-" },
    { title: "备注", dataIndex: "notes", ellipsis: true },
    { title: "创建时间", dataIndex: "created_at", width: 100, render: (v: string) => v?.slice(0, 10) || "-" },
    {
      title: "操作", key: "action", width: 120,
      render: (_: unknown, r: PurchaseOrder) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => navigate(`/sales/purchase-orders/${r.id}`)}>查看</Button>
          {r.status === "draft" && (
            <Dropdown menu={{
              items: [
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
              ],
            }}>
              <Button size="small" icon={<MoreOutlined />} />
            </Dropdown>
          )}
        </Space>
      ),
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
        </Space>
      </Card>

      <Card
        size="small"
        className="sales-erp-table-card"
        title={(
          <Space size={8} wrap>
            <Typography.Text strong>采购订单单据</Typography.Text>
            <Typography.Text type="secondary">{data.length} / {total} 单</Typography.Text>
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
          scroll={{ x: 800 }}
          pagination={{
            current: page, total, pageSize: 20,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p) => setPage(p),
          }}
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
