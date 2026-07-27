import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "@/router";
import { Button, Card, DatePicker, Form, Input, InputNumber, Select, Space, Typography, message } from "antd";
import { ArrowLeftOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { createDeliveryNote, getDeliveryNote, getProductCustomerCodes, getSalesOrders, updateDeliveryNote } from "../../api";
import dayjs from "dayjs";
import type { SalesOrder } from "../../types";
import { CustomerSelect, ProductSelect, SalesModuleShell, shortDate } from "./salesUi";

export default function DeliveryNoteForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const isEdit = !!id;

  useEffect(() => {
    getSalesOrders({ page: 1, page_size: 100, sort_by: "id", sort_order: "desc" })
      .then((r) => setOrders(r.data.data.list || []))
      .catch(() => {});

    if (isEdit) {
      getDeliveryNote(Number(id)).then((r) => {
        const n = r.data.data;
        form.setFieldsValue({
          ...n,
          delivery_date: n.delivery_date ? dayjs(n.delivery_date) : null,
          received_date: n.received_date ? dayjs(n.received_date) : null,
        });
      });
    } else {
      const orderId = Number(searchParams.get("sales_order_id"));
      const customerId = Number(searchParams.get("customer_id"));
      if (customerId) form.setFieldValue("customer_id", customerId);
      if (orderId) form.setFieldValue("sales_order_id", orderId);
    }
  }, [form, id, isEdit, searchParams]);

  const orderById = useMemo(() => new Map(orders.map((order) => [order.id, order])), [orders]);

  const applyOrder = (orderId?: number) => {
    const order = orderById.get(Number(orderId));
    if (!order) return;
    form.setFieldsValue({
      customer_id: order.customer_id,
      items: (order.items || []).map((item) => ({
        product_id: item.product_id,
        product_name: item.product_name,
        customer_part_no: item.customer_part_no,
        customer_product_name: item.customer_product_name,
        quantity: item.quantity,
      })),
    });
  };

  useEffect(() => {
    const orderId = Number(searchParams.get("sales_order_id"));
    if (!isEdit && orderId && orders.length > 0) applyOrder(orderId);
  }, [orders, searchParams, isEdit]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload: Record<string, unknown> = {
        ...values,
        delivery_date: values.delivery_date ? (values.delivery_date as string) : null,
        received_date: values.received_date ? (values.received_date as string) : null,
        items: values.items || [],
      };
      if (isEdit) {
        await updateDeliveryNote(Number(id), payload);
        message.success("发货单已更新");
      } else {
        await createDeliveryNote(payload);
        message.success("发货单已创建");
      }
      navigate("/sales/delivery-notes");
    } catch (err: any) {
      message.error(err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "保存失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑发货单" : "新增发货单"}
      subtitle="发货单必须绑定销售订单，客户默认跟随订单，避免错发和漏关联"
      activeKey="delivery"
      extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/delivery-notes")}>返回</Button>}
    >
      <Card size="small">
        <Form form={form} layout="vertical" size="small" onFinish={onFinish} initialValues={{ status: "pending", items: [{}] }}>
          <Form.Item name="sales_order_id" label="关联销售订单" rules={[{ required: true }]}>
            <Select
              showSearch
              placeholder="选择销售订单"
              optionFilterProp="label"
              onChange={applyOrder}
              options={orders.map((order) => ({
                value: order.id,
                label: `${order.order_no || `#${order.id}`} / 客户 #${order.customer_id} / ${shortDate(order.delivery_date)}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <CustomerSelect />
          </Form.Item>
          <Form.Item name="delivery_no" label="发货单号"><Input placeholder="留空自动生成" /></Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={[
              { value: "pending", label: "待发货" },
              { value: "shipped", label: "已发货" },
              { value: "delivered", label: "已签收" },
              { value: "returned", label: "已退回" },
            ]} />
          </Form.Item>
          <Form.Item name="delivery_date" label="发货日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="received_date" label="签收日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>

          <Typography.Title level={5}>发货明细</Typography.Title>
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...rest }) => (
                  <Space key={key} style={{ display: "flex", marginBottom: 8 }} align="baseline" wrap>
                    <Form.Item {...rest} name={[name, "product_name"]} hidden />
                    <Form.Item {...rest} name={[name, "customer_product_name"]} hidden />
                    <Form.Item {...rest} name={[name, "product_id"]} label="产品" rules={[{ required: true, message: "请选择产品" }]} style={{ minWidth: 280 }}>
                      <ProductSelect
                        onProductPicked={(product) => {
                          const items = [...(form.getFieldValue("items") || [])];
                          items[name] = { ...items[name], product_name: product.name };
                          form.setFieldValue("items", items);
                          const customerId = Number(form.getFieldValue("customer_id"));
                          if (customerId) void getProductCustomerCodes(product.id).then((response) => {
                            const mapping = response.data.data.find((link) => link.customer_id === customerId && link.is_active);
                            if (!mapping) return;
                            const currentItems = [...(form.getFieldValue("items") || [])];
                            currentItems[name] = {
                              ...currentItems[name],
                              customer_part_no: currentItems[name]?.customer_part_no || mapping.customer_part_no,
                              customer_product_name: currentItems[name]?.customer_product_name || mapping.customer_product_name,
                            };
                            form.setFieldValue("items", currentItems);
                          }).catch(() => {});
                        }}
                      />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, "customer_part_no"]} label="客户料号" style={{ minWidth: 190 }}>
                      <Input placeholder="自动取订单快照" />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, "quantity"]} label="数量"><InputNumber min={1} /></Form.Item>
                    <Button icon={<DeleteOutlined />} onClick={() => remove(name)} />
                  </Space>
                ))}
                <Button type="dashed" icon={<PlusOutlined />} onClick={() => add()} block>添加品项</Button>
              </>
            )}
          </Form.List>

          <Form.Item style={{ marginTop: 16 }}>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
              <Button onClick={() => navigate("/sales/delivery-notes")}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </SalesModuleShell>
  );
}
