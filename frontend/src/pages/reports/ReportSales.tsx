import { useState } from "react";
import { Card, Row, Col, Select, Typography, Spin, Empty, Button } from "antd";
import type { ProColumns } from "@ant-design/pro-components";
import { ProTable } from "@ant-design/pro-components";
import { DownloadOutlined } from "@ant-design/icons";
import { useApiQuery } from "@/lib/queries";
import client from "../../api/client";
import { SalesModuleShell } from "../sales/salesUi";

interface MonthlyItem { month: string; count: number; amount: number; }
interface TopProduct { name: string; sku: string; order_count: number; }
interface SalesData {
  monthly_orders: MonthlyItem[];
  monthly_quotations: MonthlyItem[];
  top_products: TopProduct[];
}

export default function ReportSales() {
  const [months, setMonths] = useState(12);

  const query = useApiQuery<SalesData>(
    ["report-sales", months],
    "/reports/predefined/sales",
    { months },
    { staleTime: 5 * 60 * 1000 },
  );

  const loading = query.isLoading || query.isFetching;

  const exportCsv = async () => {
    try {
      const resp = await client.post("/reports/export/sales", null, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `sales_report_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch { /* ignore */ }
  };

  const orderColumns: ProColumns<MonthlyItem>[] = [
    { title: "月份", dataIndex: "month", key: "month" },
    { title: "订单数", dataIndex: "count", key: "count" },
    { title: "金额", dataIndex: "amount", key: "amount", render: (_, r) => `¥${r.amount.toLocaleString()}` },
  ];

  const productColumns: ProColumns<TopProduct>[] = [
    { title: "产品名", dataIndex: "name", key: "name" },
    { title: "SKU", dataIndex: "sku", key: "sku" },
    { title: "订单数", dataIndex: "order_count", key: "order_count" },
  ];

  return (
    <SalesModuleShell
      title="销售分析"
      subtitle="查看销售订单、报价趋势和热销产品"
      activeKey="analysis"
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>销售报表</Typography.Title>
        <div>
          <Select value={months} onChange={setMonths} style={{ width: 120, marginRight: 12 }}
            options={[6, 12, 18, 24, 36].map(m => ({ value: m, label: `${m}个月` }))}
          />
          <Button icon={<DownloadOutlined />} onClick={exportCsv}>导出CSV</Button>
        </div>
      </div>

      {loading ? (
        <Spin size="large" style={{ display: "block", margin: "120px auto" }} />
      ) : (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={12}>
              <Card title="月度销售订单" size="small">
                {query.data?.monthly_orders?.length ? (
                  <ProTable<MonthlyItem>
                    rowKey="month"
                    columns={orderColumns}
                    dataSource={query.data.monthly_orders}
                    pagination={false}
                    size="small"
                    search={false}
                    options={false}
                  />
                ) : <Empty />}
              </Card>
            </Col>
            <Col span={12}>
              <Card title="月度报价单" size="small">
                {query.data?.monthly_quotations?.length ? (
                  <ProTable<MonthlyItem>
                    rowKey="month"
                    columns={orderColumns}
                    dataSource={query.data.monthly_quotations}
                    pagination={false}
                    size="small"
                    search={false}
                    options={false}
                  />
                ) : <Empty />}
              </Card>
            </Col>
          </Row>

          <Card title="热销产品 Top 10" size="small">
            {query.data?.top_products?.length ? (
              <ProTable<TopProduct>
                rowKey="sku"
                columns={productColumns}
                dataSource={query.data.top_products}
                pagination={false}
                size="small"
                search={false}
                options={false}
              />
            ) : <Empty />}
          </Card>
        </>
      )}
    </SalesModuleShell>
  );
}