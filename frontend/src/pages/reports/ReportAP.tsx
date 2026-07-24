import { useEffect, useState } from "react";
import { Card, Tag, Typography, Statistic, Spin, Empty } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { DollarOutlined } from "@ant-design/icons";
import client from "../../api/client";

interface APItem { po_id: number; order_no: string; supplier: string; amount: number; status: string; age_days: number; }

export default function ReportAP() {
  const [data, setData] = useState<{ total_ap: number; items: APItem[] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const resp = await client.get("/finance/reports/ap");
        setData(resp.data.data);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  const columns = [
    { title: "订单号", dataIndex: "order_no", key: "order_no" },
    { title: "供应商", dataIndex: "supplier", key: "supplier" },
    { title: "金额", dataIndex: "amount", key: "amount", render: (v: number) => `¥${v.toLocaleString()}` },
    { title: "状态", dataIndex: "status", key: "status", render: (v: string) => <Tag>{v}</Tag> },
    { title: "账龄(天)", dataIndex: "age_days", key: "age_days" },
  ];

  return (
    <div>
      <Typography.Title level={4}>应付账款报表</Typography.Title>
      <Card style={{ marginBottom: 16 }}>
        <Statistic title="应付账款总额" value={data?.total_ap || 0} prefix={<DollarOutlined />} precision={2} />
      </Card>
      <Card title="应付明细" size="small">
        {data?.items?.length ? (
          <ProTable rowKey="po_id" columns={columns as any} dataSource={data.items} pagination={false} size="small" search={false} options={false} />
        ) : <Empty description="暂无应付账款" />}
      </Card>
    </div>
  );
}
