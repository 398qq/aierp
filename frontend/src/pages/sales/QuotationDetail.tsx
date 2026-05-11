import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Button, Space, Tag, Spin, Alert, Empty, Table, Switch, message } from "antd";
import { ArrowLeftOutlined, EditOutlined } from "@ant-design/icons";
import { getQuotation, convertQuotationToOrder, downloadQuotationPDF } from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { Quotation } from "../../types";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" }, sent: { color: "blue", label: "已发送" },
  won: { color: "green", label: "成交" }, lost: { color: "red", label: "丢失" },
};

export default function QuotationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [quote, setQuote] = useState<Quotation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeAi, setIncludeAi] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getQuotation(Number(id), includeAi)
      .then((r) => setQuote(r.data.data))
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id, includeAi]);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!quote) return <Empty description="报价单不存在" />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/quotations")}>返回</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/quotations/${quote.id}/edit`)}>编辑</Button>
        <Button onClick={() => { downloadQuotationPDF(quote.id, `quotation_${quote.quotation_no || quote.id}.pdf`).catch(() => message.error("下载失败")); }}>下载PDF</Button>
        {quote.status !== "won" && (
          <Button type="primary" onClick={async () => {
            try { await convertQuotationToOrder(quote.id); message.success("已转为订单"); navigate("/sales/orders"); } catch { message.error("转换失败"); }
          }}>转为订单</Button>
        )}
        <Space>
          <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
          <span style={{ fontSize: 13 }}>AI</span>
        </Space>
      </Space>

      <Card title={quote.quotation_no || `报价单 #${quote.id}`} extra={<Tag color={STATUS[quote.status]?.color}>{STATUS[quote.status]?.label || quote.status}</Tag>}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="标题">{quote.title || "-"}</Descriptions.Item>
          <Descriptions.Item label="总金额">¥{quote.total_amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="有效期">{quote.valid_until?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{quote.notes || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>

      {quote.items.length > 0 && (
        <Card title="报价明细" size="small" style={{ marginTop: 16 }}>
          <Table
            rowKey="id"
            dataSource={quote.items}
            size="small"
            pagination={false}
            columns={[
              { title: "产品", dataIndex: "product_name", ellipsis: true },
              { title: "数量", dataIndex: "quantity", width: 80 },
              { title: "单价", dataIndex: "unit_price", width: 100, render: (v: number | null) => v ? `¥${v}` : "-" },
              { title: "小计", dataIndex: "total_price", width: 120, render: (v: number | null) => v ? `¥${v.toLocaleString()}` : "-" },
            ]}
          />
        </Card>
      )}

      {includeAi && <SalesAIInsight aiData={quote.ai} />}
    </div>
  );
}
