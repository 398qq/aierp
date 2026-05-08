import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Form, Input, Select, InputNumber, DatePicker, Button, message, Space } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { getDeliveryNote, createDeliveryNote, updateDeliveryNote, getCustomers, getSalesOrders } from "../../api";
import dayjs from "dayjs";
import type { Customer, SalesOrder } from "../../types";

export default function DeliveryNoteForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const isEdit = !!id;

  useEffect(() => {
    getCustomers({ page: 1, page_size: 200 }).then((r) => setCustomers(r.data.data.list || []));
    getSalesOrders({ page: 1, page_size: 200 }).then((r) => setOrders(r.data.data.list || []));
    if (isEdit) {
      getDeliveryNote(Number(id)).then((r) => {
        const n = r.data.data;
        form.setFieldsValue({ ...n, delivery_date: n.delivery_date ? dayjs(n.delivery_date) : null, received_date: n.received_date ? dayjs(n.received_date) : null });
      });
    }
  }, [id]);

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
    } catch { message.error("保存失败"); }
    finally { setLoading(false); }
  };

  return (
    <Card title={isEdit ? "编辑发货单" : "新增发货单"}>
      <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ status: "pending", items: [{}] }}>
        <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
          <Select showSearch placeholder="选择客户" options={customers.map((c) => ({ value: c.id, label: c.name }))} />
        </Form.Item>
        <Form.Item name="sales_order_id" label="关联销售订单" rules={[{ required: true }]}>
          <Select showSearch placeholder="选择销售订单" options={orders.map((o) => ({ value: o.id, label: o.order_no || `#${o.id}` }))} />
        </Form.Item>
        <Form.Item name="delivery_no" label="发货单号"><Input placeholder="留空自动生成" /></Form.Item>
        <Form.Item name="status" label="状态">
          <Select options={[
            { value: "pending", label: "待发货" }, { value: "shipped", label: "已发货" }, { value: "delivered", label: "已签收" },
          ]} />
        </Form.Item>
        <Form.Item name="delivery_date" label="发货日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="received_date" label="签收日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>

        <Form.List name="items">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...rest }) => (
                <Space key={key} style={{ display: "flex", marginBottom: 8 }} align="baseline">
                  <Form.Item {...rest} name={[name, "product_name"]} label="产品"><Input placeholder="产品名称" /></Form.Item>
                  <Form.Item {...rest} name={[name, "quantity"]} label="数量"><InputNumber min={1} /></Form.Item>
                  <Button icon={<DeleteOutlined />} onClick={() => remove(name)} />
                </Space>
              ))}
              <Button type="dashed" icon={<PlusOutlined />} onClick={() => add()} block>添加品项</Button>
            </>
          )}
        </Form.List>

        <Form.Item style={{ marginTop: 16 }}>
          <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/delivery-notes")}>取消</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
