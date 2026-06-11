import { useState } from "react";
import { Card, Form, Input, Button, Typography, Spin, message, Result, Row, Col, Flex } from "antd";
import { SendOutlined, CheckCircleOutlined, RobotOutlined, PhoneOutlined, MailOutlined } from "@ant-design/icons";
import client from "../../api/client";
import type { APIResponse } from "../../types";

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface MatchedProduct {
  id: number;
  sku: string;
  name: string;
  brand_name?: string;
  stock_status: string;
  stock_qty: number;
  unit_price?: number;
}

interface Alternative {
  original_sku: string;
  alternative_sku: string;
  alternative_name: string;
  brand: string;
  reason: string;
}

interface InquiryResult {
  inquiry_id: number;
  reply_text: string;
  confidence: number;
  matched_products: MatchedProduct[];
  alternatives: Alternative[];
  summary: string;
}

function StockBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; text: string }> = {
    in_stock: { color: "green", text: "有货" },
    low_stock: { color: "orange", text: "库存不足" },
    out_of_stock: { color: "red", text: "缺货" },
  };
  const { color = "default", text } = map[status] || { color: "default", text: status };
  return (
    <span style={{
      display: "inline-block",
      padding: "2px 8px",
      borderRadius: 4,
      fontSize: 12,
      fontWeight: 600,
      color: status === "in_stock" ? "#52c41a" : status === "low_stock" ? "#fa8c16" : "#ff4d4f",
      background: status === "in_stock" ? "#f6ffed" : status === "low_stock" ? "#fff7e6" : "#fff1f0",
      border: `1px solid ${status === "in_stock" ? "#b7eb8f" : status === "low_stock" ? "#ffd591" : "#ffa39e"}`,
    }}>
      {text}
    </span>
  );
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = (confidence * 100).toFixed(0);
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      padding: "2px 8px",
      borderRadius: 4,
      fontSize: 12,
      fontWeight: 600,
      color: Number(pct) >= 80 ? "#52c41a" : Number(pct) >= 60 ? "#fa8c16" : "#ff4d4f",
      background: Number(pct) >= 80 ? "#f6ffed" : Number(pct) >= 60 ? "#fff7e6" : "#fff1f0",
    }}>
      <CheckCircleOutlined /> 置信度 {pct}%
    </span>
  );
}

export default function InquiryPortal() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InquiryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (values: { inquiry_text: string; contact_name: string; contact_info: string }) => {
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const resp = await client.post<APIResponse<InquiryResult>>("/public/inquiry", {
        inquiry_text: values.inquiry_text,
        contact_name: values.contact_name,
        contact_info: values.contact_info,
      });
      if (resp.data.code === 0 && resp.data.data) {
        setResult(resp.data.data);
        message.success("询价已提交，AI 正在处理中...");
      } else {
        setError(resp.data.msg || "提交失败，请稍后重试");
      }
    } catch (err: any) {
      setError(err?.response?.data?.msg || err?.message || "网络错误，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      padding: "40px 16px",
    }}>
      {/* Container */}
      <div style={{ maxWidth: 720, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 12,
            background: "white",
            borderRadius: 16,
            padding: "16px 32px",
            boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
          }}>
            <RobotOutlined style={{ fontSize: 32, color: "#667eea" }} />
            <div style={{ textAlign: "left" }}>
              <Title level={4} style={{ margin: 0, color: "#222" }}>TTDIY 电子元器件</Title>
              <Text type="secondary" style={{ fontSize: 13 }}>官方询价通道 · AI 智能响应</Text>
            </div>
          </div>
        </div>

        {/* Form Card */}
        {!result && (
          <Card
            style={{
              borderRadius: 16,
              boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
              border: "none",
            }}
            styles={{ body: { padding: 32 } }}
          >
            <div style={{ marginBottom: 24 }}>
              <Title level={4} style={{ marginBottom: 4 }}>快速询价</Title>
              <Text type="secondary">填写您的产品需求，AI 将实时返回库存和参考价格</Text>
            </div>

            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
              requiredMark={false}
              initialValues={{ contact_name: "", contact_info: "" }}
            >
              <Form.Item
                name="inquiry_text"
                label={<Text strong>产品需求</Text>}
                rules={[{ required: true, message: "请输入询价产品描述" }]}
                extra={<Text type="secondary" style={{ fontSize: 12 }}>可填写型号（MPN）、品牌、数量、交期要求等</Text>}
              >
                <TextArea
                  rows={4}
                  placeholder="例如：需要 QMI8658 型号，1K片，交期要求 2 周"
                  autoSize={{ minRows: 3, maxRows: 6 }}
                  style={{ fontSize: 15 }}
                />
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="contact_name"
                    label={<Text strong>您的姓名</Text>}
                    rules={[{ required: true, message: "请输入姓名" }]}
                  >
                    <Input placeholder="张三" size="large" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="contact_info"
                    label={<Text strong>联系方式</Text>}
                    rules={[{ required: true, message: "请输入手机或邮箱" }]}
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>手机号或邮箱均可</Text>}
                  >
                    <Input
                      placeholder="13800138000 或 name@example.com"
                      size="large"
                      suffix={
                        <span style={{ fontSize: 12, color: "#999" }}>
                          <PhoneOutlined /> 或 <MailOutlined />
                        </span>
                      }
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item style={{ marginBottom: 0, marginTop: 8 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  size="large"
                  block
                  icon={<SendOutlined />}
                  loading={loading}
                  style={{
                    height: 48,
                    fontSize: 16,
                    fontWeight: 600,
                    borderRadius: 8,
                    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    border: "none",
                  }}
                >
                  {loading ? "AI 正在处理..." : "提交询价"}
                </Button>
              </Form.Item>
            </Form>

            {loading && (
              <div style={{ textAlign: "center", padding: "32px 0" }}>
                <Spin size="large" tip="AI 正在分析产品目录，请稍候..." />
                <div style={{ marginTop: 12 }}>
                  <Text type="secondary">通常在 5-10 秒内返回结果</Text>
                </div>
              </div>
            )}

            {error && (
              <Result
                status="error"
                title="提交失败"
                subTitle={error}
                extra={
                  <Button type="primary" onClick={() => setError(null)}>
                    重新填写
                  </Button>
                }
              />
            )}
          </Card>
        )}

        {/* Result Card */}
        {result && !loading && (
          <Card
            style={{
              borderRadius: 16,
              boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
              border: "none",
            }}
            styles={{ body: { padding: 32 } }}
          >
            <div style={{ textAlign: "center", marginBottom: 24 }}>
              <div style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "#f6ffed",
                border: "1px solid #b7eb8f",
                borderRadius: 8,
                padding: "8px 16px",
                marginBottom: 16,
              }}>
                <CheckCircleOutlined style={{ color: "#52c41a", fontSize: 18 }} />
                <Text style={{ color: "#52c41a", fontWeight: 600, fontSize: 15 }}>询价已处理完成</Text>
              </div>
              <div style={{ marginBottom: 8 }}>
                <ConfidenceBadge confidence={result.confidence} />
              </div>
            </div>

            {/* AI Reply */}
            <Card
              title={
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <RobotOutlined style={{ color: "#667eea" }} />
                  <span>AI 回复</span>
                </span>
              }
              style={{ marginBottom: 16 }}
              styles={{ body: { background: "#f8f6ff" } }}
            >
              <Paragraph style={{ fontSize: 15, marginBottom: 0, whiteSpace: "pre-wrap", lineHeight: 1.8 }}>
                {result.reply_text}
              </Paragraph>
            </Card>

            {/* Matched Products */}
            {result.matched_products.length > 0 && (
              <Card
                title={`匹配产品 (${result.matched_products.length})`}
                style={{ marginBottom: 16 }}
                styles={{ body: { padding: 0 } }}
              >
                {result.matched_products.map((p, idx) => (
                  <div
                    key={p.id}
                    style={{
                      padding: "12px 16px",
                      borderBottom: idx < result.matched_products.length - 1 ? "1px solid #f0f0f0" : "none",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <Text strong style={{ fontSize: 14 }}>{p.name}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>型号：{p.sku} {p.brand_name ? `· 品牌：${p.brand_name}` : ""}</Text>
                      <br />
                      {p.unit_price != null && (
                        <Text style={{ fontSize: 13, color: "#fa8c16", fontWeight: 600 }}>
                          含税参考价 ¥{p.unit_price.toFixed(2)}/件
                        </Text>
                      )}
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <StockBadge status={p.stock_status} />
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>库存 {p.stock_qty.toLocaleString()} 件</Text>
                    </div>
                  </div>
                ))}
              </Card>
            )}

            {/* Alternatives */}
            {result.alternatives.length > 0 && (
              <Card title="替代料建议" style={{ marginBottom: 16 }}>
                {result.alternatives.map((alt, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "8px 0",
                      borderBottom: idx < result.alternatives.length - 1 ? "1px solid #f0f0f0" : "none",
                    }}
                  >
                    <Text strong>{alt.alternative_sku}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}> ← {alt.original_sku}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>品牌：{alt.brand} · {alt.reason}</Text>
                  </div>
                ))}
              </Card>
            )}

            {/* Actions */}
            <div style={{ textAlign: "center", marginTop: 24 }}>
              <Button
                size="large"
                onClick={() => { setResult(null); form.resetFields(); }}
                style={{ borderRadius: 8, height: 44, minWidth: 120 }}
              >
                继续询价
              </Button>
            </div>
          </Card>
        )}

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: 24 }}>
          <Text style={{ color: "rgba(255,255,255,0.7)", fontSize: 12 }}>
            免责声明：以上价格仅供参考，实际价格以我司正式报价单为准。提交即表示同意我们的
            <a href="#" style={{ color: "rgba(255,255,255,0.8)" }}> 隐私政策 </a>
            和
            <a href="#" style={{ color: "rgba(255,255,255,0.8)" }}> 服务条款</a>。
          </Text>
        </div>

        {/* Contact Info */}
        <div style={{ textAlign: "center", marginTop: 12 }}>
          <Text style={{ color: "rgba(255,255,255,0.6)", fontSize: 12 }}>
            如需紧急询价，请联系：sales@ttdiy.com · 400-XXX-XXXX
          </Text>
        </div>

      </div>
    </div>
  );
}
