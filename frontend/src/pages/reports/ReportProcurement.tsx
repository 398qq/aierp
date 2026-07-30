import { Card, Row, Col, Select, Typography, Empty, Spin } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { useApiQuery } from "@/lib/queries";
import { useState } from "react";

interface MonthlyItem {
  month: string;
  count: number;
  amount: number;
}
interface StatusItem {
  status: string;
  count: number;
}
interface ProcurementData {
  monthly: MonthlyItem[];
  status_summary: StatusItem[];
}

const statusColors: Record<string, string> = {
  draft: "default",
  submitted: "processing",
  approved: "blue",
  in_transit: "orange",
  received: "cyan",
  completed: "green",
  cancelled: "red",
  partial: "gold",
};

export default function ReportProcurement() {
  const [months, setMonths] = useState(12);
  const query = useApiQuery<ProcurementData>(
    ["report-procurement", months],
    "/reports/predefined/procurement",
    { months },
    { staleTime: 5 * 60 * 1000 },
  );
  const data = query.data;
  const loading = query.isLoading;

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  const columns: ProColumns<MonthlyItem>[] = [
    { title: "月份", dataIndex: "month", key: "month" },
    { title: "订单数", dataIndex: "count", key: "count" },
    {
      title: "金额",
      dataIndex: "amount",
      key: "amount",
      render: (_, r) => `¥${r.amount.toLocaleString()}`,
    },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <Typography.Title level={4} style={{ margin: 0 }}>
          采购报表
        </Typography.Title>
        <Select
          value={months}
          onChange={setMonths}
          style={{ width: 120 }}
          options={[6, 12, 18, 24, 36].map((m) => ({ value: m, label: `${m}个月` }))}
        />
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={16}>
          <Card title="月度采购趋势" size="small">
            {data?.monthly?.length ? (
              <ProTable<MonthlyItem>
                rowKey="month"
                columns={columns}
                dataSource={data.monthly}
                pagination={false}
                size="small"
                search={false}
                options={false}
              />
            ) : (
              <Empty />
            )}
          </Card>
        </Col>
        <Col span={8}>
          <Card title="订单状态汇总" size="small">
            {(data?.status_summary || []).map((s) => (
              <div
                key={s.status}
                style={{
                  marginBottom: 8,
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <StatusTag status={s.status} color={statusColors[s.status] || "default"} />
                <span>{s.count} 单</span>
              </div>
            ))}
            {(!data?.status_summary || data.status_summary.length === 0) && <Empty />}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
