import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Button, Space, Tag, Spin, Alert, Empty, Table, Switch, message, Modal, Form, Select, Input, Checkbox } from "antd";
import { ArrowLeftOutlined, DownloadOutlined, EditOutlined } from "@ant-design/icons";
import { getSalesOrder, convertSalesOrderToDelivery, updateSalesOrder, downloadSalesOrderPDF } from "../../api";
import type { SalesOrderPDFOptions } from "../../api";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { SalesOrder } from "../../types";
import { CustomerLink } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  pending: { color: "default", label: "待处理" }, confirmed: { color: "blue", label: "已确认" },
  shipped: { color: "orange", label: "已发货" }, delivered: { color: "green", label: "已签收" }, cancelled: { color: "red", label: "已取消" },
};

export default function SalesOrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<SalesOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeAi, setIncludeAi] = useState(true);
  const [pdfOpen, setPdfOpen] = useState(false);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [pdfForm] = Form.useForm<SalesOrderPDFOptions>();

  useEffect(() => {
    setLoading(true);
    setError(null);
    getSalesOrder(Number(id), includeAi)
      .then((r) => setOrder(r.data.data))
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id, includeAi]);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!order) return <Empty description="订单不存在" />;

  const handleDownloadPDF = async () => {
    setPdfDownloading(true);
    try {
      const values = await pdfForm.validateFields();
      await downloadSalesOrderPDF(order.id, `sales_order_${order.order_no || order.id}.pdf`, values);
      setPdfOpen(false);
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error("下载失败");
    } finally {
      setPdfDownloading(false);
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/orders")}>返回</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/orders/${order.id}/edit`)}>编辑</Button>
        <Button icon={<DownloadOutlined />} onClick={() => setPdfOpen(true)}>智能PDF</Button>
        <Button type="primary" onClick={async () => {
          try { await convertSalesOrderToDelivery(order.id); message.success("已转为发货单"); navigate("/sales/delivery-notes"); } catch { message.error("转换失败"); }
        }}>转为发货单</Button>
        {order.status === "pending" && (
          <Button type="primary" style={{ background: "#52c41a", borderColor: "#52c41a" }} onClick={async () => {
            try { await updateSalesOrder(order.id, { status: "confirmed" }); message.success("订单已确认，库存已锁定"); setOrder({ ...order, status: "confirmed" }); } catch { message.error("确认失败"); }
          }}>确认订单 (锁定库存)</Button>
        )}
        <Space>
          <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
          <span style={{ fontSize: 13 }}>AI</span>
        </Space>
      </Space>

      <Modal
        title="自定义订单 PDF"
        open={pdfOpen}
        onCancel={() => setPdfOpen(false)}
        onOk={handleDownloadPDF}
        confirmLoading={pdfDownloading}
        okText="下载 PDF"
        width={680}
      >
        <Form
          form={pdfForm}
          layout="vertical"
          onValuesChange={(changed) => {
            if (!("template" in changed)) return;
            if (changed.template === "smart") {
              pdfForm.setFieldsValue({ show_smart_summary: true, show_line_hints: true, show_terms: true, show_notes: true, show_signature: true });
            } else if (changed.template === "standard") {
              pdfForm.setFieldsValue({ show_smart_summary: false, show_line_hints: false, show_terms: true, show_notes: true, show_signature: true });
            } else if (changed.template === "compact") {
              pdfForm.setFieldsValue({ show_smart_summary: false, show_line_hints: false, show_terms: true, show_notes: false, show_signature: false });
            }
          }}
          initialValues={{
            template: "smart",
            document_title: "正式销售订单 / SALES ORDER",
            show_smart_summary: true,
            show_line_hints: true,
            show_terms: true,
            show_notes: true,
            show_signature: true,
            terms: [
              "1、订单产品、数量、单价、交期以双方确认的销售订单为准；",
              "2、交付前请确认库存、包装、收货地址及客户验收要求；",
              "3、付款方式、发票及运输方式以合同或双方最终确认为准；",
            ].join("\n"),
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            <Form.Item name="template" label="PDF 形式">
              <Select options={[
                { value: "smart", label: "智能版：含交付摘要" },
                { value: "standard", label: "标准版：订单和条款" },
                { value: "compact", label: "紧凑版：适合打印" },
              ]} />
            </Form.Item>
            <Form.Item name="company_name" label="抬头公司">
              <Input placeholder="默认取客户公司名称" />
            </Form.Item>
          </div>
          <Form.Item name="document_title" label="文档标题">
            <Input />
          </Form.Item>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            <Form.Item name="prepared_by" label="制单人">
              <Input placeholder="销售 / 商务负责人" />
            </Form.Item>
            <Form.Item name="contact_phone" label="联系电话">
              <Input placeholder="对外联系号码" />
            </Form.Item>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8 }}>
            <Form.Item name="show_smart_summary" valuePropName="checked"><Checkbox>智能摘要</Checkbox></Form.Item>
            <Form.Item name="show_line_hints" valuePropName="checked"><Checkbox>交付提示</Checkbox></Form.Item>
            <Form.Item name="show_terms" valuePropName="checked"><Checkbox>交付条款</Checkbox></Form.Item>
            <Form.Item name="show_notes" valuePropName="checked"><Checkbox>订单备注</Checkbox></Form.Item>
            <Form.Item name="show_signature" valuePropName="checked"><Checkbox>签署确认栏</Checkbox></Form.Item>
          </div>
          <Form.Item name="terms" label="交付条款">
            <Input.TextArea rows={5} />
          </Form.Item>
        </Form>
      </Modal>

      <Card title={order.order_no || `订单 #${order.id}`} extra={<Tag color={STATUS[order.status]?.color}>{STATUS[order.status]?.label || order.status}</Tag>}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="客户"><CustomerLink id={order.customer_id} /></Descriptions.Item>
          <Descriptions.Item label="总金额">¥{order.total_amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="下单日期">{order.order_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="预计交货">{order.delivery_date?.slice(0, 10) || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{order.notes || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>

      {order.items.length > 0 && (
        <Card title="订单明细" size="small" style={{ marginTop: 16 }}>
          <Table
            rowKey="id"
            dataSource={order.items}
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

      {includeAi && <SalesAIInsight aiData={order.ai} />}
    </div>
  );
}
