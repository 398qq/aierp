import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, DatePicker, Form, Input, InputNumber, Select, Space, Statistic, Table, Tag, Typography, message } from "antd";
import { ArrowLeftOutlined, DeleteOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import { getQuotation, createQuotation, updateQuotation } from "../../api";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import FormAIWarning from "../../components/sales/FormAIWarning";
import { CustomerSelect, OpportunitySelect, ProductSelect, SalesModuleShell, money } from "./salesUi";

type QuoteItemForm = {
  product_id?: number;
  product_name?: string;
  quantity?: number;
  unit_price?: number;
  total_price?: number;
  cost_price?: number;
  untaxed_cost?: number;
  taxed_cost?: number;
  sales_profit?: number;
  notes?: string;
};

const toNumber = (value: unknown) => Number(value || 0);
const COST_TAX_RATE = 0.13;
const formatPercent = (value: number) => `${value.toFixed(2)}%`;
const DEFAULT_QUOTATION_NOTES = [
  "1、以上报价为含税13%，如增加或改变加工工艺、零件、辅料，则须重新核价，并以确认的新单价为准；",
  "2、报价批量含运包费用，供方负责送货到需方指定地点",
  "3、产品付款方式：以合同为准",
  "4、报价有效期：3天",
].join("\n");

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
      const totalPrice = quantity * unitPrice;
      const costPrice = toNumber(item?.cost_price);
      const untaxedCost = quantity * costPrice;
      const taxedCost = untaxedCost * (1 + COST_TAX_RATE);
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
    const items = ((values.items || []) as QuoteItemForm[]).filter((item) => item.product_id || item.product_name);
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

  return (
    <SalesModuleShell
      title={isEdit ? "编辑报价单" : "新增报价单"}
      subtitle="选择客户与产品后自动计算报价金额，减少手工汇总错误"
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
        initialValues={{ status: "draft", items: [{}], valid_until: dayjs().add(3, "day"), notes: DEFAULT_QUOTATION_NOTES }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 300px", gap: 12, alignItems: "start" }}>
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Card size="small" title="报价基础信息">
              <FormAIWarning entityType="quotation" formData={formValues} />
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
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
                <Form.Item name="title" label="标题">
                  <Input placeholder="报价主题" />
                </Form.Item>
                <Form.Item name="quotation_no" label="报价单号">
                  <Input placeholder="留空自动生成" />
                </Form.Item>
                <Form.Item name="status" label="状态">
                  <Select options={[
                    { value: "draft", label: "草稿" },
                    { value: "sent", label: "已发送" },
                    { value: "won", label: "成交" },
                    { value: "lost", label: "丢失" },
                  ]} />
                </Form.Item>
                <Form.Item
                  name="valid_until"
                  label="有效期"
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
              <Form.Item name="notes" label="备注">
                <Input.TextArea rows={5} placeholder="付款条件、交期、特别说明" />
              </Form.Item>
            </Card>

            <Card
              size="small"
              title="报价产品行"
              extra={<Tag color={summary.itemCount > 0 ? "blue" : "red"}>{summary.itemCount} 项</Tag>}
            >
              <Form.List name="items">
                {(fields, { add, remove }) => (
                  <>
                    <Table
                      rowKey="key"
                      size="small"
                      pagination={false}
                      dataSource={fields}
                      scroll={{ x: "max-content" }}
                      columns={[
                        {
                          title: "产品",
                          width: 310,
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
                                      unit_price: current.unit_price ?? product.unit_price ?? 0,
                                      quantity: current.quantity || 1,
                                    };
                                    form.setFieldValue("items", items);
                                    syncLineTotals();
                                  }}
                                />
                              </Form.Item>
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
                          title: "含税销售单价",
                          width: 140,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "unit_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={0} precision={4} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "含税销售额",
                          width: 140,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "total_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber disabled precision={2} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "未税成本单价",
                          width: 130,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "cost_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={0} precision={4} prefix="¥" style={{ width: "100%" }} />
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
                                  <Tag color={margin >= 0 ? "green" : "red"} style={{ margin: 0 }}>
                                    {formatPercent(margin)}
                                  </Tag>
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
                    <Button
                      type="dashed"
                      icon={<PlusOutlined />}
                      onClick={() => add({
                        quantity: 1,
                        unit_price: 0,
                        total_price: 0,
                        cost_price: 0,
                        untaxed_cost: 0,
                        taxed_cost: 0,
                        sales_profit: 0,
                      })}
                      block
                      style={{ marginTop: 12 }}
                    >
                      添加产品行
                    </Button>
                  </>
                )}
              </Form.List>
            </Card>
          </Space>

          <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
            <Card size="small" title="报价摘要">
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                <Statistic title="报价总金额" value={summary.amount} prefix="¥" precision={2} />
                <Space wrap>
                  <Tag color="blue">产品行 {summary.itemCount}</Tag>
                  <Tag>总数量 {summary.quantity}</Tag>
                  <Tag color="green">{money(summary.amount)}</Tag>
                  <Tag color="orange">含税成本 {money(summary.taxedCost)}</Tag>
                  <Tag color={summary.profit >= 0 ? "green" : "red"}>利润 {money(summary.profit)}</Tag>
                </Space>
                <Form.Item name="total_amount" hidden>
                  <InputNumber />
                </Form.Item>
                <Alert
                  showIcon
                  type={summary.itemCount > 0 ? "info" : "warning"}
                  message={summary.itemCount > 0 ? "总金额由产品行自动汇总" : "请先添加产品报价行"}
                />
              </Space>
            </Card>
            <Card size="small">
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Button block type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading}>
                  {isEdit ? "保存报价" : "创建报价"}
                </Button>
                <Button block onClick={() => navigate("/sales/quotations")}>取消</Button>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  成交建议通过详情页“转订单”完成，便于保持报价和订单链路一致。
                </Typography.Text>
              </Space>
            </Card>
          </Space>
        </div>
      </Form>
    </SalesModuleShell>
  );
}
