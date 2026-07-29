import { Card, Tag, Typography, Statistic, Empty, Spin } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { DollarOutlined } from "@ant-design/icons";
import { useApiQuery } from "@/lib/queries";

interface APItem {
  po_id: number;
  order_no: string;
  supplier: string;
  amount: number;
  status: string;
  age_days: number;
}

interface APResponse {
  total_ap: number;
  items: APItem[];
}

export default function ReportAP() {
  const query = useApiQuery<APResponse>(["report-ap"], "/finance/reports/ap", undefined, {
    staleTime: 5 * 60 * 1000,
  });
  const data = query.data;
  const loading = query.isLoading;

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  const columns: ProColumns<APItem>[] = [
    { title: "订单号", dataIndex: "order_no", key: "order_no" },
    { title: "供应商", dataIndex: "supplier", key: "supplier" },
    {
      title: "金额",
      dataIndex: "amount",
      key: "amount",
      render: (_, r) => `¥${r.amount.toLocaleString()}`,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (_, r) => <Tag>{r.status}</Tag>,
    },
    { title: "账龄(天)", dataIndex: "age_days", key: "age_days" },
  ];

  return (
    <div>
      <Typography.Title level={4}>应付账款报表</Typography.Title>
      <Card style={{ marginBottom: 16 }}>
        <Statistic
          title="应付账款总额"
          value={data?.total_ap || 0}
          prefix={<DollarOutlined />}
          precision={2}
        />
      </Card>
      <Card title="应付明细" size="small">
        {data?.items?.length ? (
          <ProTable<APItem>
            rowKey="po_id"
            columns={columns}
            dataSource={data.items}
            pagination={false}
            size="small"
            search={false}
            options={false}
          />
        ) : (
          <Empty description="暂无应付账款" />
        )}
      </Card>
    </div>
  );
}
