import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, DatePicker, Form, Input, InputNumber, Select, Space, Statistic, Table, Tag, Typography, message } from "antd";
import { StatusTag } from "../../ui";
import { ArrowLeftOutlined, CalculatorOutlined, DeleteOutlined, FileDoneOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import { getSalesOrder, createSalesOrder, updateSalesOrder } from "../../api";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import { CustomerSelect, ProductSelect, QuotationSelect, SalesModuleShell, money } from "./salesUi";

type OrderItemForm = {
  product_id?: number;
  product_name?: string;
  quantity?: number;
  unit_price?: number;
  total_price?: number;
  notes?: string;
};

const toNumber = (value: unknown) => Number(value || 0);

const STATUS_OPTIONS = [
  { value: "pending", label: "待确认" },
  { value: "confirmed", label: "已确认" },
  { value: "shipped", label: "已发货" },
  { value: "delivered", label: "已签收" },
  { value: "cancelled", label: "已取消" },
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

export default function SalesOrderForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const isEdit = !!id;
  const watchedItems = Form.useWatch("items", form) as OrderItemForm[] | undefined;
  const watchedTotal = Form.useWatch("total_amount", form) as number | undefined;
  const watchedStatus = Form.useWatch("status", form) as string | undefined;
  const watchedDeliveryDate = Form.useWatch("delivery_date", form) as Dayjs | undefined;
  const watchedCustomerId = Form.useWatch("customer_id", form) as number | undefined;

  const summary = useMemo(() => {
    const items = watchedItems || [];
    const validItems = items.filter((item) => item?.product_id || item?.product_name);
    const amount = items.reduce((sum, item) => sum + toNumber(item?.total_price), 0);
    const quantity = items.reduce((sum, item) => sum + toNumber(item?.quantity), 0);
    return { itemCount: validItems.length, amount, quantity };
  }, [watchedItems]);

  useEffect(() => {
    if (isEdit) {
      getSalesOrder(Number(id)).then((r) => {
        const order = r.data.data;
        form.setFieldsValue({
          ...order,
          order_date: order.order_date ? dayjs(order.order_date) : null,
          delivery_date: order.delivery_date ? dayjs(order.delivery_date) : null,
          items: order.items?.length ? order.items : [{}],
        });
      });
    } else {
      const customerId = Number(searchParams.get("customer_id"));
      const quotationId = Number(searchParams.get("quotation_id"));
      if (customerId) form.setFieldValue("customer_id", customerId);
      if (quotationId) form.setFieldValue("quotation_id", quotationId);
    }
  }, [id, isEdit, searchParams, form]);

  useEffect(() => {
    if (Math.abs(toNumber(watchedTotal) - summary.amount) > 0.0001) {
      form.setFieldValue("total_amount", summary.amount);
    }
  }, [form, summary.amount, watchedTotal]);

  const syncLineTotals = () => {
    const items = [...(form.getFieldValue("items") || [])] as OrderItemForm[];
    let changed = false;
    const next = items.map((item) => {
      const quantity = toNumber(item?.quantity || 1);
      const unitPrice = toNumber(item?.unit_price);
      const totalPrice = quantity * unitPrice;
      if (item?.quantity !== quantity || item?.total_price !== totalPrice) {
        changed = true;
      }
      return {
        ...item,
        quantity,
        unit_price: unitPrice,
        total_price: totalPrice,
      };
    });
    if (changed) form.setFieldValue("items", next);
  };

  const onFinish = async (values: Record<string, unknown>) => {
    const items = ((values.items || []) as OrderItemForm[]).filter((item) => item.product_id || item.product_name);
    if (!items.length) {
      message.warning("至少添加一条产品订单明细");
      return;
    }

    setLoading(true);
    try {
      const payload: Record<string, unknown> = {
        ...values,
        order_date: values.order_date ? (values.order_date as Dayjs).toISOString() : null,
        delivery_date: values.delivery_date ? (values.delivery_date as Dayjs).toISOString() : null,
        total_amount: summary.amount,
        items,
      };
      if (isEdit) {
        await updateSalesOrder(Number(id), payload);
        message.success("订单已更新");
      } else {
        await createSalesOrder(payload);
        message.success("订单已创建");
      }
      navigate("/sales/orders");
    } catch (err: any) {
      message.error(err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "保存失败");
    } finally {
      setLoading(false);
    }
  };

  const deliveryDays = watchedDeliveryDate ? watchedDeliveryDate.startOf("day").diff(dayjs().startOf("day"), "day") : null;
  const deliveryRisk = deliveryDays == null
    ? { color: "default", text: "未设置交期", type: "warning" as const }
    : deliveryDays < 0
      ? { color: "red", text: `已逾期 ${Math.abs(deliveryDays)} 天`, type: "error" as const }
      : deliveryDays <= 3
        ? { color: "orange", text: `${deliveryDays} 天内交付`, type: "warning" as const }
        : { color: "blue", text: `${deliveryDays} 天后交付`, type: "info" as const };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑销售订单" : "新增销售订单"}
      subtitle="按 ERP 单据录入订单抬头、产品明细、交付计划和执行状态"
      activeKey="orders"
      extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/orders")}>返回</Button>}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        onValuesChange={() => syncLineTotals()}
        requiredMark={false}
        initialValues={{
          status: "pending",
          items: [{}],
          order_date: dayjs(),
          delivery_date: dayjs().add(7, "day"),
        }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 320px", gap: 16, alignItems: "start" }}>
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Card
              size="small"
              title={<span style={sectionTitleStyle}><FileDoneOutlined /> 单据抬头</span>}
              extra={<StatusTag tone="processing">销售订单</StatusTag>}
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
                  <Typography.Title level={4} style={{ margin: 0 }}>销售订单</Typography.Title>
                  <Typography.Text type="secondary">客户、来源报价、订单号、日期和交期在抬头集中维护</Typography.Text>
                </div>
                <Space wrap>
                  <StatusTag tone="info">订单执行</StatusTag>
                  <StatusTag tone={deliveryRisk.color}>{deliveryRisk.text}</StatusTag>
                </Space>
              </div>

              <div style={compactFormGrid}>
                <Form.Item name="customer_id" label="客户" rules={[{ required: true, message: "请选择客户" }]}>
                  <CustomerSelect />
                </Form.Item>
                <Form.Item name="quotation_id" label="来源报价">
                  <QuotationSelect customerId={watchedCustomerId} />
                </Form.Item>
                <Form.Item name="order_no" label="订单号">
                  <Input placeholder="系统自动生成 / 手工编号" />
                </Form.Item>
                <Form.Item name="status" label="执行状态">
                  <Select options={STATUS_OPTIONS} />
                </Form.Item>
                <Form.Item name="order_date" label="下单日期">
                  <DatePicker style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item
                  name="delivery_date"
                  label="预计交货"
                  rules={[{
                    validator: (_, value: Dayjs | null) => {
                      const orderDate = form.getFieldValue("order_date") as Dayjs | null;
                      if (!value || !orderDate || value.endOf("day").isAfter(orderDate.startOf("day"))) return Promise.resolve();
                      return Promise.reject(new Error("预计交货不能早于下单日期"));
                    },
                  }]}
                >
                  <DatePicker style={{ width: "100%" }} />
                </Form.Item>
              </div>
            </Card>

            <Card
              size="small"
              title={<span style={sectionTitleStyle}><CalculatorOutlined /> 订单明细</span>}
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
                  明细行自动计算订单金额；确认订单后将进入库存锁定、发货、开票和回款链路。
                </Typography.Text>
                <Typography.Text strong>订单合计：{money(summary.amount)}</Typography.Text>
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
                            <Table.Summary.Cell index={5} />
                          </Table.Summary.Row>
                        </Table.Summary>
                      )}
                      columns={[
                        {
                          title: "物料 / 产品",
                          width: 340,
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
                                    const items = [...(form.getFieldValue("items") || [])] as OrderItemForm[];
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
                          width: 120,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "quantity"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={1} precision={0} style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "销售单价",
                          width: 150,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "unit_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={0} precision={4} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "订单金额",
                          width: 150,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "total_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber disabled precision={2} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "交付备注",
                          width: 260,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "notes"]} style={{ marginBottom: 0 }}>
                              <Input placeholder="批次 / 交期 / 包装 / 客户料号" />
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
                        onClick={() => add({ quantity: 1, unit_price: 0, total_price: 0 })}
                      >
                        添加明细行
                      </Button>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        ERP 订单保存前至少需要一条有效产品明细。
                      </Typography.Text>
                    </div>
                  </>
                )}
              </Form.List>
            </Card>

            <Card
              size="small"
              title={<span style={sectionTitleStyle}>交付条款与备注</span>}
              style={{ borderColor: "#d9e2ec" }}
            >
              <Form.Item name="notes" label="订单备注">
                <Input.TextArea rows={5} placeholder="客户 PO 号、交付批次、付款条件、发货要求、特殊包装或验收说明" />
              </Form.Item>
            </Card>
          </Space>

          <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
            <Card
              size="small"
              title="单据控制台"
              extra={<StatusTag tone={deliveryRisk.color}>{deliveryRisk.text}</StatusTag>}
              style={{ borderColor: "#d9e2ec" }}
            >
              <Space direction="vertical" size={14} style={{ width: "100%" }}>
                <Statistic title="订单总金额" value={summary.amount} prefix="¥" precision={2} />
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
                    <div style={labelTextStyle}>执行状态</div>
                    <StatusTag tone={watchedStatus === "confirmed" ? "info" : watchedStatus === "cancelled" ? "danger" : "neutral"} style={{ margin: 0 }}>
                      {STATUS_OPTIONS.find((item) => item.value === watchedStatus)?.label || watchedStatus || "待确认"}
                    </StatusTag>
                  </div>
                  <div>
                    <div style={labelTextStyle}>交付计划</div>
                    <Typography.Text strong>{deliveryRisk.text}</Typography.Text>
                  </div>
                </div>
                <Form.Item name="total_amount" hidden>
                  <InputNumber />
                </Form.Item>
                <Alert
                  showIcon
                  type={summary.itemCount > 0 ? deliveryRisk.type : "warning"}
                  message={
                    summary.itemCount === 0
                      ? "请先添加产品明细后再保存订单"
                      : deliveryRisk.type === "error"
                        ? "预计交付已逾期，请复核交期或拆分发货计划"
                        : "金额由明细行自动汇总，保存后进入订单执行链路"
                  }
                />
              </Space>
            </Card>
            <Card size="small">
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Button block type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading}>
                  {isEdit ? "保存单据" : "创建单据"}
                </Button>
                <Button block onClick={() => navigate("/sales/orders")}>取消</Button>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  订单确认后建议在详情页执行库存锁定，再转发货单推进交付。
                </Typography.Text>
              </Space>
            </Card>
          </Space>
        </div>
      </Form>
    </SalesModuleShell>
  );
}
