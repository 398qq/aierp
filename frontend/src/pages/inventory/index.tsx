import { useEffect, useState } from "react";
import { Table, Space, Tag, message } from "antd";
import { getInventory, getWarehouses, getProducts } from "../../api";
import type { InventoryItem, Warehouse, Product } from "../../types";

export default function InventoryList() {
  const [data, setData] = useState<InventoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [warehouses, setWarehouses] = useState<Record<number, string>>({});
  const [products, setProducts] = useState<Record<number, string>>({});

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const [invResp, whResp, prodResp] = await Promise.all([
        getInventory({ page: p, page_size: 20 }),
        getWarehouses(),
        getProducts({ page: 1, page_size: 200 }),
      ]);
      setData(invResp.data.data.list);
      setTotal(invResp.data.data.total);
      const whMap: Record<number, string> = {};
      (whResp.data.data as Warehouse[] || []).forEach((w) => { whMap[w.id] = w.name; });
      setWarehouses(whMap);
      const prodMap: Record<number, string> = {};
      (prodResp.data.data.list as Product[] || []).forEach((p) => { prodMap[p.id] = p.name; });
      setProducts(prodMap);
    } catch {
      message.error("加载库存失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetch(); }, [page]);

  const columns = [
    { title: "仓库", dataIndex: "warehouse_id", width: 120, render: (v: number) => warehouses[v] || `#${v}` },
    { title: "产品", dataIndex: "product_id", width: 200, render: (v: number) => products[v] || `#${v}` },
    { title: "数量", dataIndex: "quantity", width: 80 },
    { title: "安全库存", dataIndex: "safety_stock", width: 100 },
    {
      title: "状态", key: "status", width: 80,
      render: (_: unknown, r: InventoryItem) => (
        <Tag color={r.quantity < r.safety_stock ? "red" : "green"}>
          {r.quantity < r.safety_stock ? "不足" : "正常"}
        </Tag>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <h3>库存管理</h3>
      </Space>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
    </div>
  );
}
