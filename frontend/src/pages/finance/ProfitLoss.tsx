import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Table, Select, Tag, Spin, Empty, Descriptions } from "antd";
import { DollarOutlined, RiseOutlined, FallOutlined, TrophyOutlined } from "@ant-design/icons";
import client from "../../api/client";

interface PnLData {
  month: string; revenue: number; cost_of_goods: number;
  gross_profit: number; net_profit: number; details: Record<string, { debit: number; credit: number }>;
}

const typeLabels: Record<string, string> = { asset: "资产", liability: "负债", equity: "权益", income: "收入", expense: "费用" };

export default function ProfitLoss() {
  const [data, setData] = useState<PnLData | null>(null);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const resp = await client.get("/finance/reports/pnl", { params: { month } });
        setData(resp.data.data);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    })();
  }, [month]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  const d = data;
  const months = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date();
    d.setMonth(d.getMonth() - i);
    months.push(d.toISOString().slice(0, 7));
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h4 style={{ margin: 0 }}>损益表</h4>
        <Select value={month} onChange={setMonth} style={{ width: 140 }}
          options={months.map(m => ({ value: m, label: m }))} />
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}><Card><Statistic title="营业收入" value={d?.revenue || 0} prefix={<RiseOutlined />} precision={2} /></Card></Col>
        <Col span={6}><Card><Statistic title="营业成本" value={d?.cost_of_goods || 0} prefix={<FallOutlined />} precision={2} /></Card></Col>
        <Col span={6}><Card><Statistic title="毛利" value={d?.gross_profit || 0} prefix={<DollarOutlined />} precision={2} /></Card></Col>
        <Col span={6}><Card><Statistic title="净利润" value={d?.net_profit || 0} prefix={<TrophyOutlined />} precision={2}
          valueStyle={{ color: (d?.net_profit || 0) >= 0 ? "#3f8600" : "#cf1322" }} /></Card></Col>
      </Row>

      <Card title="明细" size="small">
        {d?.details && Object.keys(d.details).length > 0 ? (
          <Descriptions bordered size="small" column={2}>
            {Object.entries(d.details).map(([type, vals]) => (
              <Descriptions.Item key={type} label={typeLabels[type] || type}>
                借: ¥{vals.debit.toLocaleString()} | 贷: ¥{vals.credit.toLocaleString()}
              </Descriptions.Item>
            ))}
          </Descriptions>
        ) : <Empty description="该月无过账凭证" />}
      </Card>
    </div>
  );
}
