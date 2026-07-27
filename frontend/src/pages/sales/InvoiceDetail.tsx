import { useEffect, useState } from "react";
import { useParams, useNavigate } from "@/router";
import { Alert, Button, Card, Descriptions, Divider, Empty, Space, Spin, Tag, Typography } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { ArrowLeftOutlined, DollarOutlined, EditOutlined } from "@ant-design/icons";
import { getInvoice } from "../../api";
import type { Invoice } from "../../types";
import { CustomerLink, ErpStatusTimeline, MetricBand, SalesModuleShell, money, shortDate } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" }, issued: { color: "blue", label: "已开票" },
  paid: { color: "green", label: "已付款" }, overdue: { color: "red", label: "逾期" }, cancelled: { color: "default", label: "已取消" },
};

const STATUS_STEPS = [
  { key: "draft", label: "草稿" },
  { key: "issued", label: "已开票" },
  { key: "paid", label: "已付款" },
];

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
      extra={(
        <>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/invoices")}>返回</Button>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/invoices/${inv.id}/edit`)}>编辑</Button>
        </>
      )}
    >
      <MetricBand
        items={[
          { title: "发票金额", value: inv.amount || 0, prefix: "¥", precision: 0 },
          { title: "税额", value: inv.tax_amount || 0, prefix: "¥", precision: 0 },
          { title: "状态", value: STATUS[inv.status]?.label || inv.status },
          { title: "开票日期", value: inv.invoice_date ? shortDate(inv.invoice_date) : "-" },
        ]}
      />

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
            extra={<StatusTag tone={STATUS[inv.status]?.color}>{STATUS[inv.status]?.label || inv.status}</StatusTag>}
          >
            <Descriptions column={2} size="small">
              <Descriptions.Item label="金额">{money(inv.amount)}</Descriptions.Item>
              <Descriptions.Item label="小计">{inv.subtotal != null ? money(inv.subtotal) : "-"}</Descriptions.Item>
              <Descriptions.Item label="税额">{money(inv.tax_amount)}</Descriptions.Item>
              <Descriptions.Item label="币种">{inv.currency || "CNY"}</Descriptions.Item>
              <Descriptions.Item label="到期日">{inv.due_date?.slice(0, 10) || "-"}</Descriptions.Item>
              <Descriptions.Item label="类型">{inv.invoice_type}</Descriptions.Item>
              <Descriptions.Item label="关联订单">
                {inv.sales_order_id ? (
                  <Typography.Link onClick={() => navigate(`/sales/orders/${inv.sales_order_id}`)}>
                    订单 #{inv.sales_order_id}
                  </Typography.Link>
                ) : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="客户"><CustomerLink id={inv.customer_id} /></Descriptions.Item>
              <Descriptions.Item label="开票日期">{inv.invoice_date?.slice(0, 10) || "-"}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{inv.notes || "-"}</Descriptions.Item>
            </Descriptions>
          </Card>

          {inv.items && inv.items.length > 0 && (
            <Card title="发票行项" size="small">
              <ProTable search={false} options={false}
                rowKey="id"
                size="small"
                dataSource={inv.items}
                pagination={false}
                columns={[
                  { title: "产品", dataIndex: "product_name", width: 180 },
                  { title: "数量", dataIndex: "quantity", width: 70, align: "right" },
                  { title: "单位", dataIndex: "unit", width: 60 },
                  { title: "单价", dataIndex: "unit_price", width: 90, align: "right", render: (v: number|null) => v != null ? money(v) : "-" },
                  { title: "金额", dataIndex: "total_price", width: 100, align: "right", render: (v: number|null) => v != null ? money(v) : "-" },
                  { title: "税率", dataIndex: "tax_rate", width: 70, align: "right", render: (v: number|null) => v != null ? `${v}%` : "-" },
                  { title: "税额", dataIndex: "tax_amount", width: 90, align: "right", render: (v: number|null) => v != null ? money(v) : "-" },
                  { title: "备注", dataIndex: "notes", ellipsis: true },
                ] as any}
              />
            </Card>
          )}
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
          <Card size="small" title={<><DollarOutlined /> 发票摘要</>}>
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
                <StatusTag tone={STATUS[inv.status]?.color}>{STATUS[inv.status]?.label || inv.status}</StatusTag>
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

          <Card size="small" title="状态流转">
            <ErpStatusTimeline
              currentStatus={inv.status}
              steps={STATUS_STEPS}
              createdAt={inv.created_at}
              lostStatus="cancelled"
            />
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
