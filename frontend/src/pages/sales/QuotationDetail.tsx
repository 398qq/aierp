import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Alert,
  Button,
  Checkbox,
  Descriptions,
  Divider,
  Empty,
  Input,
  Modal,
  Popconfirm,
  Segmented,
  Select,
  Space,
  Spin,
  Switch,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import type { ProColumns } from "@ant-design/pro-components";
import { ProCard, ProForm, ProTable } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import {
  ArrowLeftOutlined,
  CopyOutlined,
  DollarOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  FileProtectOutlined,
  PrinterOutlined,
  SendOutlined,
  ShoppingCartOutlined,
} from "@ant-design/icons";
import {
  convertQuotationToOrder,
  downloadQuotationPDF,
  duplicateQuotation,
  getCustomer,
  getQuotation,
  sendQuotation,
  updateQuotationStatus,
  getApiErrorMessage,
} from "../../api";
import type { QuotationPDFOptions } from "../../api";
import client from "../../api/client";
import SalesAIInsight from "../../components/sales/SalesAIInsight";
import type { Quotation, QuotationItem } from "../../types";
import {
  CustomerLink,
  ErpStatusTimeline,
  MetricBand,
  OpportunityLink,
  SalesModuleShell,
  SalesStatusTag,
  money,
  shortDate,
} from "./salesUi";
import { SalesQuotationPrint } from "./SalesQuotationPrint";

const getDueMeta = (validUntil?: string | null, status?: string) => {
  if (!validUntil || status === "won" || status === "lost")
    return { text: "-", color: "default", risk: false };
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
  const [showCostColumns, setShowCostColumns] = useState(false);
  const [viewMode, setViewMode] = useState<"internal" | "customer">("internal");
  const [pdfOpen, setPdfOpen] = useState(false);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [customerName, setCustomerName] = useState("");
  const [pdfForm] = ProForm.useForm<QuotationPDFOptions>();

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

  useEffect(() => {
    if (!quote?.customer_id) {
      setCustomerName("");
      return;
    }
    getCustomer(quote.customer_id)
      .then((resp) => setCustomerName(resp.data.data.name || ""))
      .catch(() => setCustomerName(""));
  }, [quote?.customer_id]);

  useEffect(() => {
    if (!pdfOpen || !customerName || pdfForm.isFieldTouched("company_name")) return;
    pdfForm.setFieldValue("company_name", customerName);
  }, [customerName, pdfForm, pdfOpen]);

  const itemSummary = useMemo(() => {
    const items = quote?.items || [];
    const amount = items.reduce((sum, item) => sum + Number(item.total_price || 0), 0);
    const profit = items.reduce((sum, item) => sum + Number(item.sales_profit || 0), 0);
    const untaxedAmount = items.reduce((sum, item) => {
      const gross = Number(item.total_price || 0);
      const rate = Number(item.tax_rate || 0) / 100;
      return sum + (rate > 0 ? gross / (1 + rate) : gross);
    }, 0);
    return {
      count: items.length,
      quantity: items.reduce((sum, item) => sum + Number(item.quantity || 0), 0),
      amount,
      untaxedCost: items.reduce((sum, item) => sum + Number(item.untaxed_cost || 0), 0),
      taxedCost: items.reduce((sum, item) => sum + Number(item.taxed_cost || 0), 0),
      profit,
      profitMargin: amount > 0 ? (profit / amount) * 100 : 0,
      untaxedAmount,
      taxAmount: Math.max(amount - untaxedAmount, 0),
      missingCostLines: items.filter(
        (item) => item.cost_price == null || Number(item.cost_price) <= 0,
      ).length,
      missingTaxLines: items.filter((item) => item.tax_rate == null).length,
    };
  }, [quote]);

  const handleDownloadPDF = async () => {
    if (!quote) return;
    setPdfDownloading(true);
    try {
      const values = await pdfForm.validateFields();
      await downloadQuotationPDF(
        quote.id,
        `QUOTATION_${quote.quotation_no || quote.id}.pdf`,
        values,
      );
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
  const isCustomerView = viewMode === "customer";

  const runAction = async (action: () => Promise<void>, success: string) => {
    setActionLoading(true);
    try {
      await action();
      message.success(success);
      await load();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "操作失败"));
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <SalesModuleShell
      title={quote.quotation_no || `报价单 #${quote.id}`}
      subtitle={quote.title || "报价详情、产品明细、审批与转订单动作"}
      activeKey="quotations"
      extra={
        <>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/quotations")}>
            返回
          </Button>
          {quote.status === "draft" ? (
            <Button
              icon={<EditOutlined />}
              onClick={() => navigate(`/sales/quotations/${quote.id}/edit`)}
            >
              编辑
            </Button>
          ) : null}
          <Button
            icon={<CopyOutlined />}
            loading={actionLoading}
            onClick={() =>
              runAction(async () => {
                const resp = await duplicateQuotation(quote.id);
                navigate(`/sales/quotations/${resp.data.data.id}/edit`);
              }, "已复制为新报价")
            }
          >
            复制
          </Button>
          <Segmented
            size="small"
            value={viewMode}
            onChange={(value) => {
              const next = value as "internal" | "customer";
              setViewMode(next);
              if (next === "customer") setShowCostColumns(false);
            }}
            options={[
              { label: "内部经营", value: "internal" },
              { label: "客户视图", value: "customer" },
            ]}
          />
        </>
      }
    >
      <SalesQuotationPrint quote={quote} customerName={customerName} />
      <MetricBand
        items={[
          { title: "价税合计", value: quote.total_amount || 0, prefix: "¥", precision: 2 },
          ...(!isCustomerView
            ? [
                {
                  title: "销售利润",
                  value: itemSummary.profit,
                  prefix: "¥",
                  precision: 2,
                },
              ]
            : []),
          ...(!isCustomerView
            ? [
                {
                  title: "毛利率",
                  value: itemSummary.profitMargin,
                  suffix: "%",
                  precision: 1,
                },
              ]
            : []),
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

      <ProCard size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          {quote.status === "draft" && (
            <Button
              icon={<SendOutlined />}
              loading={actionLoading}
              onClick={() =>
                runAction(() => sendQuotation(quote.id).then(() => undefined), "已标记为已发送")
              }
            >
              发送报价
            </Button>
          )}
          {quote.status === "sent" && (
            <Button
              type="primary"
              loading={actionLoading}
              onClick={() =>
                runAction(
                  () => updateQuotationStatus(quote.id, "accepted").then(() => undefined),
                  "已记录客户接受报价",
                )
              }
            >
              客户已接受
            </Button>
          )}
          {quote.status === "accepted" && (
            <Popconfirm
              title="确认转为销售订单?"
              onConfirm={() =>
                runAction(async () => {
                  await convertQuotationToOrder(quote.id);
                  navigate("/sales/orders");
                }, "已转为订单")
              }
            >
              <Button type="primary" icon={<ShoppingCartOutlined />} loading={actionLoading}>
                转为订单
              </Button>
            </Popconfirm>
          )}
          {quote.status === "sent" && (
            <Button
              danger
              loading={actionLoading}
              onClick={() =>
                runAction(
                  () => updateQuotationStatus(quote.id, "lost").then(() => undefined),
                  "已标记为丢失",
                )
              }
            >
              标记丢失
            </Button>
          )}
          <Button
            icon={<DownloadOutlined />}
            onClick={() => {
              if (customerName && !pdfForm.getFieldValue("company_name")) {
                pdfForm.setFieldValue("company_name", customerName);
              }
              setPdfOpen(true);
            }}
          >
            智能PDF
          </Button>
          <Button icon={<PrinterOutlined />} onClick={() => window.print()}>
            打印报价单
          </Button>
          {!isCustomerView && quote.status === "draft" ? (
            <Button
              icon={<FileProtectOutlined />}
              onClick={async () => {
                try {
                  await client.post("/approvals/submit", {
                    doc_type: "quotation",
                    doc_id: quote.id,
                  });
                  message.success("已提交审批");
                } catch (e: unknown) {
                  message.error(getApiErrorMessage(e, "提交审批失败"));
                }
              }}
            >
              提交审批
            </Button>
          ) : null}
          {!isCustomerView && (
            <Space>
              <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
              <span style={{ fontSize: 13 }}>AI</span>
            </Space>
          )}
        </Space>
      </ProCard>

      <Modal
        title="自定义智能 PDF"
        open={pdfOpen}
        onCancel={() => setPdfOpen(false)}
        onOk={handleDownloadPDF}
        confirmLoading={pdfDownloading}
        okText="下载 PDF"
        width={680}
      >
        <ProForm
          form={pdfForm}
          layout="vertical"
          submitter={false}
          onValuesChange={(changed) => {
            if (!("template" in changed)) return;
            if (changed.template === "smart") {
              pdfForm.setFieldsValue({
                show_smart_summary: true,
                show_line_hints: true,
                show_terms: true,
                show_notes: true,
                show_signature: true,
              });
            } else if (changed.template === "standard") {
              pdfForm.setFieldsValue({
                show_smart_summary: false,
                show_line_hints: false,
                show_terms: true,
                show_notes: true,
                show_signature: true,
              });
            } else if (changed.template === "compact") {
              pdfForm.setFieldsValue({
                show_smart_summary: false,
                show_line_hints: false,
                show_terms: true,
                show_notes: false,
                show_signature: false,
              });
            }
          }}
          initialValues={{
            template: "smart",
            company_name: customerName,
            document_title: "正式报价单 / QUOTATION",
            show_smart_summary: true,
            show_line_hints: true,
            show_terms: true,
            show_notes: true,
            show_internal_metrics: false,
            show_signature: true,
            terms: [
              "1、以上报价为含税13%，如增加或改变加工工艺、零件、辅料，则须重新核价，并以确认的新单价为准；",
              "2、报价批量含运包费用，供方负责送货到需方指定地点",
              "3、产品付款方式：以合同为准",
              "4、报价有效期：3天",
            ].join("\n"),
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            <ProForm.Item name="template" label="PDF 形式">
              <Select
                options={[
                  { value: "smart", label: "智能版：含摘要和提示" },
                  { value: "standard", label: "标准版：报价和条款" },
                  { value: "compact", label: "紧凑版：适合打印" },
                ]}
              />
            </ProForm.Item>
            <ProForm.Item name="company_name" label="抬头公司">
              <Input placeholder="默认取客户公司名称" />
            </ProForm.Item>
          </div>
          <ProForm.Item name="document_title" label="文档标题">
            <Input />
          </ProForm.Item>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            <ProForm.Item name="prepared_by" label="报价经办">
              <Input placeholder="销售 / 商务负责人" />
            </ProForm.Item>
            <ProForm.Item name="contact_phone" label="联系电话">
              <Input placeholder="对外联系号码" />
            </ProForm.Item>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 8,
            }}
          >
            <ProForm.Item name="show_smart_summary" valuePropName="checked">
              <Checkbox>智能摘要</Checkbox>
            </ProForm.Item>
            <ProForm.Item name="show_line_hints" valuePropName="checked">
              <Checkbox>行项目提示</Checkbox>
            </ProForm.Item>
            <ProForm.Item name="show_terms" valuePropName="checked">
              <Checkbox>商务条款</Checkbox>
            </ProForm.Item>
            <ProForm.Item name="show_notes" valuePropName="checked">
              <Checkbox>报价备注</Checkbox>
            </ProForm.Item>
            <ProForm.Item name="show_signature" valuePropName="checked">
              <Checkbox>签署确认栏</Checkbox>
            </ProForm.Item>
            {!isCustomerView ? (
              <ProForm.Item name="show_internal_metrics" valuePropName="checked">
                <Checkbox>内部成本毛利</Checkbox>
              </ProForm.Item>
            ) : null}
          </div>
          <Alert
            showIcon
            type="warning"
            message="勾选“内部成本毛利”会把含税成本、销售毛利和毛利率写入 PDF，请仅用于内部评审。"
            style={{ marginBottom: 12 }}
          />
          <ProForm.Item name="terms" label="商务条款">
            <Input.TextArea rows={5} />
          </ProForm.Item>
        </ProForm>
      </Modal>

      <div className="erp-detail-two-column">
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <ProCard
            title="报价信息"
            size="small"
            extra={
              <Space>
                <SalesStatusTag value={quote.status} />
                <StatusTag tone={due.color}>{due.text}</StatusTag>
              </Space>
            }
          >
            <Descriptions column={2} size="small">
              <Descriptions.Item label="报价单号">
                {quote.quotation_no || `#${quote.id}`}
              </Descriptions.Item>
              <Descriptions.Item label="客户">
                <CustomerLink id={quote.customer_id} />
              </Descriptions.Item>
              <Descriptions.Item label="标题">{quote.title || "-"}</Descriptions.Item>
              <Descriptions.Item label="有效期">{shortDate(quote.valid_until)}</Descriptions.Item>
              <Descriptions.Item label="价税合计">{money(quote.total_amount)}</Descriptions.Item>
              <Descriptions.Item label="关联商机">
                <OpportunityLink id={quote.opportunity_id} />
              </Descriptions.Item>
              <Descriptions.Item label="币种">{quote.currency || "CNY"}</Descriptions.Item>
              <Descriptions.Item label="贸易条款">{quote.incoterms || "-"}</Descriptions.Item>
              <Descriptions.Item label="付款条件">{quote.payment_terms || "-"}</Descriptions.Item>
              <Descriptions.Item label="整单折扣">
                {quote.discount_rate != null ? `${quote.discount_rate}%` : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="折扣金额">
                {quote.discount_amount != null ? money(quote.discount_amount) : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">{shortDate(quote.created_at)}</Descriptions.Item>
              <Descriptions.Item label="最后更新">{shortDate(quote.updated_at)}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>
                {quote.notes || "-"}
              </Descriptions.Item>
            </Descriptions>
          </ProCard>

          <ProCard
            title="报价明细"
            size="small"
            extra={
              !isCustomerView ? (
                <Tooltip title={showCostColumns ? "隐藏成本列" : "显示成本列"}>
                  <Button
                    size="small"
                    type={showCostColumns ? "primary" : "default"}
                    icon={showCostColumns ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                    onClick={() => setShowCostColumns((prev) => !prev)}
                  >
                    {showCostColumns ? "隐藏成本" : "查看成本"}
                  </Button>
                </Tooltip>
              ) : (
                <Typography.Text type="secondary">客户可见字段</Typography.Text>
              )
            }
          >
            <ProTable
              rowKey={(record) => record.id || `${record.product_id}-${record.product_name}`}
              dataSource={quote.items}
              size="small"
              pagination={false}
              columns={
                [
                  {
                    title: "序号",
                    width: 56,
                    fixed: "left",
                    align: "center" as const,
                    render: (_: unknown, __: QuotationItem, index: number) => index + 1,
                  },
                  {
                    title: "产品 / 规格",
                    dataIndex: "product_name",
                    ellipsis: true,
                    width: 240,
                    fixed: "left",
                    render: (value: string | null, record) => (
                      <Space direction="vertical" size={0}>
                        <Typography.Text>
                          {record.customer_product_name || value || "-"}
                        </Typography.Text>
                        {record.product_id && (
                          <Typography.Link
                            style={{ fontSize: 12 }}
                            onClick={() => navigate(`/products/${record.product_id}`)}
                          >
                            查看产品资料
                          </Typography.Link>
                        )}
                      </Space>
                    ),
                  },
                  {
                    title: "客户料号",
                    dataIndex: "customer_part_no",
                    width: 170,
                    render: (value: string | null) =>
                      value ? <Typography.Text copyable>{value}</Typography.Text> : "-",
                  },
                  { title: "数量", dataIndex: "quantity", width: 70, align: "right" as const },
                  {
                    title: "单位",
                    dataIndex: "unit",
                    width: 70,
                    render: (value: string | null) => value || "-",
                  },
                  {
                    title: "批次 / D/C",
                    dataIndex: "datecode",
                    width: 140,
                    render: (value: string | null) => value || "-",
                  },
                  {
                    title: "交期",
                    dataIndex: "lead_time",
                    width: 120,
                    render: (value: string | null) => value || "-",
                  },
                  {
                    title: "含税单价",
                    dataIndex: "unit_price",
                    width: 110,
                    align: "right" as const,
                    render: (value: number | null) => (value != null ? money(value) : "-"),
                  },
                  {
                    title: "折扣",
                    dataIndex: "discount_rate",
                    width: 75,
                    align: "right" as const,
                    render: (value: number | null) => (value != null ? `${value}%` : "-"),
                  },
                  {
                    title: "税率",
                    dataIndex: "tax_rate",
                    width: 75,
                    align: "right" as const,
                    render: (value: number | null) =>
                      value != null ? (
                        `${value}%`
                      ) : (
                        <Typography.Text type="warning">未设置</Typography.Text>
                      ),
                  },
                  {
                    title: "未税金额",
                    width: 110,
                    align: "right" as const,
                    render: (_: unknown, record) => {
                      const gross = Number(record.total_price || 0);
                      const rate = Number(record.tax_rate || 0) / 100;
                      return money(rate > 0 ? gross / (1 + rate) : gross);
                    },
                  },
                  {
                    title: "税额",
                    width: 100,
                    align: "right" as const,
                    render: (_: unknown, record) => {
                      const gross = Number(record.total_price || 0);
                      const rate = Number(record.tax_rate || 0) / 100;
                      return money(rate > 0 ? gross - gross / (1 + rate) : 0);
                    },
                  },
                  {
                    title: "价税合计",
                    dataIndex: "total_price",
                    width: 120,
                    align: "right" as const,
                    render: (value: number | null) =>
                      value != null ? (
                        <Typography.Text strong>{money(value)}</Typography.Text>
                      ) : (
                        "-"
                      ),
                  },
                  ...(!isCustomerView && showCostColumns
                    ? [
                        {
                          title: "含税成本单价",
                          dataIndex: "cost_price",
                          width: 130,
                          align: "right" as const,
                          render: (value: number | null) => (value != null ? money(value) : "-"),
                        },
                        {
                          title: "未税成本",
                          dataIndex: "untaxed_cost",
                          width: 110,
                          align: "right" as const,
                          render: (value: number | null) => (value != null ? money(value) : "-"),
                        },
                        {
                          title: "含税成本",
                          dataIndex: "taxed_cost",
                          width: 110,
                          align: "right" as const,
                          render: (value: number | null) => (value != null ? money(value) : "-"),
                        },
                        {
                          title: "销售利润",
                          dataIndex: "sales_profit",
                          width: 110,
                          align: "right" as const,
                          render: (value: number | null) =>
                            value != null ? (
                              <Typography.Text type={value < 0 ? "danger" : undefined}>
                                {money(value)}
                              </Typography.Text>
                            ) : (
                              "-"
                            ),
                        },
                        {
                          title: "毛利率",
                          width: 90,
                          align: "right" as const,
                          render: (_: unknown, record: QuotationItem) => {
                            const amount = Number(record.total_price || 0);
                            const margin =
                              amount > 0 ? (Number(record.sales_profit || 0) / amount) * 100 : 0;
                            return (
                              <Typography.Text type={margin < 10 ? "warning" : undefined}>
                                {margin.toFixed(1)}%
                              </Typography.Text>
                            );
                          },
                        },
                      ]
                    : []),
                  {
                    title: "备注",
                    dataIndex: "notes",
                    width: 160,
                    ellipsis: true,
                    render: (value: string | null) => value || "-",
                  },
                ] as ProColumns<QuotationItem>[]
              }
              summary={() => (
                <ProTable.Summary.Row>
                  <ProTable.Summary.Cell
                    index={0}
                    colSpan={!isCustomerView && showCostColumns ? 19 : 14}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "flex-end",
                        gap: 24,
                        paddingRight: 8,
                      }}
                    >
                      <Typography.Text>
                        共 <strong>{itemSummary.count}</strong> 行 / 数量{" "}
                        <strong>{itemSummary.quantity}</strong>
                      </Typography.Text>
                      <Typography.Text>
                        未税金额 <strong>{money(itemSummary.untaxedAmount)}</strong>
                      </Typography.Text>
                      <Typography.Text>
                        税额 <strong>{money(itemSummary.taxAmount)}</strong>
                      </Typography.Text>
                      <Typography.Text strong>
                        价税合计：{money(itemSummary.amount)}
                      </Typography.Text>
                    </div>
                  </ProTable.Summary.Cell>
                </ProTable.Summary.Row>
              )}
              scroll={{ x: "max-content" }}
            />
          </ProCard>

          {includeAi && !isCustomerView && <SalesAIInsight aiData={quote.ai} />}
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
          <ProCard
            size="small"
            title={
              <>
                <DollarOutlined /> {isCustomerView ? "报价金额" : "成本与利润"}
              </>
            }
          >
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">未税销售额</Typography.Text>
                <Typography.Text>{money(itemSummary.untaxedAmount)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">销项税额</Typography.Text>
                <Typography.Text>{money(itemSummary.taxAmount)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text strong>价税合计</Typography.Text>
                <Typography.Text strong>{money(itemSummary.amount)}</Typography.Text>
              </div>
              {!isCustomerView && (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                    <Typography.Text type="secondary">未税成本</Typography.Text>
                    <Typography.Text>{money(itemSummary.untaxedCost)}</Typography.Text>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                    <Typography.Text type="secondary">含税成本</Typography.Text>
                    <Typography.Text>{money(itemSummary.taxedCost)}</Typography.Text>
                  </div>
                </>
              )}
              <Divider style={{ margin: "6px 0" }} />
              {!isCustomerView && (
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <Typography.Text strong>销售利润</Typography.Text>
                  <Typography.Text strong type={itemSummary.profit < 0 ? "danger" : undefined}>
                    {money(itemSummary.profit)}
                  </Typography.Text>
                </div>
              )}
              {!isCustomerView && (
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <Typography.Text strong>毛利率</Typography.Text>
                  <Typography.Text
                    strong
                    type={
                      itemSummary.profitMargin < 0
                        ? "danger"
                        : itemSummary.profitMargin < 10
                          ? "warning"
                          : undefined
                    }
                  >
                    {itemSummary.profitMargin.toFixed(1)}%
                  </Typography.Text>
                </div>
              )}
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">产品行数</Typography.Text>
                <Typography.Text>
                  {itemSummary.count} 项 / {itemSummary.quantity} 件
                </Typography.Text>
              </div>
            </Space>
          </ProCard>

          {!isCustomerView && (
            <ProCard size="small" title="报价风险控制">
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                {due.risk ? (
                  <Alert
                    showIcon
                    type={due.color === "red" ? "error" : "warning"}
                    message={`有效期风险：${due.text}`}
                  />
                ) : null}
                {itemSummary.missingCostLines > 0 ? (
                  <Alert
                    showIcon
                    type="warning"
                    message={`${itemSummary.missingCostLines} 行未维护成本，毛利结果可能不准确`}
                  />
                ) : null}
                {itemSummary.missingTaxLines > 0 ? (
                  <Alert
                    showIcon
                    type="warning"
                    message={`${itemSummary.missingTaxLines} 行未设置税率`}
                  />
                ) : null}
                {itemSummary.profitMargin < 10 ? (
                  <Alert
                    showIcon
                    type="error"
                    message={`毛利率 ${itemSummary.profitMargin.toFixed(1)}%，建议审批后发送`}
                  />
                ) : null}
                {!due.risk &&
                itemSummary.missingCostLines === 0 &&
                itemSummary.missingTaxLines === 0 &&
                itemSummary.profitMargin >= 10 ? (
                  <Alert showIcon type="success" message="价格、税率、成本和有效期检查正常" />
                ) : null}
              </Space>
            </ProCard>
          )}

          <ProCard size="small" title="状态流转">
            <ErpStatusTimeline
              currentStatus={quote.status}
              steps={[
                { key: "draft", label: "草稿" },
                { key: "sent", label: "已发送" },
                { key: "accepted", label: "客户接受" },
                { key: "won", label: "已转订单" },
              ]}
              createdAt={quote.created_at}
              lostStatus="lost"
            />
          </ProCard>

          <ProCard size="small" title="下一步动作">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              {quote.status === "draft" && (
                <Alert showIcon type="info" message="建议先确认有效期和产品行，再发送给客户。" />
              )}
              {quote.status === "sent" && (
                <Alert showIcon type="info" message="已发送报价，请跟进并记录客户接受或拒绝。" />
              )}
              {quote.status === "accepted" && (
                <Alert showIcon type="success" message="客户已接受报价，可以转换为销售订单。" />
              )}
              {quote.status === "won" && (
                <Alert showIcon type="success" message="报价已成交，进入订单执行链路。" />
              )}
              {quote.status === "lost" && (
                <Alert
                  showIcon
                  type="warning"
                  message="报价已丢失，建议记录原因并复制生成新版本。"
                />
              )}
              {quote.status === "draft" ? (
                <Button
                  block
                  icon={<EditOutlined />}
                  onClick={() => navigate(`/sales/quotations/${quote.id}/edit`)}
                >
                  编辑报价
                </Button>
              ) : null}
              <Button
                block
                icon={<CopyOutlined />}
                onClick={() =>
                  runAction(async () => {
                    const resp = await duplicateQuotation(quote.id);
                    navigate(`/sales/quotations/${resp.data.data.id}/edit`);
                  }, "已复制为新报价")
                }
              >
                复制新版本
              </Button>
              <Button block onClick={() => navigate(`/customers/${quote.customer_id}`)}>
                查看客户
              </Button>
            </Space>
          </ProCard>
        </Space>
      </div>
    </SalesModuleShell>
  );
}
