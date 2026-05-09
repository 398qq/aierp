import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Tag, Button, Space, message, Card, Modal, InputNumber, Dropdown, Select, DatePicker, Row, Col } from "antd";
import { ReloadOutlined, CheckCircleOutlined, PlusOutlined, EditOutlined, DeleteOutlined, MoreOutlined, ExportOutlined, ClearOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getPurchaseOrders, getSuppliers, receivePurchaseOrder, deletePurchaseOrder } from "../../api";
import type { PurchaseOrder } from "../../types";
import dayjs from "dayjs";

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

  const clearFilters = () => {
    setFilterSupplierId(undefined);
    setFilterStatus(undefined);
    setFilterDateFrom(undefined);
    setFilterDateTo(undefined);
    setPage(1);
  };

  const handleExport = () => {
    const headers = ["订单号", "供应商", "状态", "金额", "预计到货", "备注", "创建时间"];
    const rows = data.map((r) => [
      r.order_no || "-",
      r.supplier_name || `#${r.supplier_id}`,
      STATUS[r.status]?.label || r.status,
      r.total_amount,
      r.expected_date?.slice(0, 10) || "-",
      r.notes || "-",
      r.created_at?.slice(0, 10) || "-",
    ]);
    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `采购订单_${dayjs().format("YYYYMMDD")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success("导出成功");
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

  const columns: ColumnsType<PurchaseOrder> = [
    {
      title: "订单号", dataIndex: "order_no", width: 150,
      render: (v: string, r: PurchaseOrder) => (
        <a onClick={() => navigate(`/sales/purchase-orders/${r.id}`)}>{v || "-"}</a>
      ),
    },
    { title: "供应商", dataIndex: "supplier_name", width: 120, render: (v: string, r) => v || `#${r.supplier_id}` },
    {
      title: "状态", dataIndex: "status", width: 80,
      render: (s: string) => <Tag color={STATUS[s]?.color}>{STATUS[s]?.label || s}</Tag>,
    },
    {
      title: "金额", dataIndex: "total_amount", width: 100,
      render: (v: number) => `¥${v?.toLocaleString() ?? 0}`,
    },
    { title: "预计到货", dataIndex: "expected_date", width: 100, render: (v) => v?.slice(0, 10) || "-" },
    { title: "备注", dataIndex: "notes", ellipsis: true },
    { title: "创建时间", dataIndex: "created_at", width: 100, render: (v) => v?.slice(0, 10) || "-" },
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
                { type: "divider" },
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
    <div>
      <Card
        title="采购订单"
        extra={
          <Space>
            <Button icon={<ExportOutlined />} onClick={handleExport}>导出</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/purchase-orders/new")}>新建</Button>
            <Button icon={<ReloadOutlined />} onClick={() => fetch()}>刷新</Button>
          </Space>
        }
      >
        <Row gutter={12} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Select
              allowClear
              showSearch
              placeholder="供应商"
              optionFilterProp="label"
              style={{ width: "100%" }}
              value={filterSupplierId}
              onChange={(v) => { setFilterSupplierId(v); setPage(1); }}
              options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
            />
          </Col>
          <Col span={4}>
            <Select
              allowClear
              placeholder="状态"
              style={{ width: "100%" }}
              value={filterStatus}
              onChange={(v) => { setFilterStatus(v); setPage(1); }}
              options={[
                { value: "draft", label: "草稿" },
                { value: "received", label: "已收货" },
                { value: "cancelled", label: "已取消" },
              ]}
            />
          </Col>
          <Col span={4}>
            <DatePicker
              placeholder="创建日期-从"
              style={{ width: "100%" }}
              value={filterDateFrom ? dayjs(filterDateFrom) : null}
              onChange={(d) => { setFilterDateFrom(d?.format("YYYY-MM-DD")); setPage(1); }}
            />
          </Col>
          <Col span={4}>
            <DatePicker
              placeholder="创建日期-至"
              style={{ width: "100%" }}
              value={filterDateTo ? dayjs(filterDateTo) : null}
              onChange={(d) => { setFilterDateTo(d?.format("YYYY-MM-DD")); setPage(1); }}
            />
          </Col>
          <Col span={6}>
            <Button icon={<ClearOutlined />} onClick={clearFilters} disabled={!filterSupplierId && !filterStatus && !filterDateFrom && !filterDateTo}>
              清除筛选
            </Button>
          </Col>
        </Row>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="small"
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
    </div>
  );
}
