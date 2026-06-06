import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Table, Typography, Spin, Empty } from "antd";
import { StatusTag } from "../../ui";
import { WarningOutlined, ShopOutlined, CloseCircleOutlined } from "@ant-design/icons";
import client from "../../api/client";

interface InventoryData {
  summary: { total_products: number; low_stock: number; out_of_stock: number };
  items: { name: string; sku: string; quantity: number; safety_stock: number; status: string }[];
}

const statusColors: Record<string, string> = { "正常": "green", "低库存": "orange", "缺货": "red" };

export default function ReportInventory() {
  const [data, setData] = useState<InventoryData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const resp = await client.get("/reports/predefined/inventory");
        setData(resp.data.data);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    };
    fetch();
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  const d = data;
  const columns = [
    { title: "产品名", dataIndex: "name", key: "name" },
    { title: "SKU", dataIndex: "sku", key: "sku" },
    { title: "当前库存", dataIndex: "quantity", key: "quantity", sorter: (a: { quantity: number }, b: { quantity: number }) => a.quantity - b.quantity },
    { title: "安全库存", dataIndex: "safety_stock", key: "safety_stock" },
    {
      title: "状态", dataIndex: "status", key: "status",
      render: (v: string) => <StatusTag status={v} color={statusColors[v] || "default"} />,
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>库存报表</Typography.Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card><Statistic title="产品总数" value={d?.summary?.total_products || 0} prefix={<ShopOutlined />} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="低库存" value={d?.summary?.low_stock || 0} prefix={<WarningOutlined />} valueStyle={{ color: "#faad14" }} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="缺货" value={d?.summary?.out_of_stock || 0} prefix={<CloseCircleOutlined />} valueStyle={{ color: "#ff4d4f" }} /></Card>
        </Col>
      </Row>

      <Card title="库存明细" size="small">
        {d?.items?.length ? (
          <Table rowKey="sku" columns={columns} dataSource={d.items} pagination={{ pageSize: 20 }} size="small" />
        ) : <Empty />}
      </Card>
    </div>
  );
}
