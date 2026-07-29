import { Card, Row, Col, Statistic, Typography, Empty, Spin } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { WarningOutlined, ShopOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { erpPagination } from "../../ui/pagination";
import { useApiQuery } from "@/lib/queries";

interface InventoryItem {
  name: string;
  sku: string;
  quantity: number;
  safety_stock: number;
  status: string;
}

interface InventoryData {
  summary: { total_products: number; low_stock: number; out_of_stock: number };
  items: InventoryItem[];
}

const statusColors: Record<string, string> = {
  "正常": "green",
  "低库存": "orange",
  "缺货": "red",
};

export default function ReportInventory() {
  const query = useApiQuery<InventoryData>(
    ["report-inventory"],
    "/reports/predefined/inventory",
    undefined,
    { staleTime: 5 * 60 * 1000 },
  );
  const data = query.data;
  const loading = query.isLoading;

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  const d = data;
  const columns: ProColumns<InventoryItem>[] = [
    { title: "产品名", dataIndex: "name", key: "name" },
    { title: "SKU", dataIndex: "sku", key: "sku" },
    {
      title: "当前库存",
      dataIndex: "quantity",
      key: "quantity",
      sorter: (a, b) => a.quantity - b.quantity,
    },
    { title: "安全库存", dataIndex: "safety_stock", key: "safety_stock" },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (v: string) => <StatusTag status={v} color={statusColors[v] || "default"} />,
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>库存报表</Typography.Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="产品总数"
              value={d?.summary?.total_products || 0}
              prefix={<ShopOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="低库存"
              value={d?.summary?.low_stock || 0}
              prefix={<WarningOutlined />}
              valueStyle={{ color: "#faad14" }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="缺货"
              value={d?.summary?.out_of_stock || 0}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: "#ff4d4f" }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="库存明细" size="small">
        {d?.items?.length ? (
          <ProTable<InventoryItem>
            rowKey="sku"
            columns={columns}
            dataSource={d.items}
            pagination={erpPagination()}
            size="small"
            search={false}
            options={false}
          />
        ) : (
          <Empty />
        )}
      </Card>
    </div>
  );
}