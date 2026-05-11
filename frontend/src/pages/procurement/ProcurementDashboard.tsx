import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Table, Tag, Typography, Spin, Empty, List } from "antd";
import { ShoppingCartOutlined, DollarOutlined, ClockCircleOutlined, TruckOutlined } from "@ant-design/icons";
import client from "../../api/client";

interface DashboardData {
  total_po: number; total_amount: number;
  status_distribution: { status: string; count: number }[];
  monthly_trend: { month: string; count: number; amount: number }[];
  on_time_delivery: { rate: number; on_time: number; late: number };
}

interface RestockItem {
  product_id: number; product_name: string; sku: string;
  warehouse_id: number; current_qty: number; safety_stock: number;
  gap: number; suggested_order: number;
  best_supplier: { id: number; name: string; cost_price: number } | null;
}

interface CalendarItem {
  id: number; order_no: string; supplier_id: number;
  total_amount: number; status: string; expected_date: string;
}

const statusColors: Record<string, string> = {
  draft: "default", submitted: "processing", approved: "blue",
  in_transit: "orange", received: "cyan", completed: "green", cancelled: "red",
};

export default function ProcurementDashboard() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [restock, setRestock] = useState<RestockItem[]>([]);
  const [calendar, setCalendar] = useState<CalendarItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      try {
        const [dResp, rResp, cResp] = await Promise.all([
          client.get("/ai/procurement/dashboard"),
          client.get("/ai/procurement/restock-suggest", { params: { top_k: 10 } }),
          client.get("/ai/procurement/po-calendar"),
        ]);
        setDashboard(dResp.data.data);
        setRestock(rResp.data.data?.suggestions || []);
        setCalendar(cResp.data.data || []);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    };
    fetchAll();
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  const d = dashboard;

  return (
    <div>
      <Typography.Title level={4}>采购仪表板</Typography.Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}><Card><Statistic title="采购订单总数" value={d?.total_po || 0} prefix={<ShoppingCartOutlined />} /></Card></Col>
        <Col span={6}><Card><Statistic title="采购总额" value={d?.total_amount || 0} prefix={<DollarOutlined />} precision={2} /></Card></Col>
        <Col span={6}><Card><Statistic title="准时交付率" value={d?.on_time_delivery?.rate || 0} suffix="%" prefix={<ClockCircleOutlined />} /></Card></Col>
        <Col span={6}><Card><Statistic title="待收货" value={d?.status_distribution?.filter(s => ["approved", "in_transit", "partial"].includes(s.status)).reduce((a, b) => a + b.count, 0) || 0} prefix={<TruckOutlined />} /></Card></Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="订单状态分布" size="small">
            {(d?.status_distribution || []).map(s => (
              <Tag key={s.status} color={statusColors[s.status] || "default"} style={{ margin: 4 }}>
                {s.status}: {s.count}
              </Tag>
            ))}
            {(!d?.status_distribution || d.status_distribution.length === 0) && <Empty description="暂无数据" />}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="月度采购趋势" size="small">
            <Table
              rowKey="month" dataSource={d?.monthly_trend || []} pagination={false} size="small"
              columns={[
                { title: "月份", dataIndex: "month" },
                { title: "订单数", dataIndex: "count" },
                { title: "金额", dataIndex: "amount", render: (v: number) => `¥${v.toLocaleString()}` },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="缺货补货建议" size="small">
            {restock.length === 0 ? <Empty description="暂无缺货产品" /> : (
              <List
                size="small"
                dataSource={restock}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      title={`${item.product_name} (${item.sku})`}
                      description={`库存: ${item.current_qty} | 安全库存: ${item.safety_stock} | 缺口: ${item.gap} | 建议采购: ${item.suggested_order}${item.best_supplier ? ` | 推荐供应商: ${item.best_supplier.name}` : ""}`}
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="预计到货日历" size="small">
            {calendar.length === 0 ? <Empty description="近期无预计到货" /> : (
              <List
                size="small"
                dataSource={calendar}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      title={item.order_no}
                      description={`¥${item.total_amount.toLocaleString()} | ${item.expected_date?.slice(0, 10)}`}
                    />
                    <Tag color={statusColors[item.status]}>{item.status}</Tag>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
