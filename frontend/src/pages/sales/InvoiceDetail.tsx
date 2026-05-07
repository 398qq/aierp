import { useEffect, useState } from "react";
import { Card, Descriptions, Tag, Spin, Alert, Button, Space, Modal, Typography, Progress, Badge, Table } from "antd";
import { useParams } from "react-router-dom";
import { DollarOutlined, AlertOutlined } from "@ant-design/icons";
import { getInvoice, generateDunningStrategy, predictPaymentDelays } from "../../api";
import type { Invoice, DunningStrategy, PaymentDelayPrediction } from "../../types";

const statusColors: Record<string, string> = { draft: "default", issued: "green", void: "red" };

const DUNNING_LEVEL_COLORS: Record<string, string> = {
  轻度: "blue", 中度: "orange", 重度: "red",
  light: "blue", medium: "orange", severe: "red",
};

const RISK_COLORS: Record<string, string> = {
  low: "green", medium: "orange", high: "red",
  低: "green", 中: "orange", 高: "red",
};

export default function InvoiceDetail() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Dunning Strategy
  const [dunningModalOpen, setDunningModalOpen] = useState(false);
  const [dunningResult, setDunningResult] = useState<DunningStrategy | null>(null);
  const [dunningLoading, setDunningLoading] = useState(false);

  // Payment Prediction
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [paymentResult, setPaymentResult] = useState<PaymentDelayPrediction | null>(null);
  const [paymentLoading, setPaymentLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const resp = await getInvoice(Number(id));
        setData(resp.data.data);
      } catch { setError("加载失败"); }
      finally { setLoading(false); }
    })();
  }, [id]);

  const handleDunning = async () => {
    setDunningLoading(true);
    try {
      const resp = await generateDunningStrategy(Number(id));
      setDunningResult(resp.data.data);
      setDunningModalOpen(true);
    } catch { /* handled by error boundary or silent */ }
    finally { setDunningLoading(false); }
  };

  const handlePaymentPrediction = async () => {
    setPaymentLoading(true);
    try {
      const resp = await predictPaymentDelays();
      setPaymentResult(resp.data.data);
      setPaymentModalOpen(true);
    } catch { /* handled by error boundary or silent */ }
    finally { setPaymentLoading(false); }
  };

  if (loading) return <Spin />;
  if (error) return <Alert type="error" message={error} />;
  if (!data) return <Alert type="warning" message="未找到" />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button
          icon={<AlertOutlined />}
          loading={dunningLoading}
          onClick={handleDunning}
        >
          催款策略
        </Button>
        <Button
          icon={<DollarOutlined />}
          loading={paymentLoading}
          onClick={handlePaymentPrediction}
        >
          回款预测
        </Button>
      </Space>

      <Card title={`发票详情 - ${data.invoice_no || `#${data.id}`}`}>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="发票号">{data.invoice_no || "-"}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={statusColors[data.status]}>{data.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="客户ID">{data.customer_id}</Descriptions.Item>
          <Descriptions.Item label="销售订单ID">{data.sales_order_id}</Descriptions.Item>
          <Descriptions.Item label="金额">¥{data.amount.toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="税额">¥{data.tax_amount.toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="发票类型">{data.invoice_type}</Descriptions.Item>
          <Descriptions.Item label="开票日期">{data.invoice_date || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{data.notes || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{data.created_at}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Dunning Strategy Modal */}
      <Modal
        title={<span><AlertOutlined /> 催款策略</span>}
        open={dunningModalOpen}
        onCancel={() => setDunningModalOpen(false)}
        footer={<Button onClick={() => setDunningModalOpen(false)}>关闭</Button>}
        width={720}
      >
        {dunningLoading ? (
          <Spin tip="AI 分析中..." />
        ) : dunningResult ? (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Card size="small" style={{ background: "#f0f5ff" }}>
              <Space align="center" size="middle">
                <Typography.Text strong>催款等级：</Typography.Text>
                <Badge
                  status="processing"
                  color={DUNNING_LEVEL_COLORS[dunningResult.dunning_level] || "default"}
                  text={dunningResult.dunning_level}
                />
              </Space>
            </Card>

            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="建议联系人">
                {dunningResult.suggested_contact}
              </Descriptions.Item>
              <Descriptions.Item label="建议时机">
                {dunningResult.suggested_timing}
              </Descriptions.Item>
            </Descriptions>

            <Card size="small" title="催款消息模板" style={{ background: "#fffbe6" }}>
              <Typography.Paragraph
                style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}
              >
                {dunningResult.message_template}
              </Typography.Paragraph>
            </Card>

            <Card size="small" title="升级时间线">
              <Typography.Text>{dunningResult.escalation_timeline}</Typography.Text>
            </Card>

            <Card size="small" title="谈判策略" style={{ background: "#f6ffed" }}>
              <Typography.Text>{dunningResult.negotiation_strategy}</Typography.Text>
            </Card>

            <Card size="small" title="违约风险" style={{ background: "#fff2f0" }}>
              <Space>
                <AlertOutlined style={{ color: "#ff4d4f" }} />
                <Typography.Text type="danger">{dunningResult.risk_of_default}</Typography.Text>
              </Space>
            </Card>
          </Space>
        ) : null}
      </Modal>

      {/* Payment Prediction Modal */}
      <Modal
        title={<span><DollarOutlined /> 回款预测</span>}
        open={paymentModalOpen}
        onCancel={() => setPaymentModalOpen(false)}
        footer={<Button onClick={() => setPaymentModalOpen(false)}>关闭</Button>}
        width={820}
      >
        {paymentLoading ? (
          <Spin tip="AI 分析中..." />
        ) : paymentResult ? (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Card size="small" style={{ background: "#f0f5ff" }}>
              <Space size="large" align="center">
                <div>
                  <Typography.Text strong>整体风险：</Typography.Text>
                  <Tag
                    color={
                      RISK_COLORS[paymentResult.overall_risk?.toLowerCase()] || "default"
                    }
                  >
                    {paymentResult.overall_risk}
                  </Tag>
                </div>
                <div>
                  <Typography.Text strong>风险评分：</Typography.Text>
                  <Progress
                    type="circle"
                    percent={paymentResult.risk_score}
                    size={60}
                    strokeColor={
                      paymentResult.risk_score >= 70
                        ? "#ff4d4f"
                        : paymentResult.risk_score >= 40
                        ? "#faad14"
                        : "#52c41a"
                    }
                  />
                </div>
                <div>
                  <Typography.Text strong>DSO 预测：</Typography.Text>
                  <Typography.Text>{paymentResult.dso_forecast} 天</Typography.Text>
                </div>
              </Space>
            </Card>

            <Card size="small" title="逾期发票预测" style={{ background: "#fff7e6" }}>
              <Table
                size="small"
                dataSource={paymentResult.late_invoice_predictions || []}
                rowKey="invoice_no"
                pagination={false}
                columns={[
                  { title: "发票号", dataIndex: "invoice_no", width: 120 },
                  {
                    title: "金额",
                    dataIndex: "amount",
                    width: 100,
                    render: (v: number) => `¥${v.toFixed(2)}`,
                  },
                  {
                    title: "到期日",
                    dataIndex: "due_date",
                    width: 100,
                  },
                  {
                    title: "预计逾期天数",
                    dataIndex: "predicted_delay_days",
                    width: 110,
                    render: (v: number) => (
                      <Typography.Text type={v > 30 ? "danger" : "warning"}>
                        {v} 天
                      </Typography.Text>
                    ),
                  },
                  {
                    title: "概率",
                    dataIndex: "probability",
                    width: 90,
                    render: (v: number) => (
                      <Progress
                        percent={v}
                        size="small"
                        strokeColor={v >= 70 ? "#ff4d4f" : v >= 40 ? "#faad14" : "#52c41a"}
                      />
                    ),
                  },
                  { title: "原因", dataIndex: "reason" },
                ]}
              />
            </Card>

            <Card size="small" title="现金流影响" style={{ background: "#fff2f0" }}>
              <Typography.Text type="danger">{paymentResult.cash_flow_impact}</Typography.Text>
            </Card>

            <Card size="small" title="建议措施">
              {(paymentResult.recommendations || []).map((rec, i) => (
                <Typography.Paragraph key={i} style={{ marginBottom: 4 }}>
                  <Typography.Text strong>{i + 1}. </Typography.Text>
                  {rec}
                </Typography.Paragraph>
              ))}
            </Card>
          </Space>
        ) : null}
      </Modal>
    </div>
  );
}
