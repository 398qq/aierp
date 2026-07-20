import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, DatePicker, Form, Input, InputNumber, Select, Space, Statistic, Table, Tag, Typography, message } from "antd";
import { StatusTag } from "../../ui";
import { ArrowLeftOutlined, CalculatorOutlined, DeleteOutlined, FileDoneOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import { getProductCustomerCodes, getQuotation, createQuotation, updateQuotation } from "../../api";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import FormAIWarning from "../../components/sales/FormAIWarning";
import { CustomerSelect, OpportunitySelect, ProductSelect, SalesModuleShell, money } from "./salesUi";

type QuoteItemForm = {
  product_id?: number;
  product_name?: string;
  customer_part_no?: string;
  customer_product_name?: string;
  quantity?: number;
  unit?: string;
  unit_price?: number;
  tax_rate?: number;
  discount_rate?: number;
  total_price?: number;
  cost_price?: number;
  untaxed_cost?: number;
  taxed_cost?: number;
  sales_profit?: number;
  datecode?: string | null;
  lead_time?: string;
  notes?: string;
};

const toNumber = (value: unknown) => Number(value || 0);
const COST_TAX_RATE = 0.13;
const formatPercent = (value: number) => `${value.toFixed(2)}%`;
const STATUS_OPTIONS = [
  { value: "draft", label: "草稿" },
  { value: "sent", label: "已发送" },
  { value: "won", label: "成交" },
  { value: "lost", label: "丢失" },
];

const sectionTitleStyle = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  fontWeight: 600,
} as const;

const compactFormGrid = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  columnGap: 16,
  rowGap: 2,
} as const;

const labelTextStyle = { fontSize: 12, color: "#667085" } as const;

export default function QuotationForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const isEdit = !!id;
  const watchedItems = Form.useWatch("items", form) as QuoteItemForm[] | undefined;
  const watchedTotal = Form.useWatch("total_amount", form) as number | undefined;
  const watchedCustomerId = Form.useWatch("customer_id", form) as number | undefined;

  const summary = useMemo(() => {
    const items = watchedItems || [];
    const validItems = items.filter((item) => item?.product_id || item?.product_name);
    const amount = items.reduce((sum, item) => sum + toNumber(item?.total_price), 0);
    const untaxedCost = items.reduce((sum, item) => sum + toNumber(item?.untaxed_cost), 0);
    const taxedCost = items.reduce((sum, item) => sum + toNumber(item?.taxed_cost), 0);
    const profit = items.reduce((sum, item) => sum + toNumber(item?.sales_profit), 0);
    const quantity = items.reduce((sum, item) => sum + toNumber(item?.quantity), 0);
    return { itemCount: validItems.length, amount, untaxedCost, taxedCost, profit, quantity };
  }, [watchedItems]);

  useEffect(() => {
    if (isEdit) {
      getQuotation(Number(id)).then((r) => {
        const q = r.data.data;
        form.setFieldsValue({
          ...q,
          valid_until: q.valid_until ? dayjs(q.valid_until) : null,
          items: q.items?.length ? q.items : [{}],
        });
        setFormValues(q as unknown as Record<string, unknown>);
      });
    } else {
      const customerId = Number(searchParams.get("customer_id"));
      const opportunityId = Number(searchParams.get("opportunity_id"));
      if (customerId) form.setFieldValue("customer_id", customerId);
      if (opportunityId) form.setFieldValue("opportunity_id", opportunityId);
    }
  }, [id, isEdit, searchParams, form]);

  useEffect(() => {
    if (Math.abs(toNumber(watchedTotal) - summary.amount) > 0.0001) {
      form.setFieldValue("total_amount", summary.amount);
    }
  }, [form, summary.amount, watchedTotal]);

  const syncLineTotals = () => {
    const items = [...(form.getFieldValue("items") || [])] as QuoteItemForm[];
    let changed = false;
    const next = items.map((item) => {
      const quantity = toNumber(item?.quantity || 1);
      const unitPrice = toNumber(item?.unit_price);
      const discountRate = Math.min(Math.max(toNumber(item?.discount_rate), 0), 100);
      const totalPrice = quantity * unitPrice * (1 - discountRate / 100);
      const costPrice = toNumber(item?.cost_price);
      const taxedCost = quantity * costPrice;
      const untaxedCost = taxedCost / (1 + COST_TAX_RATE);
      const salesProfit = totalPrice - taxedCost;
      if (
        item?.total_price !== totalPrice
        || item?.untaxed_cost !== untaxedCost
        || item?.taxed_cost !== taxedCost
        || item?.sales_profit !== salesProfit
      ) {
        changed = true;
      }
      return {
        ...item,
        quantity,
        tax_rate: item.tax_rate ?? 13,
        discount_rate: discountRate,
        total_price: totalPrice,
        cost_price: costPrice,
        untaxed_cost: untaxedCost,
        taxed_cost: taxedCost,
        sales_profit: salesProfit,
      };
    });
    if (changed) form.setFieldValue("items", next);
  };

  const onFinish = async (values: Record<string, unknown>) => {
    const items = ((values.items || []) as QuoteItemForm[])
      .filter((item) => item.product_id || item.product_name);
    if (!items.length) {
      message.warning("至少添加一条产品报价行");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        ...values,
        valid_until: values.valid_until ? (values.valid_until as Dayjs).toISOString() : null,
        total_amount: summary.amount,
        items,
      };
      if (isEdit) {
        await updateQuotation(Number(id), payload);
        message.success("报价单已更新");
      } else {
        await createQuotation(payload);
        message.success("报价单已创建");
      }
      navigate("/sales/quotations");
    } catch (err: any) {
      message.error(err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "保存失败");
    } finally {
      setLoading(false);
    }
  };

  const marginRate = summary.amount ? (summary.profit / summary.amount) * 100 : 0;
  const marginColor = marginRate >= 20 ? "green" : marginRate >= 8 ? "orange" : marginRate >= 0 ? "blue" : "red";

  return (
    <SalesModuleShell
      title={isEdit ? "编辑报价单" : "新增报价单"}
      subtitle="按 ERP 单据录入报价抬头、产品明细、成本毛利与交易条款"
      activeKey="quotations"
      extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/quotations")}>返回</Button>}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        onValuesChange={(_, values) => {
          setFormValues(values);
          syncLineTotals();
        }}
        requiredMark={false}
        initialValues={{ status: "draft", items: [{}], valid_until: dayjs().add(3, "day"), notes: "" }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 320px", gap: 16, alignItems: "start" }}>
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Card
              size="small"
              title={<span style={sectionTitleStyle}><FileDoneOutlined /> 单据抬头</span>}
              extra={<StatusTag tone={summary.itemCount > 0 ? "processing" : "neutral"}>销售报价单</StatusTag>}
              style={{ borderColor: "#d9e2ec" }}
            >
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 16,
                paddingBottom: 12,
                marginBottom: 12,
                borderBottom: "1px solid #eef2f7",
              }}>
                <div>
                  <Typography.Title level={4} style={{ margin: 0 }}>销售报价单</Typography.Title>
                  <Typography.Text type="secondary">客户、商机、报价号、有效期在抬头集中维护</Typography.Text>
                </div>
                <Space wrap>
                  <StatusTag tone="info">含税报价</StatusTag>
                  <StatusTag tone="info">税率 {formatPercent(COST_TAX_RATE * 100)}</StatusTag>
                </Space>
              </div>

              <FormAIWarning entityType="quotation" formData={formValues} />

              <div style={compactFormGrid}>
                <Form.Item name="customer_id" label="客户" rules={[{ required: true, message: "请选择客户" }]}>
                  <CustomerSelect />
                </Form.Item>
                <Form.Item name="opportunity_id" label="关联商机">
                  <OpportunitySelect
                    customerId={watchedCustomerId}
                    onOpportunityPicked={(opportunity) => {
                      if (!form.getFieldValue("customer_id")) {
                        form.setFieldValue("customer_id", opportunity.customer_id);
                      }
                      if (!form.getFieldValue("title")) {
                        form.setFieldValue("title", opportunity.title);
                      }
                    }}
                  />
                </Form.Item>
                <Form.Item name="quotation_no" label="报价单号">
                  <Input placeholder="系统自动生成 / 手工编号" />
                </Form.Item>
                <Form.Item name="status" label="单据状态">
                  <Select options={STATUS_OPTIONS} />
                </Form.Item>
                <Form.Item name="title" label="报价主题">
                  <Input placeholder="例如：华东客户 MCU 批量报价" />
                </Form.Item>
                <Form.Item
                  name="valid_until"
                  label="报价有效期"
                  rules={[{
                    validator: (_, value: Dayjs | null) => {
                      if (!value || value.endOf("day").isAfter(dayjs())) return Promise.resolve();
                      return Promise.reject(new Error("有效期不能早于今天"));
                    },
                  }]}
                >
                  <DatePicker style={{ width: "100%" }} />
                </Form.Item>
              </div>
            </Card>

            <Card
              size="small"
              title={<span style={sectionTitleStyle}><CalculatorOutlined /> 报价明细</span>}
              extra={(
                <Space size={8}>
                  <StatusTag tone={summary.itemCount > 0 ? "info" : "danger"}>{summary.itemCount} 行</StatusTag>
                  <StatusTag>数量 {summary.quantity}</StatusTag>
                </Space>
              )}
              style={{ borderColor: "#d9e2ec" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
                <Typography.Text type="secondary">
                  明细行按含税成本单价自动计算未税成本、进项税、含税成本、销售毛利与毛利率。
                </Typography.Text>
                <Typography.Text strong>明细合计：{money(summary.amount)}</Typography.Text>
              </div>
              <Form.List name="items">
                {(fields, { add, remove }) => (
                  <>
                    <Table
                      rowKey="key"
                      size="small"
                      bordered
                      pagination={false}
                      dataSource={fields}
                      scroll={{ x: "max-content" }}
                      summary={() => (
                        <Table.Summary fixed>
                          <Table.Summary.Row>
                            <Table.Summary.Cell index={0}>
                              <Typography.Text strong>合计</Typography.Text>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={1}>
                              <Typography.Text strong>{summary.quantity}</Typography.Text>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={2} />
                            <Table.Summary.Cell index={3}>
                              <Typography.Text strong>{money(summary.amount)}</Typography.Text>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={4} />
                            <Table.Summary.Cell index={5}>
                              <Typography.Text>{money(summary.untaxedCost)}</Typography.Text>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={6}>
                              <Typography.Text>{money(summary.taxedCost - summary.untaxedCost)}</Typography.Text>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={7}>
                              <Typography.Text>{money(summary.taxedCost)}</Typography.Text>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={8}>
                              <Typography.Text type={summary.profit < 0 ? "danger" : undefined} strong>
                                {money(summary.profit)}
                              </Typography.Text>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={9}>
                              <StatusTag tone={marginColor} style={{ margin: 0 }}>{formatPercent(marginRate)}</StatusTag>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={10} />
                            <Table.Summary.Cell index={11} />
                          </Table.Summary.Row>
                        </Table.Summary>
                      )}
                      columns={[
                        {
                          title: "物料 / 产品",
                          width: 320,
                          render: (_: unknown, field) => (
                            <>
                              <Form.Item name={[field.name, "product_name"]} hidden />
                              <Form.Item
                                name={[field.name, "product_id"]}
                                rules={[{ required: true, message: "请选择产品" }]}
                                style={{ marginBottom: 0 }}
                              >
                                <ProductSelect
                                  onProductPicked={(product) => {
                                    const items = [...(form.getFieldValue("items") || [])] as QuoteItemForm[];
                                    const current = items[field.name] || {};
                                    items[field.name] = {
                                      ...current,
                                      product_name: product.name,
                                      datecode: current.datecode ?? product.datecode ?? null,
                                      unit_price: current.unit_price ?? product.unit_price ?? 0,
                                      quantity: current.quantity || 1,
                                    };
                                    form.setFieldValue("items", items);
                                    syncLineTotals();
                                    const customerId = Number(form.getFieldValue("customer_id"));
                                    if (customerId) void getProductCustomerCodes(product.id).then((response) => {
                                      const mapping = response.data.data.find((link) => link.customer_id === customerId && link.is_active);
                                      if (!mapping) return;
                                      const currentItems = [...(form.getFieldValue("items") || [])] as QuoteItemForm[];
                                      currentItems[field.name] = {
                                        ...currentItems[field.name],
                                        customer_part_no: currentItems[field.name]?.customer_part_no || mapping.customer_part_no,
                                        customer_product_name: currentItems[field.name]?.customer_product_name || mapping.customer_product_name || undefined,
                                      };
                                      form.setFieldValue("items", currentItems);
                                    }).catch(() => {});
                                  }}
                                />
                              </Form.Item>
                              <Space.Compact block style={{ marginTop: 6 }}>
                                <Form.Item name={[field.name, "customer_part_no"]} noStyle>
                                  <Input placeholder="客户料号（自动带出，可调整）" />
                                </Form.Item>
                                <Form.Item name={[field.name, "customer_product_name"]} noStyle>
                                  <Input placeholder="客户品名" />
                                </Form.Item>
                              </Space.Compact>
                            </>
                          ),
                        },
                        {
                          title: "数量",
                          width: 110,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "quantity"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={1} precision={0} style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "单位",
                          width: 90,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "unit"]} style={{ marginBottom: 0 }}>
                              <Input placeholder="件" />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "含税单价",
                          width: 140,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "unit_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={0} precision={4} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "折扣率",
                          width: 110,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "discount_rate"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={0} max={100} precision={2} suffix="%" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "税率",
                          width: 100,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "tax_rate"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={0} max={100} precision={2} suffix="%" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "销售额",
                          width: 140,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "total_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber disabled precision={2} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "含税成本单价",
                          width: 130,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "cost_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={0} precision={4} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "生产日期（DATECODE）",
                          width: 150,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "datecode"]} style={{ marginBottom: 0 }}>
                              <Input maxLength={100} placeholder="引用产品 DATECODE" />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "交期",
                          width: 140,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "lead_time"]} style={{ marginBottom: 0 }}>
                              <Input maxLength={100} placeholder="现货 / 7天 / 2–3周" />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "未税成本额",
                          width: 140,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "untaxed_cost"]} style={{ marginBottom: 0 }}>
                              <InputNumber disabled precision={2} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "进项税额",
                          width: 120,
                          render: (_: unknown, field) => (
                            <Form.Item noStyle shouldUpdate>
                              {() => {
                                const item = (form.getFieldValue(["items", field.name]) || {}) as QuoteItemForm;
                                const taxAmount = toNumber(item.taxed_cost) - toNumber(item.untaxed_cost);
                                return <Typography.Text>{money(taxAmount)}</Typography.Text>;
                              }}
                            </Form.Item>
                          ),
                        },
                        {
                          title: "含税成本额",
                          width: 140,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "taxed_cost"]} style={{ marginBottom: 0 }}>
                              <InputNumber disabled precision={2} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "销售毛利",
                          width: 140,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "sales_profit"]} style={{ marginBottom: 0 }}>
                              <InputNumber disabled precision={2} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "毛利率",
                          width: 110,
                          render: (_: unknown, field) => (
                            <Form.Item noStyle shouldUpdate>
                              {() => {
                                const item = (form.getFieldValue(["items", field.name]) || {}) as QuoteItemForm;
                                const totalPrice = toNumber(item.total_price);
                                const margin = totalPrice ? (toNumber(item.sales_profit) / totalPrice) * 100 : 0;
                                return (
                                  <StatusTag tone={margin >= 0 ? "success" : "danger"} style={{ margin: 0 }}>
                                    {formatPercent(margin)}
                                  </StatusTag>
                                );
                              }}
                            </Form.Item>
                          ),
                        },
                        {
                          title: "备注",
                          width: 220,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "notes"]} style={{ marginBottom: 0 }}>
                              <Input placeholder="交期 / 替代料 / 条件" />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "",
                          width: 54,
                          render: (_: unknown, field) => (
                            <Button danger type="text" icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
                          ),
                        },
                      ]}
                    />
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 12 }}>
                      <Button
                        type="dashed"
                        icon={<PlusOutlined />}
                        onClick={() => add({
                          quantity: 1,
                          unit_price: 0,
                          unit: "件",
                          tax_rate: 13,
                          discount_rate: 0,
                          total_price: 0,
                          cost_price: 0,
                          untaxed_cost: 0,
                          taxed_cost: 0,
                          sales_profit: 0,
                        })}
                      >
                        添加明细行
                      </Button>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        ERP 单据保存前至少需要一条有效产品明细。
                      </Typography.Text>
                    </div>
                  </>
                )}
              </Form.List>
            </Card>

            <Card
              size="small"
              title={<span style={sectionTitleStyle}>交易条款与备注</span>}
              style={{ borderColor: "#d9e2ec" }}
            >
              <Form.Item name="notes" label="报价条款">
                <Input.TextArea rows={6} placeholder="付款条件、交期、运输、价格有效期、特别说明" />
              </Form.Item>
            </Card>
          </Space>

          <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
            <Card
              size="small"
              title="单据控制台"
              extra={<StatusTag tone={marginColor}>毛利率 {formatPercent(marginRate)}</StatusTag>}
              style={{ borderColor: "#d9e2ec" }}
            >
              <Space direction="vertical" size={14} style={{ width: "100%" }}>
                <Statistic title="报价总金额" value={summary.amount} prefix="¥" precision={2} />
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div>
                    <div style={labelTextStyle}>产品行</div>
                    <Typography.Text strong>{summary.itemCount} 行</Typography.Text>
                  </div>
                  <div>
                    <div style={labelTextStyle}>总数量</div>
                    <Typography.Text strong>{summary.quantity}</Typography.Text>
                  </div>
                  <div>
                    <div style={labelTextStyle}>未税成本</div>
                    <Typography.Text>{money(summary.untaxedCost)}</Typography.Text>
                  </div>
                  <div>
                    <div style={labelTextStyle}>含税成本</div>
                    <Typography.Text>{money(summary.taxedCost)}</Typography.Text>
                  </div>
                  <div>
                    <div style={labelTextStyle}>销售毛利</div>
                    <Typography.Text type={summary.profit < 0 ? "danger" : undefined} strong>
                      {money(summary.profit)}
                    </Typography.Text>
                  </div>
                  <div>
                    <div style={labelTextStyle}>综合毛利率</div>
                    <StatusTag tone={marginColor} style={{ margin: 0 }}>{formatPercent(marginRate)}</StatusTag>
                  </div>
                </div>
                <Form.Item name="total_amount" hidden>
                  <InputNumber />
                </Form.Item>
                <Alert
                  showIcon
                  type={summary.itemCount > 0 && summary.profit >= 0 ? "info" : "warning"}
                  message={
                    summary.itemCount === 0
                      ? "请先添加产品明细后再保存单据"
                      : summary.profit < 0
                        ? "当前报价毛利为负，请复核销售价或成本"
                        : "金额由明细行自动汇总，保存时同步写入单据总额"
                  }
                />
              </Space>
            </Card>
            <Card size="small">
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Button block type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading}>
                  {isEdit ? "保存单据" : "创建单据"}
                </Button>
                <Button block onClick={() => navigate("/sales/quotations")}>取消</Button>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  报价成交后在详情页执行“转订单”，保持报价、订单、发货链路一致。
                </Typography.Text>
              </Space>
            </Card>
          </Space>
        </div>
      </Form>
    </SalesModuleShell>
  );
}
