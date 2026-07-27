import { useEffect, useState } from "react";
import { Card, Descriptions, Tag, Spin, Alert, Row, Col, List, Typography } from "antd";
import { StatusTag } from "../../ui";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { useParams } from "@/router";
import { getCustomerInsight } from "../../api";
import type { CustomerInsight as CustomerInsightType } from "../../types";

const { Text, Title } = Typography;
const COLORS = ["#1890ff", "#52c41a", "#faad14", "#ff4d4f", "#722ed1", "#13c2c2"];

export default function CustomerInsight() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<CustomerInsightType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const resp = await getCustomerInsight(Number(id));
        setData(resp);
      } catch { setError("加载失败"); }
      finally { setLoading(false); }
    })();
  }, [id]);

  if (loading) return <Spin />;
  if (error) return <Alert type="error" message={error} />;
  if (!data) return <Alert type="warning" message="未找到" />;

  const c = data.customer as Record<string, unknown>;
  const productChartData = data.product_distribution.map(p => ({ name: p.product_name, value: p.amount }));

  return (
    <div>
      <Card title="客户信息" style={{ marginBottom: 24 }}>
        <Descriptions bordered column={3}>
          <Descriptions.Item label="名称">{String(c.name || "-")}</Descriptions.Item>
          <Descriptions.Item label="编码">{String(c.code || "-")}</Descriptions.Item>
          <Descriptions.Item label="行业">{String(c.industry || "-")}</Descriptions.Item>
          <Descriptions.Item label="等级">{String(c.level || "-")}</Descriptions.Item>
          <Descriptions.Item label="联系人">{String(c.contact_person || "-")}</Descriptions.Item>
          <Descriptions.Item label="电话">{String(c.phone || "-")}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Row gutter={24} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="交易历史">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="订单总数">{data.order_summary.total_orders}</Descriptions.Item>
              <Descriptions.Item label="总金额">¥{data.order_summary.total_amount.toFixed(2)}</Descriptions.Item>
              <Descriptions.Item label="平均订单金额">¥{data.order_summary.avg_order_amount.toFixed(2)}</Descriptions.Item>
              <Descriptions.Item label="最近订单">{data.order_summary.last_order_date || "无"}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="产品偏好">
            {productChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={productChartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                    {productChartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : <Alert type="info" message="暂无购买记录" />}
          </Card>
        </Col>
      </Row>

      <Row gutter={24} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="跟进记录">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="总跟进次数">{data.followup_summary.total_followups}</Descriptions.Item>
              <Descriptions.Item label="最近跟进">{data.followup_summary.last_followup || "无"}</Descriptions.Item>
              <Descriptions.Item label="待处理">{data.followup_summary.pending_count}</Descriptions.Item>
              <Descriptions.Item label="已逾期">
                <Text type={data.followup_summary.overdue_count > 0 ? "danger" : undefined}>{data.followup_summary.overdue_count}</Text>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="商机分析">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="总商机数">{data.opportunity_summary.total}</Descriptions.Item>
              <Descriptions.Item label="活跃商机">{data.opportunity_summary.active}</Descriptions.Item>
              <Descriptions.Item label="已赢单">{data.opportunity_summary.won}</Descriptions.Item>
              <Descriptions.Item label="成交概率">
                <StatusTag tone={data.opportunity_summary.win_probability >= 50 ? "success" : "warning"}>{data.opportunity_summary.win_probability}%</StatusTag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {data.suggestions.length > 0 && (
        <Card title="AI 建议">
          <List dataSource={data.suggestions} renderItem={(s: string) => (
            <List.Item><Text>{s}</Text></List.Item>
          )} />
        </Card>
      )}
    </div>
  );
}
