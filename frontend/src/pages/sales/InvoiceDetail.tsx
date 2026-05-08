import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Button, Space, Tag, Spin, Alert, Empty } from "antd";
import { ArrowLeftOutlined, EditOutlined } from "@ant-design/icons";
import { getInvoice } from "../../api";
import type { Invoice } from "../../types";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" }, issued: { color: "blue", label: "已开票" },
  paid: { color: "green", label: "已付款" }, overdue: { color: "red", label: "逾期" }, cancelled: { color: "default", label: "已取消" },
};

export default function InvoiceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [inv, setInv] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getInvoice(Number(id)).then((r) => setInv(r.data.data))
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!inv) return <Empty description="发票不存在" />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/invoices")}>返回</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/invoices/${inv.id}/edit`)}>编辑</Button>
      </Space>
      <Card title={inv.invoice_no || `发票 #${inv.id}`} extra={<Tag color={STATUS[inv.status]?.color}>{STATUS[inv.status]?.label || inv.status}</Tag>}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="金额">¥{inv.amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="税额">¥{inv.tax_amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="类型">{inv.invoice_type}</Descriptions.Item>
          <Descriptions.Item label="关联订单">{inv.sales_order_id}</Descriptions.Item>
          <Descriptions.Item label="客户ID">{inv.customer_id}</Descriptions.Item>
          <Descriptions.Item label="开票日期">{inv.invoice_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{inv.notes || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
