import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Alert, Button, Card, Checkbox, Descriptions, Empty, Form, Input, Modal, Popconfirm, Select, Space, Spin, Switch, Table, Tag, Typography, message } from "antd";
import {
  ArrowLeftOutlined,
  CopyOutlined,
  DownloadOutlined,
  EditOutlined,
  FileProtectOutlined,
  SendOutlined,
  ShoppingCartOutlined,
} from "@ant-design/icons";
import { convertQuotationToOrder, downloadQuotationPDF, duplicateQuotation, getQuotation, sendQuotation, updateQuotationStatus } from "../../api";
import type { QuotationPDFOptions } from "../../api";
import client from "../../api/client";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { Quotation } from "../../types";
import { CustomerLink, MetricBand, OpportunityLink, SalesModuleShell, SalesStatusTag, money, shortDate } from "./salesUi";

const getDueMeta = (validUntil?: string | null, status?: string) => {
  if (!validUntil || status === "won" || status === "lost") return { text: "-", color: "default", risk: false };
  const due = new Date(validUntil).getTime();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((due - today.getTime()) / (24 * 60 * 60 * 1000));
  if (Number.isNaN(diffDays)) return { text: shortDate(validUntil), color: "default", risk: false };
  if (diffDays < 0) return { text: `已过期 ${Math.abs(diffDays)} 天`, color: "red", risk: true };
  if (diffDays === 0) return { text: "今日到期", color: "red", risk: true };
  if (diffDays <= 7) return { text: `${diffDays} 天后到期`, color: "orange", risk: true };
  return { text: shortDate(validUntil), color: "blue", risk: false };
};

export default function QuotationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [quote, setQuote] = useState<Quotation | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeAi, setIncludeAi] = useState(false);
  const [pdfOpen, setPdfOpen] = useState(false);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [pdfForm] = Form.useForm<QuotationPDFOptions>();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getQuotation(Number(id), includeAi);
      setQuote(resp.data.data);
    } catch (e: any) {
      setError(e.message || "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [id, includeAi]);

  const itemSummary = useMemo(() => {
    const items = quote?.items || [];
    return {
      count: items.length,
      quantity: items.reduce((sum, item) => sum + Number(item.quantity || 0), 0),
      amount: items.reduce((sum, item) => sum + Number(item.total_price || 0), 0),
      untaxedCost: items.reduce((sum, item) => sum + Number(item.untaxed_cost || 0), 0),
      taxedCost: items.reduce((sum, item) => sum + Number(item.taxed_cost || 0), 0),
      profit: items.reduce((sum, item) => sum + Number(item.sales_profit || 0), 0),
    };
  }, [quote]);

  const handleDownloadPDF = async () => {
    if (!quote) return;
    setPdfDownloading(true);
    try {
      const values = await pdfForm.validateFields();
      await downloadQuotationPDF(quote.id, `quotation_${quote.quotation_no || quote.id}.pdf`, values);
      setPdfOpen(false);
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error("下载失败");
    } finally {
      setPdfDownloading(false);
    }
  };

  if (loading) {
    return (
      <SalesModuleShell title="报价详情" activeKey="quotations">
        <Spin style={{ display: "block", margin: "100px auto" }} />
      </SalesModuleShell>
    );
  }
  if (error) {
    return (
      <SalesModuleShell title="报价详情" activeKey="quotations">
        <Alert type="error" message={error} />
      </SalesModuleShell>
    );
  }
  if (!quote) {
    return (
      <SalesModuleShell title="报价详情" activeKey="quotations">
        <Empty description="报价单不存在" />
      </SalesModuleShell>
    );
  }

  const due = getDueMeta(quote.valid_until, quote.status);

  const runAction = async (action: () => Promise<void>, success: string) => {
    setActionLoading(true);
    try {
      await action();
      message.success(success);
      await load();
    } catch {
      message.error("操作失败");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <SalesModuleShell
      title={quote.quotation_no || `报价单 #${quote.id}`}
      subtitle={quote.title || "报价详情、产品明细、审批与转订单动作"}
      activeKey="quotations"
      extra={(
        <>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/quotations")}>返回</Button>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/quotations/${quote.id}/edit`)}>编辑</Button>
          <Button
            icon={<CopyOutlined />}
            loading={actionLoading}
            onClick={() => runAction(async () => {
              const resp = await duplicateQuotation(quote.id);
              navigate(`/sales/quotations/${resp.data.data.id}/edit`);
            }, "已复制为新报价")}
          >
            复制
          </Button>
        </>
      )}
    >
      <MetricBand
        items={[
          { title: "报价金额", value: quote.total_amount || 0, prefix: "¥", precision: 2 },
          { title: "产品行", value: itemSummary.count, suffix: "项" },
          { title: "总数量", value: itemSummary.quantity },
          { title: "明细合计", value: itemSummary.amount, prefix: "¥", precision: 2 },
          { title: "含税成本", value: itemSummary.taxedCost, prefix: "¥", precision: 2 },
          { title: "销售利润", value: itemSummary.profit, prefix: "¥", precision: 2 },
          { title: "状态", value: quote.status },
          { title: "有效期", value: due.text },
        ]}
      />

      {due.risk && quote.status !== "won" && quote.status !== "lost" && (
        <Alert
          showIcon
          type={due.color === "red" ? "error" : "warning"}
          message={`报价有效期提醒：${due.text}`}
          style={{ marginBottom: 12 }}
        />
      )}

      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          {quote.status === "draft" && (
            <Button
              icon={<SendOutlined />}
              loading={actionLoading}
              onClick={() => runAction(() => sendQuotation(quote.id).then(() => undefined), "已标记为已发送")}
            >
              发送报价
            </Button>
          )}
          {quote.status !== "won" && (
            <Popconfirm title="确认转为销售订单?" onConfirm={() => runAction(async () => {
              await convertQuotationToOrder(quote.id);
              navigate("/sales/orders");
            }, "已转为订单")}>
              <Button type="primary" icon={<ShoppingCartOutlined />} loading={actionLoading}>转为订单</Button>
            </Popconfirm>
          )}
          {quote.status !== "lost" && quote.status !== "won" && (
            <Button
              danger
              loading={actionLoading}
              onClick={() => runAction(() => updateQuotationStatus(quote.id, "lost").then(() => undefined), "已标记为丢失")}
            >
              标记丢失
            </Button>
          )}
          <Button icon={<DownloadOutlined />} onClick={() => setPdfOpen(true)}>
            智能PDF
          </Button>
          <Button icon={<FileProtectOutlined />} onClick={async () => {
            try {
              await client.post("/approvals/submit", { doc_type: "quotation", doc_id: quote.id });
              message.success("已提交审批");
            } catch {
              message.error("提交审批失败");
            }
          }}>
            提交审批
          </Button>
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </Space>
      </Card>

      <Modal
        title="自定义智能 PDF"
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
              pdfForm.setFieldsValue({ show_smart_summary: true, show_line_hints: true, show_terms: true, show_notes: true });
            } else if (changed.template === "standard") {
              pdfForm.setFieldsValue({ show_smart_summary: false, show_line_hints: false, show_terms: true, show_notes: true });
            } else if (changed.template === "compact") {
              pdfForm.setFieldsValue({ show_smart_summary: false, show_line_hints: false, show_terms: true, show_notes: false });
            }
          }}
          initialValues={{
            template: "smart",
            company_name: "深圳天允电子有限公司",
            document_title: "智能报价单 / SMART QUOTATION",
            show_smart_summary: true,
            show_line_hints: true,
            show_terms: true,
            show_notes: true,
            terms: [
              "1、以上报价为含税13%，如增加或改变加工工艺、零件、辅料，则须重新核价，并以确认的新单价为准；",
              "2、报价批量含运包费用，供方负责送货到需方指定地点",
              "3、产品付款方式：以合同为准",
              "4、报价有效期：3天",
            ].join("\n"),
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            <Form.Item name="template" label="PDF 形式">
              <Select options={[
                { value: "smart", label: "智能版：含摘要和提示" },
                { value: "standard", label: "标准版：报价和条款" },
                { value: "compact", label: "紧凑版：适合打印" },
              ]} />
            </Form.Item>
            <Form.Item name="company_name" label="抬头公司">
              <Input />
            </Form.Item>
          </div>
          <Form.Item name="document_title" label="文档标题">
            <Input />
          </Form.Item>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8 }}>
            <Form.Item name="show_smart_summary" valuePropName="checked">
              <Checkbox>智能摘要</Checkbox>
            </Form.Item>
            <Form.Item name="show_line_hints" valuePropName="checked">
              <Checkbox>行项目提示</Checkbox>
            </Form.Item>
            <Form.Item name="show_terms" valuePropName="checked">
              <Checkbox>商务条款</Checkbox>
            </Form.Item>
            <Form.Item name="show_notes" valuePropName="checked">
              <Checkbox>报价备注</Checkbox>
            </Form.Item>
          </div>
          <Form.Item name="terms" label="商务条款">
            <Input.TextArea rows={5} />
          </Form.Item>
        </Form>
      </Modal>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 320px", gap: 12, alignItems: "start" }}>
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Card
            title="报价信息"
            size="small"
            extra={(
              <Space>
                <SalesStatusTag value={quote.status} />
                <Tag color={due.color}>{due.text}</Tag>
              </Space>
            )}
          >
            <Descriptions column={2} size="small">
              <Descriptions.Item label="报价单号">{quote.quotation_no || `#${quote.id}`}</Descriptions.Item>
              <Descriptions.Item label="客户"><CustomerLink id={quote.customer_id} /></Descriptions.Item>
              <Descriptions.Item label="标题">{quote.title || "-"}</Descriptions.Item>
              <Descriptions.Item label="有效期">{shortDate(quote.valid_until)}</Descriptions.Item>
              <Descriptions.Item label="总金额">{money(quote.total_amount)}</Descriptions.Item>
              <Descriptions.Item label="关联商机"><OpportunityLink id={quote.opportunity_id} /></Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{quote.notes || "-"}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="报价明细" size="small">
            <Table
              rowKey={(record) => record.id || `${record.product_id}-${record.product_name}`}
              dataSource={quote.items}
              size="small"
              pagination={false}
              columns={[
                {
                  title: "产品",
                  dataIndex: "product_name",
                  ellipsis: true,
                  render: (value: string | null, record) => (
                    <Space direction="vertical" size={0}>
                      <Typography.Text>{value || "-"}</Typography.Text>
                      {record.product_id && (
                        <Typography.Link style={{ fontSize: 12 }} onClick={() => navigate(`/products/${record.product_id}`)}>
                          产品详情 #{record.product_id}
                        </Typography.Link>
                      )}
                    </Space>
                  ),
                },
                { title: "数量", dataIndex: "quantity", width: 90 },
                { title: "单价", dataIndex: "unit_price", width: 120, render: (value: number | null) => value != null ? money(value) : "-" },
                { title: "小计", dataIndex: "total_price", width: 130, render: (value: number | null) => value != null ? money(value) : "-" },
                { title: "成本", dataIndex: "cost_price", width: 120, render: (value: number | null) => value != null ? money(value) : "-" },
                { title: "未税成本", dataIndex: "untaxed_cost", width: 130, render: (value: number | null) => value != null ? money(value) : "-" },
                { title: "含税成本", dataIndex: "taxed_cost", width: 130, render: (value: number | null) => value != null ? money(value) : "-" },
                {
                  title: "销售利润",
                  dataIndex: "sales_profit",
                  width: 130,
                  render: (value: number | null) => (
                    value != null ? <Typography.Text type={value < 0 ? "danger" : undefined}>{money(value)}</Typography.Text> : "-"
                  ),
                },
                { title: "备注", dataIndex: "notes", width: 180, ellipsis: true, render: (value: string | null) => value || "-" },
              ]}
              summary={() => (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0}><Typography.Text strong>合计</Typography.Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={1}>{itemSummary.quantity}</Table.Summary.Cell>
                  <Table.Summary.Cell index={2}>-</Table.Summary.Cell>
                  <Table.Summary.Cell index={3}><Typography.Text strong>{money(itemSummary.amount)}</Typography.Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={4}>-</Table.Summary.Cell>
                  <Table.Summary.Cell index={5}>{money(itemSummary.untaxedCost)}</Table.Summary.Cell>
                  <Table.Summary.Cell index={6}>{money(itemSummary.taxedCost)}</Table.Summary.Cell>
                  <Table.Summary.Cell index={7}>
                    <Typography.Text strong type={itemSummary.profit < 0 ? "danger" : undefined}>
                      {money(itemSummary.profit)}
                    </Typography.Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={8}>-</Table.Summary.Cell>
                </Table.Summary.Row>
              )}
              scroll={{ x: "max-content" }}
            />
          </Card>

          {includeAi && <SalesAIInsight aiData={quote.ai} />}
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
          <Card size="small" title="下一步动作">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              {quote.status === "draft" && <Alert showIcon type="info" message="建议先确认有效期和产品行，再发送给客户。" />}
              {quote.status === "sent" && <Alert showIcon type="success" message="已发送报价，下一步建议跟进客户反馈并转订单。" />}
              {quote.status === "won" && <Alert showIcon type="success" message="报价已成交，进入订单执行链路。" />}
              {quote.status === "lost" && <Alert showIcon type="warning" message="报价已丢失，建议记录原因并复制生成新版本。" />}
              <Button block icon={<EditOutlined />} onClick={() => navigate(`/sales/quotations/${quote.id}/edit`)}>编辑报价</Button>
              <Button block icon={<CopyOutlined />} onClick={() => runAction(async () => {
                const resp = await duplicateQuotation(quote.id);
                navigate(`/sales/quotations/${resp.data.data.id}/edit`);
              }, "已复制为新报价")}>复制新版本</Button>
              <Button block onClick={() => navigate(`/customers/${quote.customer_id}`)}>查看客户</Button>
            </Space>
          </Card>
        </Space>
      </div>
    </SalesModuleShell>
  );
}
