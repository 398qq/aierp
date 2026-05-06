import { useEffect, useState } from "react";
import { Table, Space, Tag, message } from "antd";
import { getSalesOrders } from "../../api";
import type { SalesOrder } from "../../types";

const statusColors: Record<string, string> = {
  pending: "orange", confirmed: "blue", shipped: "cyan", delivered: "green", cancelled: "red",
};

export default function SalesOrderList() {
  const [data, setData] = useState<SalesOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const resp = await getSalesOrders({ page: p, page_size: 20 });
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch {
      message.error("加载销售订单失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetch(); }, [page]);

  const columns = [
    { title: "订单号", dataIndex: "order_no", width: 150 },
    { title: "客户ID", dataIndex: "customer_id", width: 80 },
    { title: "状态", dataIndex: "status", width: 100, render: (v: string) => <Tag color={statusColors[v] || "default"}>{v}</Tag> },
    { title: "金额", dataIndex: "total_amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
    { title: "交货日期", dataIndex: "delivery_date", width: 120 },
    { title: "备注", dataIndex: "notes", width: 200, ellipsis: true },
    { title: "创建时间", dataIndex: "created_at", width: 180 },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <h3>销售订单</h3>
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
