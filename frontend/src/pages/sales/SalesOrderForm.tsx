import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Form, Input, Select, InputNumber, DatePicker, Button, message, Space } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { getSalesOrder, createSalesOrder, updateSalesOrder, getCustomers } from "../../api";
import dayjs from "dayjs";
import type { Customer } from "../../types";

export default function SalesOrderForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const isEdit = !!id;

  useEffect(() => {
    getCustomers({ page: 1, page_size: 200 }).then((r) => setCustomers(r.data.data.list || []));
    if (isEdit) {
      getSalesOrder(Number(id)).then((r) => {
        const o = r.data.data;
        form.setFieldsValue({ ...o, order_date: o.order_date ? dayjs(o.order_date) : null, delivery_date: o.delivery_date ? dayjs(o.delivery_date) : null });
      });
    }
  }, [id]);

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
    } catch { message.error("保存失败"); }
    finally { setLoading(false); }
  };

  return (
    <Card title={isEdit ? "编辑销售订单" : "新增销售订单"}>
      <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ status: "pending", items: [{}] }}>
        <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
          <Select showSearch placeholder="选择客户" options={customers.map((c) => ({ value: c.id, label: c.name }))} />
        </Form.Item>
        <Form.Item name="order_no" label="订单号"><Input placeholder="留空自动生成" /></Form.Item>
        <Form.Item name="total_amount" label="总金额"><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
        <Form.Item name="status" label="状态">
          <Select options={[
            { value: "pending", label: "待处理" }, { value: "confirmed", label: "已确认" }, { value: "shipped", label: "已发货" },
          ]} />
        </Form.Item>
        <Form.Item name="order_date" label="下单日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="delivery_date" label="预计交货"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>

        <Form.List name="items">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...rest }) => (
                <Space key={key} style={{ display: "flex", marginBottom: 8 }} align="baseline">
                  <Form.Item {...rest} name={[name, "product_name"]} label="产品"><Input placeholder="产品名称" /></Form.Item>
                  <Form.Item {...rest} name={[name, "quantity"]} label="数量"><InputNumber min={1} /></Form.Item>
                  <Form.Item {...rest} name={[name, "unit_price"]} label="单价"><InputNumber prefix="¥" /></Form.Item>
                  <Form.Item {...rest} name={[name, "total_price"]} label="小计"><InputNumber prefix="¥" /></Form.Item>
                  <Button icon={<DeleteOutlined />} onClick={() => remove(name)} />
                </Space>
              ))}
              <Button type="dashed" icon={<PlusOutlined />} onClick={() => add()} block>添加品项</Button>
            </>
          )}
        </Form.List>

        <Form.Item style={{ marginTop: 16 }}>
          <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/orders")}>取消</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
