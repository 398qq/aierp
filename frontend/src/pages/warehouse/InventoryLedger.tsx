import { useEffect, useState } from "react";
import { Table, Button, Space, Card, Select, Input, message } from "antd";
import { StatusTag } from "../../ui";
import { ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getInventoryTransactions, getWarehouses, getApiErrorMessage } from "../../api";
import type { Warehouse } from "../../types";

const TRANSACTION_TYPES = [
  { value: "stock_in", label: "入库" },
  { value: "stock_out", label: "出库" },
  { value: "adjust", label: "调整" },
  { value: "transfer", label: "调拨" },
];

const TYPE_COLORS: Record<string, string> = {
  stock_in: "green",
  stock_out: "red",
  adjust: "orange",
  transfer: "blue",
};

const TYPE_LABELS: Record<string, string> = {
  stock_in: "入库",
  stock_out: "出库",
  adjust: "调整",
  transfer: "调拨",
};

interface InventoryTransactionRecord {
  id: number;
  product_id: number;
  warehouse_id: number;
  type: string;
  quantity: number;
  before_qty: number | null;
  after_qty: number | null;
  reference_type: string | null;
  reference_id: number | null;
  notes: string | null;
  created_at: string;
  product_name: string;
  warehouse_name: string;
}

export default function InventoryLedger() {
  const [data, setData] = useState<InventoryTransactionRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [warehouseId, setWarehouseId] = useState<number | undefined>();
  const [productSearch, setProductSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | undefined>();

  useEffect(() => {
    getWarehouses({ page: 1, page_size: 200 }).then((r) => {
      if (r.data.code === 0) setWarehouses(r.data.data.list as Warehouse[]);
    });
  }, []);

  const fetch = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (warehouseId) params.warehouse_id = warehouseId;
      if (typeFilter) params.type = typeFilter;
      if (productSearch) params.product_id = productSearch;

      const resp = await getInventoryTransactions(params);
      if (resp.data.code === 0) {
        setData(resp.data.data.list as InventoryTransactionRecord[]);
        setTotal(resp.data.data.total);
      }
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载库存流水失败")); } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, [page, warehouseId, typeFilter]);

  const handleSearch = () => {
    setPage(1);
    fetch();
  };

  const columns: ColumnsType<InventoryTransactionRecord> = [
    {
      title: "日期",
      dataIndex: "created_at",
      width: 100,
      render: (v: string) => v?.slice(0, 10) || "-",
    },
    { title: "产品", dataIndex: "product_name", width: 180, ellipsis: true },
    { title: "仓库", dataIndex: "warehouse_name", width: 120 },
    {
      title: "类型",
      dataIndex: "type",
      width: 80,
      render: (v: string) => (
        <StatusTag status={v} color={TYPE_COLORS[v] || "default"} label={TYPE_LABELS[v] || v} />
      ),
    },
    {
      title: "数量变化",
      width: 120,
      render: (_: unknown, r: InventoryTransactionRecord) => {
        const sign = r.type === "stock_in" || r.type === "adjust" ? "+" : "-";
        const color = r.type === "stock_in" ? "green" : r.type === "stock_out" ? "red" : "orange";
        return <span style={{ color }}>{sign}{r.quantity}</span>;
      },
    },
    {
      title: "库存变化",
      width: 140,
      render: (_: unknown, r: InventoryTransactionRecord) => {
        if (r.before_qty === null || r.after_qty === null) return "-";
        return `${r.before_qty} → ${r.after_qty}`;
      },
    },
    { title: "参考类型", dataIndex: "reference_type", width: 100, render: (v) => v || "-" },
    { title: "参考ID", dataIndex: "reference_id", width: 80, render: (v) => v || "-" },
    { title: "备注", dataIndex: "notes", ellipsis: true, render: (v) => v || "-" },
  ];

  return (
    <div>
      <Card
        title="库存台账"
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetch}>刷新</Button>
        }
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            allowClear
            placeholder="选择仓库"
            style={{ width: 160 }}
            value={warehouseId}
            onChange={(v) => { setWarehouseId(v); setPage(1); }}
            options={warehouses.map((w) => ({ value: w.id, label: w.name }))}
          />
          <Select
            allowClear
            placeholder="交易类型"
            style={{ width: 120 }}
            value={typeFilter}
            onChange={(v) => { setTypeFilter(v); setPage(1); }}
            options={TRANSACTION_TYPES}
          />
          <Input.Search
            placeholder="搜索产品ID"
            style={{ width: 160 }}
            value={productSearch}
            onChange={(e) => setProductSearch(e.target.value)}
            onSearch={handleSearch}
            enterButton
          />
        </Space>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="small"
          scroll={{ x: 1000 }}
          pagination={{
            current: page,
            total,
            pageSize,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p) => setPage(p),
          }}
        />
      </Card>
    </div>
  );
}
