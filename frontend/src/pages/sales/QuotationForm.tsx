import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, DatePicker, Form, Input, InputNumber, Select, Space, Statistic, Table, Tag, Typography, message } from "antd";
import { ArrowLeftOutlined, DeleteOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import { getQuotation, createQuotation, updateQuotation } from "../../api";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import FormAIWarning from "../../components/sales/FormAIWarning";
import { CustomerSelect, ProductSelect, SalesModuleShell, money } from "./salesUi";

type QuoteItemForm = {
  product_id?: number;
  product_name?: string;
  quantity?: number;
  unit_price?: number;
  total_price?: number;
  notes?: string;
};

const toNumber = (value: unknown) => Number(value || 0);

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

  const summary = useMemo(() => {
    const items = watchedItems || [];
    const validItems = items.filter((item) => item?.product_id || item?.product_name);
    const amount = items.reduce((sum, item) => sum + toNumber(item?.total_price), 0);
    const quantity = items.reduce((sum, item) => sum + toNumber(item?.quantity), 0);
    return { itemCount: validItems.length, amount, quantity };
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
      if (item?.total_price !== totalPrice) changed = true;
      return { ...item, quantity, total_price: totalPrice };
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
        initialValues={{ status: "draft", items: [{}], valid_until: dayjs().add(30, "day") }}
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
                  <InputNumber style={{ width: "100%" }} placeholder="可由商机页面带入" />
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
                <Input.TextArea rows={2} placeholder="付款条件、交期、特别说明" />
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
                          title: "单价",
                          width: 140,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "unit_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={0} precision={4} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "小计",
                          width: 140,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "total_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber disabled precision={2} prefix="¥" style={{ width: "100%" }} />
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
                    <Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ quantity: 1, unit_price: 0, total_price: 0 })} block style={{ marginTop: 12 }}>
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
