import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Alert, Button, Card, DatePicker, Form, Input, InputNumber, Select, Space, Statistic, Table, Tag, Typography, message } from "antd";
import { ArrowLeftOutlined, CalculatorOutlined, DeleteOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { getSuppliers, getProducts, createPurchaseOrder, getPurchaseOrder, updatePurchaseOrder } from "../../api";
import { SalesModuleShell, money } from "./salesUi";

type POItemForm = {
  product_id?: number;
  quantity?: number;
  unit_price?: number;
  amount?: number;
};

const toNumber = (value: unknown) => Number(value || 0);

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

export default function PurchaseOrderForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const [products, setProducts] = useState<{ id: number; name: string; sku?: string }[]>([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  const watchedItems = Form.useWatch("items", form) as POItemForm[] | undefined;

  const summary = useMemo(() => {
    const items = watchedItems || [];
    const validItems = items.filter((item) => item?.product_id);
    const amount = items.reduce((sum, item) => sum + toNumber(item?.amount), 0);
    const quantity = items.reduce((sum, item) => sum + toNumber(item?.quantity), 0);
    return { itemCount: validItems.length, amount, quantity };
  }, [watchedItems]);

  useEffect(() => {
    // Load reference data first, then PO data if editing
    Promise.all([
      getSuppliers({ page: 1, page_size: 200 }).then((r) =>
        setSuppliers((r.data.data?.list || []) as { id: number; name: string }[])
      ).catch(() => message.error("加载供应商列表失败")),
      getProducts({ page: 1, page_size: 200 }).then((r) =>
        setProducts((r.data.data?.list || []) as { id: number; name: string; sku?: string }[])
      ).catch(() => message.error("加载产品列表失败")),
    ]).then(() => {
      if (isEdit) {
        setLoading(true);
        getPurchaseOrder(Number(id))
          .then((r) => {
            const po = r.data.data as unknown as Record<string, unknown>;
            const items = (po.items as Record<string, unknown>[]) || [];
            form.setFieldsValue({
              supplier_id: po.supplier_id,
              expected_date: po.expected_date ? dayjs(po.expected_date as string) : undefined,
              notes: po.notes,
              items: items.length > 0
                ? items.map((i) => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price, amount: i.amount }))
                : [{}],
            });
          })
          .catch(() => message.error("加载采购订单信息失败"))
          .finally(() => setLoading(false));
      }
    });
  }, [id, isEdit, form]);

  const syncLineTotals = () => {
    const items = [...(form.getFieldValue("items") || [])] as POItemForm[];
    let changed = false;
    const next = items.map((item) => {
      const quantity = toNumber(item?.quantity || 1);
      const unitPrice = toNumber(item?.unit_price);
      const amt = quantity * unitPrice;
      if (item?.amount !== amt) {
        changed = true;
      }
      return { ...item, quantity, unit_price: unitPrice, amount: amt };
    });
    if (changed) form.setFieldValue("items", next);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    const items = ((values.items || []) as POItemForm[]).filter((item) => item.product_id);
    if (!items.length) {
      message.warning("至少添加一条采购明细");
      return;
    }

    setSaving(true);
    try {
      const expectedDate = values.expected_date
        ? dayjs(values.expected_date as string).format("YYYY-MM-DD")
        : undefined;
      const payload = {
        supplier_id: values.supplier_id as number,
        expected_date: expectedDate,
        notes: values.notes as string || undefined,
        total_amount: summary.amount,
        items: items.map((item) => ({
          product_id: item.product_id as number,
          quantity: toNumber(item.quantity),
          unit_price: toNumber(item.unit_price),
          amount: toNumber(item.quantity) * toNumber(item.unit_price),
        })),
      };
      if (isEdit) {
        await updatePurchaseOrder(Number(id), payload);
        message.success("采购订单已更新");
      } else {
        await createPurchaseOrder(payload);
        message.success("采购订单已创建");
      }
      navigate("/sales/purchase-orders");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { msg?: string } }; message?: string };
      message.error(err?.response?.data?.msg || err?.message || (isEdit ? "更新失败" : "创建失败"));
    }
    finally { setSaving(false); }
  };

  if (loading) return (
    <SalesModuleShell title={isEdit ? "编辑采购订单" : "新建采购订单"} activeKey="procurement">
      <div style={{ display: "flex", justifyContent: "center", padding: 80 }}>
        <div className="ant-spin-dot ant-spin-dot-spin"><i /><i /><i /><i /></div>
      </div>
    </SalesModuleShell>
  );

  return (
    <SalesModuleShell
      title={isEdit ? "编辑采购订单" : "新建采购订单"}
      subtitle="创建和管理供应商采购订单，包含采购明细和预计到货日期"
      activeKey="procurement"
      extra={(
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/purchase-orders")}>返回列表</Button>
      )}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        onValuesChange={() => syncLineTotals()}
        requiredMark={false}
        initialValues={{ items: [{}] }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 320px", gap: 16, alignItems: "start" }}>
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Card
              size="small"
              title={<span style={sectionTitleStyle}><CalculatorOutlined /> 采购单据</span>}
              extra={<Tag color="processing">采购订单</Tag>}
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
                  <Typography.Title level={4} style={{ margin: 0 }}>采购订单</Typography.Title>
                  <Typography.Text type="secondary">选择供应商、录入采购明细、设定预计到货</Typography.Text>
                </div>
              </div>

              <div style={compactFormGrid}>
                <Form.Item name="supplier_id" label="供应商" rules={[{ required: true, message: "请选择供应商" }]}>
                  <Select
                    showSearch
                    placeholder="搜索并选择供应商"
                    optionFilterProp="label"
                    options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
                    notFoundContent={suppliers.length === 0 ? "加载中..." : "无匹配供应商"}
                  />
                </Form.Item>
                <Form.Item name="expected_date" label="预计到货日期">
                  <DatePicker style={{ width: "100%" }} placeholder="选择日期" />
                </Form.Item>
              </div>

              <Form.Item name="notes" label="备注">
                <Input.TextArea rows={2} placeholder="采购备注..." />
              </Form.Item>
            </Card>

            <Card
              size="small"
              title={<span style={sectionTitleStyle}><CalculatorOutlined /> 采购明细</span>}
              extra={(
                <Space size={8}>
                  <Tag color={summary.itemCount > 0 ? "blue" : "red"}>{summary.itemCount} 行</Tag>
                  <Tag>数量 {summary.quantity}</Tag>
                </Space>
              )}
              style={{ borderColor: "#d9e2ec" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
                <Typography.Text type="secondary">
                  明细行自动计算采购金额；保存后可在列表页操作收货入库。
                </Typography.Text>
                <Typography.Text strong>采购合计：{money(summary.amount)}</Typography.Text>
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
                          </Table.Summary.Row>
                        </Table.Summary>
                      )}
                      columns={[
                        {
                          title: "产品",
                          width: 340,
                          render: (_: unknown, field) => (
                            <Form.Item
                              name={[field.name, "product_id"]}
                              rules={[{ required: true, message: "必选" }]}
                              style={{ marginBottom: 0 }}
                            >
                              <Select
                                showSearch
                                placeholder="搜索产品"
                                optionFilterProp="label"
                                options={products.map((p) => ({ value: p.id, label: `${p.sku || ""} ${p.name}` }))}
                                notFoundContent={products.length === 0 ? "加载中..." : "无匹配产品"}
                              />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "数量",
                          width: 120,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "quantity"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={1} placeholder="数量" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "单价",
                          width: 150,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "unit_price"]} style={{ marginBottom: 0 }}>
                              <InputNumber min={0} step={0.01} placeholder="单价" style={{ width: "100%" }} prefix="¥" />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "小计",
                          width: 130,
                          render: (_: unknown, field) => (
                            <Form.Item name={[field.name, "amount"]} style={{ marginBottom: 0 }}>
                              <InputNumber disabled precision={2} prefix="¥" style={{ width: "100%" }} />
                            </Form.Item>
                          ),
                        },
                        {
                          title: "",
                          width: 54,
                          render: (_: unknown, field) => (
                            fields.length > 1 ? (
                              <Button danger type="text" icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
                            ) : null
                          ),
                        },
                      ]}
                    />
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 12 }}>
                      <Button
                        type="dashed"
                        icon={<PlusOutlined />}
                        onClick={() => add({ quantity: 1, unit_price: 0, amount: 0 })}
                      >
                        添加产品
                      </Button>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        采购单保存前至少需要一条有效产品明细。
                      </Typography.Text>
                    </div>
                  </>
                )}
              </Form.List>
            </Card>
          </Space>

          <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
            <Card
              size="small"
              title="单据控制台"
              style={{ borderColor: "#d9e2ec" }}
            >
              <Space direction="vertical" size={14} style={{ width: "100%" }}>
                <Statistic title="采购总金额" value={summary.amount} prefix="¥" precision={2} />
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div>
                    <div style={labelTextStyle}>产品行</div>
                    <Typography.Text strong>{summary.itemCount} 行</Typography.Text>
                  </div>
                  <div>
                    <div style={labelTextStyle}>总数量</div>
                    <Typography.Text strong>{summary.quantity}</Typography.Text>
                  </div>
                </div>
                <Alert
                  showIcon
                  type={summary.itemCount > 0 ? "info" : "warning"}
                  message={
                    summary.itemCount === 0
                      ? "请先添加产品明细后再保存采购单"
                      : "金额由明细行自动汇总，保存后可执行收货入库"
                  }
                />
              </Space>
            </Card>
            <Card size="small">
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Button block type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
                  {isEdit ? "保存修改" : "创建采购订单"}
                </Button>
                <Button block onClick={() => navigate("/sales/purchase-orders")}>取消</Button>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  采购单保存后可在列表页操作收货，系统自动更新库存。
                </Typography.Text>
              </Space>
            </Card>
          </Space>
        </div>
      </Form>
    </SalesModuleShell>
  );
}
