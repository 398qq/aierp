import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card, Form, Input, Button, Space, Tag, Table, Typography,
  message, Spin, Alert, Badge, Row, Col, Modal,
} from "antd";
import { StatusTag, type StatusTone } from "../../ui";
import {
  SendOutlined, HistoryOutlined, CheckCircleOutlined,
  WarningOutlined, ExclamationCircleOutlined, FileTextOutlined,
} from "@ant-design/icons";
import { inquiryAutoReply, getInquiries, createQuotationFromInquiry, type InquiryAutoReplyResponse, type InquiryRecord, type InquiryMatchedProduct, type InquiryAlternative } from "../../api";
import dayjs from "dayjs";
import { CustomerSelect, SalesModuleShell } from "./salesUi";

const { TextArea } = Input;
const { Paragraph } = Typography;

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = (confidence * 100).toFixed(0);
  let color = "green";
  let icon = <CheckCircleOutlined />;
  if (confidence < 0.6) {
    color = "red";
    icon = <WarningOutlined />;
  } else if (confidence < 0.8) {
    color = "orange";
    icon = <ExclamationCircleOutlined />;
  }
  return (
    <StatusTag status={`${pct}%`} color={color} icon={icon} style={{ fontWeight: 600 }} />
  );
}

function StockStatusTag({ status }: { status: string }) {
  const map: Record<string, { tone: StatusTone; text: string }> = {
    in_stock: { tone: "success", text: "有货" },
    low_stock: { tone: "warning", text: "库存不足" },
    out_of_stock: { tone: "danger", text: "缺货" },
    discontinued: { tone: "neutral", text: "停产" },
  };
  const { tone = "neutral", text } = map[status] || { tone: "neutral" as const, text: status };
  return <StatusTag status={text} tone={tone} />;
}

export default function InquiryAutoReply() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InquiryAutoReplyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [history, setHistory] = useState<InquiryRecord[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const resp = await getInquiries({ limit: 10, sort_by: "created_at", order: "desc" });
      setHistory(resp.data.data.list || []);
    } catch {
      /* ignore */
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleGenerateQuotation = async (record: InquiryRecord) => {
    try {
      const resp = await createQuotationFromInquiry(record.id);
      if (resp.data.code === 0) {
        message.success("报价单已生成：" + resp.data.data.quotation_no);
        navigate("/sales/quotations/" + resp.data.data.id);
      } else {
        message.error(resp.data.msg || "生成失败");
      }
    } catch (err: any) {
      message.error(err?.response?.data?.msg || err?.response?.data?.detail || "生成失败");
    }
  };

  const handleSubmit = async (values: { inquiry_text: string; customer_id?: number; contact_name?: string; contact_info?: string }) => {
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const resp = await inquiryAutoReply({
        inquiry_text: values.inquiry_text,
        customer_id: values.customer_id,
        contact_name: values.contact_name,
        contact_info: values.contact_info,
        channel: "wechat",
      });
      if (resp.data.code === 0) {
        setResult(resp.data.data);
        message.success("询价处理完成");
        fetchHistory();
      } else {
        setError(resp.data.msg || "处理失败");
      }
    } catch (err: any) {
      setError(err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "请求失败");
    } finally {
      setLoading(false);
    }
  };

  const matchedProductColumns = [
    { title: "型号/SKU", dataIndex: "sku", key: "sku", width: 160 },
    { title: "产品名称", dataIndex: "name", key: "name", width: 200 },
    { title: "品牌", dataIndex: "brand", key: "brand", width: 120 },
    {
      title: "库存状态",
      dataIndex: "stock_status",
      key: "stock_status",
      width: 120,
      render: (status: string) => <StockStatusTag status={status} />,
    },
    {
      title: "库存数量",
      dataIndex: "stock_quantity",
      key: "stock_quantity",
      width: 100,
      render: (qty?: number) => qty != null ? qty.toLocaleString() : "-",
    },
    {
      title: "单价(¥)",
      dataIndex: "unit_price",
      key: "unit_price",
      width: 100,
      render: (p?: number) => p != null ? p.toFixed(2) : "-",
    },
  ];

  const alternativeColumns = [
    { title: "原型号", dataIndex: "original_sku", key: "original_sku", width: 120 },
    { title: "替代型号", dataIndex: "alternative_sku", key: "alternative_sku", width: 140 },
    { title: "替代名称", dataIndex: "alternative_name", key: "alternative_name", width: 200 },
    { title: "品牌", dataIndex: "brand", key: "brand", width: 120 },
    { title: "替代原因", dataIndex: "reason", key: "reason", ellipsis: true },
  ];

  const historyColumns = [
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 160,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "询价内容",
      dataIndex: "inquiry_text",
      key: "inquiry_text",
      ellipsis: true,
    },
    {
      title: "客户",
      dataIndex: "customer_name",
      key: "customer_name",
      width: 140,
      render: (v?: string) => v || "-",
    },
    {
      title: "置信度",
      dataIndex: "confidence",
      key: "confidence",
      width: 80,
      render: (v?: number) => v != null ? <ConfidenceBadge confidence={v} /> : "-",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 80,
      render: (v: string) => {
        const toneMap: Record<string, StatusTone> = { processed: "success", pending: "warning", failed: "danger" };
        return <StatusTag status={v} tone={toneMap[v] || "neutral"} />;
      },
    },
    {
      title: "操作",
      key: "actions",
      width: 120,
      render: (_: unknown, record: InquiryRecord) => (
        <Button
          size="small"
          icon={<FileTextOutlined />}
          onClick={() => handleGenerateQuotation(record)}
        >
          生成报价单
        </Button>
      ),
    },
  ];

  return (
    <SalesModuleShell
      title="询价自动回复"
      subtitle="识别客户询价文本，匹配产品库存并生成报价动作"
      activeKey="inquiry"
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Input Form */}
      <Card title="询价输入" size="small">
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ channel: "wechat" }}>
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item
                name="inquiry_text"
                label="询价内容"
                rules={[{ required: true, message: "请输入询价内容" }]}
              >
                <TextArea
                  rows={3}
                  placeholder="例如：需要 QMI8658，1K片，单价多少？"
                  autoSize={{ minRows: 2, maxRows: 5 }}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="customer_id" label="客户（可选）">
                <CustomerSelect />
              </Form.Item>
              <Form.Item name="contact_name" label="联系人（可选）">
                <Input placeholder="手动输入联系人姓名" />
              </Form.Item>
              <Form.Item name="contact_info" label="联系方式（可选）">
                <Input placeholder="手机/微信/邮箱" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item style={{ marginBottom: 0 }}>
            <Space>
              <Button
                type="primary"
                icon={<SendOutlined />}
                htmlType="submit"
                loading={loading}
              >
                发送询价
              </Button>
              <Button onClick={() => { form.resetFields(); setResult(null); setError(null); }}>
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: "center", padding: 32 }}>
          <Spin tip="AI 正在处理询价..." size="large" />
        </div>
      )}

      {/* Error */}
      {error && (
        <Alert
          type="error"
          message="处理失败"
          description={error}
          showIcon
          closable
          onClose={() => setError(null)}
        />
      )}

      {/* Result */}
      {result && !loading && (
        <>
          {/* AI Reply */}
          <Card
            title="AI 回复"
            size="small"
            extra={<ConfidenceBadge confidence={result.confidence} />}
          >
            <Paragraph style={{ marginBottom: 0, whiteSpace: "pre-wrap", fontSize: 15 }}>
              {result.reply_text}
            </Paragraph>
          </Card>

          {/* Matched Products */}
          {result.matched_products.length > 0 && (
            <Card title={`匹配产品 (${result.matched_products.length})`} size="small">
              <Table
                dataSource={result.matched_products}
                columns={matchedProductColumns}
                rowKey="product_id"
                pagination={false}
                size="small"
                scroll={{ x: 760 }}
              />
            </Card>
          )}

          {/* Alternatives */}
          {result.alternatives.length > 0 && (
            <Card title={`替代料建议 (${result.alternatives.length})`} size="small">
              <Table
                dataSource={result.alternatives}
                columns={alternativeColumns}
                rowKey="alternative_sku"
                pagination={false}
                size="small"
                scroll={{ x: 700 }}
              />
            </Card>
          )}
        </>
      )}

      {/* History */}
      <Card
        title={<><HistoryOutlined /> 询价历史</>}
        size="small"
        extra={
          <Button size="small" onClick={fetchHistory} loading={historyLoading}>
            刷新
          </Button>
        }
      >
        <Table
          dataSource={history}
          columns={historyColumns}
          rowKey="id"
          loading={historyLoading}
          pagination={{ pageSize: 10, size: "small" }}
          size="small"
          scroll={{ x: 700 }}
        />
      </Card>
      </div>
    </SalesModuleShell>
  );
}
