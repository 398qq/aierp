import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Alert, Button, Card, Descriptions, Divider, Empty, Space, Spin, Tag, Typography } from "antd";
import { ArrowLeftOutlined, EditOutlined } from "@ant-design/icons";
import { getInvoice } from "../../api";
import type { Invoice } from "../../types";
import { CustomerLink, SalesModuleShell, money, shortDate } from "./salesUi";

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

  if (loading) {
    return (
      <SalesModuleShell title="发票详情" activeKey="invoices">
        <Spin style={{ display: "block", margin: "100px auto" }} />
      </SalesModuleShell>
    );
  }

  if (error) {
    return (
      <SalesModuleShell title="发票详情" activeKey="invoices">
        <Alert type="error" message={error} />
      </SalesModuleShell>
    );
  }

  if (!inv) {
    return (
      <SalesModuleShell title="发票详情" activeKey="invoices">
        <Empty description="发票不存在" />
      </SalesModuleShell>
    );
  }

  return (
    <SalesModuleShell
      title={inv.invoice_no || `发票 #${inv.id}`}
      subtitle={inv.notes ? `备注: ${inv.notes}` : "发票详情，含金额、税额和开票信息"}
      activeKey="invoices"
    >
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/invoices")}>返回</Button>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/invoices/${inv.id}/edit`)}>编辑</Button>
        </Space>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 320px", gap: 12, alignItems: "start" }}>
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Card
            title="发票信息"
            size="small"
            extra={<Tag color={STATUS[inv.status]?.color}>{STATUS[inv.status]?.label || inv.status}</Tag>}
          >
            <Descriptions column={2} size="small">
              <Descriptions.Item label="金额">¥{inv.amount.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="税额">¥{inv.tax_amount.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="类型">{inv.invoice_type}</Descriptions.Item>
              <Descriptions.Item label="关联订单">{inv.sales_order_id}</Descriptions.Item>
              <Descriptions.Item label="客户"><CustomerLink id={inv.customer_id} /></Descriptions.Item>
              <Descriptions.Item label="开票日期">{inv.invoice_date?.slice(0, 10) || "-"}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{inv.notes || "-"}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
          <Card size="small" title="发票摘要">
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">发票号</Typography.Text>
                <Typography.Text strong>{inv.invoice_no || `#${inv.id}`}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">金额</Typography.Text>
                <Typography.Text strong>{money(inv.amount)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">税额</Typography.Text>
                <Typography.Text>{money(inv.tax_amount)}</Typography.Text>
              </div>
              <Divider style={{ margin: "6px 0" }} />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">状态</Typography.Text>
                <Tag color={STATUS[inv.status]?.color}>{STATUS[inv.status]?.label || inv.status}</Tag>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">开票日期</Typography.Text>
                <Typography.Text>{shortDate(inv.invoice_date)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">类型</Typography.Text>
                <Typography.Text>{inv.invoice_type}</Typography.Text>
              </div>
            </Space>
          </Card>

          <Card size="small" title="下一步动作">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              {inv.status === "draft" ? (
                <Alert showIcon type="info" message="发票为草稿状态，确认信息后可以开票。" />
              ) : inv.status === "issued" ? (
                <Alert showIcon type="success" message="发票已开票，等待客户付款。" />
              ) : inv.status === "paid" ? (
                <Alert showIcon type="success" message="发票已付款，流程已完成。" />
              ) : inv.status === "overdue" ? (
                <Alert showIcon type="warning" message="发票已逾期，请及时跟进客户催款。" />
              ) : null}
              <Button block icon={<EditOutlined />} onClick={() => navigate(`/sales/invoices/${inv.id}/edit`)}>编辑发票</Button>
              {inv.customer_id ? (
                <Button block onClick={() => navigate(`/customers/${inv.customer_id}`)}>查看客户</Button>
              ) : null}
            </Space>
          </Card>
        </Space>
      </div>
    </SalesModuleShell>
  );
}
