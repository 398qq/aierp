import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Table, Tag, Typography, Spin, Empty } from "antd";
import { StatusTag } from "../../ui";
import { DollarOutlined, WarningOutlined } from "@ant-design/icons";
import client from "../../api/client";

interface ARData {
  total_ar: number;
  aging: Record<string, { count: number; amount: number }>;
  details: Record<string, { invoice_id: number; invoice_no: string; customer: string; customer_code: string; amount: number; age_days: number; status: string; invoice_date: string | null }[]>;
}

const agingLabels: Record<string, string> = {
  current: "0-30天", "1_30": "31-60天", "31_60": "61-90天", "61_90": "91-120天", over_90: "120天以上",
};
const agingColors: Record<string, string> = {
  current: "green", "1_30": "blue", "31_60": "orange", "61_90": "volcano", over_90: "red",
};

export default function ReportAR() {
  const [data, setData] = useState<ARData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const resp = await client.get("/reports/predefined/ar");
        setData(resp.data.data);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    };
    fetch();
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  const d = data;
  const detailColumns = [
    { title: "发票号", dataIndex: "invoice_no", key: "invoice_no" },
    { title: "客户", dataIndex: "customer", key: "customer" },
    { title: "金额", dataIndex: "amount", key: "amount", render: (v: number) => `¥${v.toLocaleString()}` },
    { title: "账龄(天)", dataIndex: "age_days", key: "age_days" },
    { title: "状态", dataIndex: "status", key: "status", render: (v: string) => <StatusTag>{v}</StatusTag> },
    { title: "发票日期", dataIndex: "invoice_date", key: "invoice_date", render: (v: string | null) => v?.slice(0, 10) || "-" },
  ];

  return (
    <div>
      <Typography.Title level={4}>应收账款账龄报表</Typography.Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card><Statistic title="应收账款总额" value={d?.total_ar || 0} prefix={<DollarOutlined />} precision={2} /></Card>
        </Col>
        {Object.entries(d?.aging || {}).map(([key, val]) => (
          <Col span={3} key={key}>
            <Card size="small">
              <Statistic
                title={<StatusTag tone={agingColors[key]}>{agingLabels[key]}</StatusTag>}
                value={val.count}
                suffix={`笔 / ¥${val.amount.toLocaleString()}`}
                valueStyle={{ fontSize: 16 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {Object.entries(d?.details || {}).map(([key, items]) => (
        items.length > 0 && (
          <Card key={key} title={<StatusTag tone={agingColors[key]}>{agingLabels[key]} ({items.length}笔)</StatusTag>} size="small" style={{ marginBottom: 16 }}>
            <Table rowKey="invoice_id" columns={detailColumns} dataSource={items} pagination={false} size="small" />
          </Card>
        )
      ))}
      {(!d || Object.values(d.details || {}).every(arr => arr.length === 0)) && <Empty description="暂无应收账款" />}
    </div>
  );
}
