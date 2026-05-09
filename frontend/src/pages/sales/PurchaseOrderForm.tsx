import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, Form, Input, InputNumber, Select, Button, Space, message, DatePicker, Row, Col, Divider, Spin } from "antd";
import { PlusOutlined, DeleteOutlined, ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { getSuppliers, getProducts, createPurchaseOrder, getPurchaseOrder, updatePurchaseOrder } from "../../api";

export default function PurchaseOrderForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const [products, setProducts] = useState<{ id: number; name: string; sku?: string }[]>([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Load reference data first, then PO data if editing
    Promise.all([
      getSuppliers({ page: 1, page_size: 100 }).then((r) =>
        setSuppliers((r.data.data?.list || []) as { id: number; name: string }[])
      ).catch(() => message.error("加载供应商列表失败")),
      getProducts({ page: 1, page_size: 100 }).then((r) =>
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

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSaving(true);
    try {
      const expectedDate = values.expected_date
        ? dayjs(values.expected_date as string).format("YYYY-MM-DD")
        : undefined;
      const payload = {
        supplier_id: values.supplier_id as number,
        expected_date: expectedDate,
        notes: values.notes as string || undefined,
        items: ((values.items as Record<string, unknown>[]) || []).map((item) => ({
          product_id: item.product_id as number,
          quantity: (item.quantity as number) || 1,
          unit_price: (item.unit_price as number) || 0,
          amount: ((item.quantity as number) || 1) * ((item.unit_price as number) || 0),
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
      console.error("PO save failed:", e);
      const err = e as { response?: { data?: { msg?: string } } };
      message.error(err?.response?.data?.msg || (isEdit ? "更新失败" : "创建失败"));
    }
    finally { setSaving(false); }
  };

  if (loading) return <Spin style={{ display: "block", margin: "80px auto" }} />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/purchase-orders")}>返回</Button>
      </Space>

      <Card title={isEdit ? "编辑采购订单" : "新建采购订单"}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}
          initialValues={{ items: [{}] }}
          onFinishFailed={() => message.warning("请完善必填项")}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="supplier_id" label="供应商" rules={[{ required: true, message: "请选择供应商" }]}>
                <Select
                  showSearch
                  placeholder="搜索并选择供应商"
                  optionFilterProp="label"
                  options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
                  notFoundContent={suppliers.length === 0 ? "加载中..." : "无匹配供应商"}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="expected_date" label="预计到货日期">
                <DatePicker style={{ width: "100%" }} placeholder="选择日期" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} placeholder="采购备注..." />
          </Form.Item>

          <Divider>采购明细</Divider>

          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...rest }) => (
                  <Row gutter={8} key={key} style={{ marginBottom: 8 }}>
                    <Col span={10}>
                      <Form.Item {...rest} name={[name, "product_id"]} rules={[{ required: true, message: "必选" }]} noStyle>
                        <Select
                          showSearch
                          placeholder="搜索产品"
                          optionFilterProp="label"
                          options={products.map((p) => ({ value: p.id, label: `${p.sku || ""} ${p.name}` }))}
                          notFoundContent={products.length === 0 ? "加载中..." : "无匹配产品"}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={4}>
                      <Form.Item {...rest} name={[name, "quantity"]} rules={[{ required: true, message: "必填" }]} noStyle>
                        <InputNumber min={1} placeholder="数量" style={{ width: "100%" }}
                          onChange={() => {
                            const qty = form.getFieldValue(["items", name, "quantity"]) || 0;
                            const price = form.getFieldValue(["items", name, "unit_price"]) || 0;
                            form.setFieldValue(["items", name, "amount"], qty * price);
                          }}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={5}>
                      <Form.Item {...rest} name={[name, "unit_price"]} noStyle>
                        <InputNumber min={0} step={0.01} placeholder="单价" style={{ width: "100%" }} prefix="¥"
                          onChange={() => {
                            const qty = form.getFieldValue(["items", name, "quantity"]) || 0;
                            const price = form.getFieldValue(["items", name, "unit_price"]) || 0;
                            form.setFieldValue(["items", name, "amount"], qty * price);
                          }}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={3}>
                      <Form.Item {...rest} name={[name, "amount"]} noStyle>
                        <InputNumber min={0} step={0.01} placeholder="小计" style={{ width: "100%" }} prefix="¥" disabled />
                      </Form.Item>
                    </Col>
                    <Col span={2}>
                      {fields.length > 1 && (
                        <Button type="text" danger icon={<DeleteOutlined />} onClick={() => remove(name)} />
                      )}
                    </Col>
                  </Row>
                ))}
                <Button type="dashed" onClick={() => add({ quantity: 1, unit_price: 0, amount: 0 })} block icon={<PlusOutlined />}>
                  添加产品
                </Button>
              </>
            )}
          </Form.List>

          <div style={{ marginTop: 24, textAlign: "right" }}>
            <Space>
              <Button onClick={() => navigate("/sales/purchase-orders")}>取消</Button>
              <Button type="primary" htmlType="submit" loading={saving} icon={<SaveOutlined />}>
                {isEdit ? "保存修改" : "创建采购订单"}
              </Button>
            </Space>
          </div>
        </Form>
      </Card>
    </div>
  );
}
