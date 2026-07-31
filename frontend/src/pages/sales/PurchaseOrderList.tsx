import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Space,
  Card,
  Modal,
  InputNumber,
  Dropdown,
  Select,
  DatePicker,
  Typography,
  Input,
  Popconfirm,
  App,
} from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { StatusTag, type StatusTone } from "../../ui";
import type { MenuProps } from "antd";
import {
  ReloadOutlined,
  CheckCircleOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  MoreOutlined,
  ClearOutlined,
} from "@ant-design/icons";
import {
  getPurchaseOrders,
  receivePurchaseOrder,
  deletePurchaseOrder,
  batchDeletePurchaseOrders,
  getApiErrorMessage,
} from "../../api";
import type { PurchaseOrder, PageData, Supplier } from "@/types";
import dayjs from "dayjs";
import { useApiQuery, useQueryClient } from "@/lib/queries";
import { ErpExportButton, MetricBand, SalesModuleShell, shortDate } from "./salesUi";

const STATUS: Record<string, { tone: StatusTone; label: string }> = {
  draft: { tone: "neutral", label: "草稿" },
  approved: { tone: "info", label: "已审批" },
  ordered: { tone: "processing", label: "已下单" },
  partially_received: { tone: "processing", label: "部分收货" },
  received: { tone: "success", label: "已收货" },
  cancelled: { tone: "danger", label: "已取消" },
};

export default function PurchaseOrderList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [receiveModalOpen, setReceiveModalOpen] = useState(false);
  const [receivePO, setReceivePO] = useState<PurchaseOrder | null>(null);
  const [receiveWarehouseId, setReceiveWarehouseId] = useState(1);
  const [receiving, setReceiving] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [searchText, setSearchText] = useState("");
  const [q, setQ] = useState("");

  const [filterSupplierId, setFilterSupplierId] = useState<number | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterDateFrom, setFilterDateFrom] = useState<string | undefined>();
  const [filterDateTo, setFilterDateTo] = useState<string | undefined>();

  const suppliersQuery = useApiQuery<PageData<Supplier>>(
    ["suppliers-options"],
    "/suppliers",
    { page: 1, page_size: 200 },
    { staleTime: 5 * 60 * 1000 },
  );
  const suppliers = suppliersQuery.data?.list || [];

  const params: Record<string, unknown> = {};
  if (filterSupplierId) params.supplier_id = filterSupplierId;
  if (filterStatus) params.status = filterStatus;
  if (filterDateFrom) params.date_from = filterDateFrom;
  if (filterDateTo) params.date_to = filterDateTo;
  if (q.trim()) params.q = q.trim();

  const query = useApiQuery<PageData<PurchaseOrder>>(
    [
      "purchase-orders",
      filterSupplierId ?? "",
      filterStatus ?? "",
      filterDateFrom ?? "",
      filterDateTo ?? "",
      q,
    ],
    "/sales/purchase-orders",
    params,
    { staleTime: 30 * 1000 },
  );

  const list = query.data?.list || [];
  const totalRecords = query.data?.total || 0;

  const stats = useMemo(() => {
    const amount = list.reduce((sum, item) => sum + Number(item.total_amount || 0), 0);
    const draft = list.filter((item) => item.status === "draft").length;
    const received = list.filter((item) => item.status === "received").length;
    const cancelled = list.filter((item) => item.status === "cancelled").length;
    return { amount, draft, received, cancelled };
  }, [list]);

  const clearFilters = () => {
    setFilterSupplierId(undefined);
    setFilterStatus(undefined);
    setFilterDateFrom(undefined);
    setFilterDateTo(undefined);
  };

  const invalidatePOs = () => queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });

  const handleBatchDelete = async () => {
    try {
      await batchDeletePurchaseOrders(selected);
      message.success("已批量删除");
      setSelected([]);
      invalidatePOs();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "批量删除失败"));
    }
  };

  const handleReceive = async () => {
    if (!receivePO) return;
    setReceiving(true);
    try {
      await receivePurchaseOrder(receivePO.id, receiveWarehouseId);
      message.success(`PO #${receivePO.order_no || receivePO.id} 已收货，库存已自动入库`);
      setReceiveModalOpen(false);
      invalidatePOs();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "收货失败"));
    } finally {
      setReceiving(false);
    }
  };

  const handleDelete = async (po: PurchaseOrder) => {
    try {
      await deletePurchaseOrder(po.id);
      message.success(`PO ${po.order_no || `#${po.id}`} 已删除`);
      setSelected((prev) => prev.filter((id) => id !== po.id));
      invalidatePOs();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "删除失败"));
    }
  };

  const exportData = useMemo(
    () =>
      list.map((item) => ({
        order_no: item.order_no || "-",
        supplier: item.supplier_name || `#${item.supplier_id}`,
        status: STATUS[item.status]?.label || item.status,
        total_amount: `¥${item.total_amount?.toLocaleString() ?? 0}`,
        expected_date: item.expected_date?.slice(0, 10) || "-",
        notes: item.notes || "-",
        created_at: item.created_at?.slice(0, 10) || "-",
      })),
    [list],
  );

  const columns: ProColumns<PurchaseOrder>[] = [
    { title: "#", width: 40, fixed: "left", render: (_, __, index) => index + 1 },
    {
      title: "采购单",
      dataIndex: "order_no",
      minWidth: 200,
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <a onClick={() => navigate(`/sales/purchase-orders/${r.id}`)}>
            {r.order_no || `PO#${r.id}`}
          </a>
          <Space size={8}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {r.supplier_name || `#${r.supplier_id}`}
            </Typography.Text>
          </Space>
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 80,
      render: (_, r) => (
        <StatusTag
          status={r.status}
          tone={STATUS[r.status]?.tone || "neutral"}
          label={STATUS[r.status]?.label || r.status}
        />
      ),
    },
    {
      title: "金额",
      dataIndex: "total_amount",
      width: 120,
      render: (_, r) => `¥${r.total_amount?.toLocaleString() ?? 0}`,
    },
    {
      title: "预计到货",
      dataIndex: "expected_date",
      width: 100,
      render: (_, r) => shortDate(r.expected_date),
    },
    { title: "备注", dataIndex: "notes", ellipsis: true },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 100,
      render: (_, r) => shortDate(r.created_at),
    },
    {
      title: "操作",
      key: "action",
      width: 60,
      fixed: "right",
      render: (_, r) => {
        const items: MenuProps["items"] = [
          {
            key: "view",
            label: "查看详情",
            onClick: () => navigate(`/sales/purchase-orders/${r.id}`),
          },
          ...(r.status === "draft"
            ? [
                {
                  key: "edit",
                  icon: <EditOutlined />,
                  label: "编辑",
                  onClick: () => navigate(`/sales/purchase-orders/${r.id}/edit`),
                },
                { type: "divider" as const },
                {
                  key: "delete",
                  icon: <DeleteOutlined />,
                  label: "删除",
                  danger: true,
                  onClick: () =>
                    Modal.confirm({
                      title: "确认删除",
                      content: `确定要删除 ${r.order_no || `PO#${r.id}`} 吗？`,
                      okText: "删除",
                      cancelText: "取消",
                      okButtonProps: { danger: true },
                      onOk: () => handleDelete(r),
                    }),
                },
              ]
            : []),
          ...(["ordered", "partially_received"].includes(r.status)
            ? [
                {
                  key: "receive",
                  icon: <CheckCircleOutlined />,
                  label: "收货",
                  onClick: () => {
                    setReceivePO(r);
                    setReceiveModalOpen(true);
                  },
                },
              ]
            : []),
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
      extra={
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/sales/purchase-orders/new")}
          >
            新建采购单
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => query.refetch()}>
            刷新
          </Button>
        </Space>
      }
    >
      <MetricBand
        items={[
          { title: "采购单数", value: totalRecords, suffix: "单" },
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
              if (!e.target.value) setQ("");
            }}
            onSearch={(value) => setQ(value)}
            style={{ width: 240 }}
          />
          <Select
            allowClear
            showSearch
            placeholder="供应商"
            optionFilterProp="label"
            style={{ width: 160 }}
            value={filterSupplierId}
            onChange={setFilterSupplierId}
            options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
          />
          <Select
            allowClear
            placeholder="状态"
            style={{ width: 120 }}
            value={filterStatus}
            onChange={setFilterStatus}
            options={[
              { value: "draft", label: "草稿" },
              { value: "approved", label: "已审批" },
              { value: "ordered", label: "已下单" },
              { value: "partially_received", label: "部分收货" },
              { value: "received", label: "已收货" },
              { value: "cancelled", label: "已取消" },
            ]}
          />
          <DatePicker
            placeholder="创建日期-从"
            value={filterDateFrom ? dayjs(filterDateFrom) : null}
            onChange={(d) => setFilterDateFrom(d?.format("YYYY-MM-DD"))}
          />
          <DatePicker
            placeholder="创建日期-至"
            value={filterDateTo ? dayjs(filterDateTo) : null}
            onChange={(d) => setFilterDateTo(d?.format("YYYY-MM-DD"))}
          />
          <Button
            icon={<ClearOutlined />}
            onClick={clearFilters}
            disabled={!filterSupplierId && !filterStatus && !filterDateFrom && !filterDateTo}
          >
            清除筛选
          </Button>
          {selected.length > 0 ? (
            <Popconfirm title="确定批量删除?" onConfirm={handleBatchDelete}>
              <Button danger icon={<DeleteOutlined />}>
                删除 {selected.length}
              </Button>
            </Popconfirm>
          ) : null}
        </Space>
      </Card>

      <Card
        size="small"
        className="sales-erp-table-card"
        title={
          <Space size={8} wrap>
            <Typography.Text strong>采购订单单据</Typography.Text>
            <Typography.Text type="secondary">
              {list.length} / {totalRecords} 单
            </Typography.Text>
            {selected.length > 0 && <StatusTag status={`已选 ${selected.length}`} tone="info" />}
          </Space>
        }
      >
        <ProTable<PurchaseOrder>
          rowKey="id"
          columns={columns}
          dataSource={list}
          loading={query.isLoading || query.isFetching}
          search={false}
          options={{ reload: () => query.refetch(), density: true, setting: true }}
          size="small"
          bordered
          rowSelection={{
            selectedRowKeys: selected,
            onChange: (keys) => setSelected(keys as number[]),
          }}
          scroll={{ x: 900 }}
          pagination={{
            total: totalRecords,
            showSizeChanger: true,
            onChange: () => query.refetch(),
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
            <p>
              <strong>订单号:</strong> {receivePO.order_no || `#${receivePO.id}`}
            </p>
            <p>
              <strong>供应商:</strong> {receivePO.supplier_name || `#${receivePO.supplier_id}`}
            </p>
            <p>
              <strong>入库仓库:</strong>
              <InputNumber
                min={1}
                value={receiveWarehouseId}
                onChange={(v) => setReceiveWarehouseId(v || 1)}
                style={{ marginLeft: 8, width: 80 }}
              />
            </p>
            <p style={{ color: "#52c41a" }}>确认收货后，系统将自动为每个采购项增加库存。</p>
          </>
        )}
      </Modal>
    </SalesModuleShell>
  );
}
