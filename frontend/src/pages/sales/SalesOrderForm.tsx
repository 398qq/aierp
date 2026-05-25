import { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Button, Card, DatePicker, Form, Input, InputNumber, Select, Space, message } from "antd";
import { ArrowLeftOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { getSalesOrder, createSalesOrder, updateSalesOrder } from "../../api";
import dayjs from "dayjs";
import { CustomerSelect, ProductSelect, SalesModuleShell } from "./salesUi";

export default function SalesOrderForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const isEdit = !!id;

  useEffect(() => {
    if (isEdit) {
      getSalesOrder(Number(id)).then((r) => {
        const o = r.data.data;
        form.setFieldsValue({ ...o, order_date: o.order_date ? dayjs(o.order_date) : null, delivery_date: o.delivery_date ? dayjs(o.delivery_date) : null });
      });
    } else {
      const customerId = Number(searchParams.get("customer_id"));
      const quotationId = Number(searchParams.get("quotation_id"));
      if (customerId) form.setFieldValue("customer_id", customerId);
      if (quotationId) form.setFieldValue("quotation_id", quotationId);
    }
  }, [id, isEdit, searchParams, form]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload: Record<string, unknown> = {
        ...values,
        order_date: values.order_date ? (values.order_date as string) : null,
        delivery_date: values.delivery_date ? (values.delivery_date as string) : null,
        items: values.items || [],
      };
      if (isEdit) {
        await updateSalesOrder(Number(id), payload);
        message.success("订单已更新");
      } else {
        await createSalesOrder(payload);
        message.success("订单已创建");
      }
      navigate("/sales/orders");
    } catch (err: any) { message.error(err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "保存失败"); }
    finally { setLoading(false); }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑销售订单" : "新增销售订单"}
      subtitle="确认客户订单、产品明细、交付日期和执行状态"
      activeKey="orders"
      extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/orders")}>返回</Button>}
    >
      <Card>
        <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ status: "pending", items: [{}] }}>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <CustomerSelect />
          </Form.Item>
          <Form.Item name="quotation_id" label="来源报价"><InputNumber style={{ width: "100%" }} placeholder="可由报价转订单带入" /></Form.Item>
          <Form.Item name="order_no" label="订单号"><Input placeholder="留空自动生成" /></Form.Item>
          <Form.Item name="total_amount" label="总金额"><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={[
              { value: "pending", label: "待确认" }, { value: "confirmed", label: "已确认" }, { value: "shipped", label: "已发货" },
            ]} />
          </Form.Item>
          <Form.Item name="order_date" label="下单日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="delivery_date" label="预计交货"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>

          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...rest }) => (
                  <Space key={key} style={{ display: "flex", marginBottom: 8 }} align="baseline" wrap>
                    <Form.Item {...rest} name={[name, "product_name"]} hidden />
                    <Form.Item {...rest} name={[name, "product_id"]} label="产品" rules={[{ required: true, message: "请选择产品" }]} style={{ minWidth: 280 }}>
                      <ProductSelect
                        onProductPicked={(product) => {
                          const items = [...(form.getFieldValue("items") || [])];
                          items[name] = {
                            ...items[name],
                            product_name: product.name,
                            unit_price: items[name]?.unit_price ?? product.unit_price,
                          };
                          form.setFieldValue("items", items);
                        }}
                      />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, "quantity"]} label="数量"><InputNumber min={1} /></Form.Item>
                    <Form.Item {...rest} name={[name, "unit_price"]} label="单价"><InputNumber prefix="¥" /></Form.Item>
                    <Form.Item {...rest} name={[name, "total_price"]} label="小计"><InputNumber prefix="¥" /></Form.Item>
                    <Button icon={<DeleteOutlined />} onClick={() => remove(name)} />
                  </Space>
                ))}
                <Button type="dashed" icon={<PlusOutlined />} onClick={() => add()} block>添加产品行</Button>
              </>
            )}
          </Form.List>

          <Form.Item style={{ marginTop: 16 }}>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
              <Button onClick={() => navigate("/sales/orders")}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </SalesModuleShell>
  );
}
