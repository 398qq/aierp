import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Form, Input, Select, Button, message, Card, Space, InputNumber, Table } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { getSalesOrder, createSalesOrder, updateSalesOrder, getSalesOrderItems, createSalesOrderItem, deleteSalesOrderItem, getCustomers, getProducts } from "../../api";
import type { Customer, Product, SalesOrderItem } from "../../types";

const statusColors: Record<string, string> = {
  pending: "orange", confirmed: "blue", shipped: "cyan", delivered: "green", cancelled: "red",
};

export default function SalesOrderForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [items, setItems] = useState<Partial<SalesOrderItem>[]>([]);
  const isEdit = Boolean(id);

  const loadCustomers = async (q?: string) => {
    try { const r = await getCustomers({ page: 1, page_size: 100, q }); setCustomers(r.data.data.list || []); } catch {}
  };
  const loadProducts = async (q?: string) => {
    try { const r = await getProducts({ page: 1, page_size: 100, q }); setProducts(r.data.data.list || []); } catch {}
  };

  useEffect(() => {
    loadCustomers();
    loadProducts();
    if (id) {
      Promise.all([getSalesOrder(Number(id)), getSalesOrderItems(Number(id))]).then(([orderR, itemsR]) => {
        form.setFieldsValue(orderR.data.data);
        setItems((itemsR.data.data as SalesOrderItem[]) || []);
      }).catch(() => message.error("加载失败"));
    }
  }, [id, form]);

  const addItem = () => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0, amount: 0 }]);

  const updateItemField = (idx: number, field: string, value: number) => {
    const newItems = [...items];
    newItems[idx] = { ...newItems[idx], [field]: value };
    if (field === "quantity" || field === "unit_price") {
      const qty = newItems[idx].quantity || 0;
      const price = newItems[idx].unit_price || 0;
      newItems[idx].amount = qty * price;
    }
    setItems(newItems);
  };

  const removeItem = (idx: number) => setItems(items.filter((_, i) => i !== idx));

  const handleSubmit = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const totalAmount = items.reduce((sum, item) => sum + (item.amount || 0), 0);
      const payload = { ...values, total_amount: totalAmount };
      const parentId = isEdit
        ? (await updateSalesOrder(Number(id), payload), Number(id))
        : ((await createSalesOrder(payload)).data.data as { id: number }).id;

      if (isEdit) {
        const existing = (await getSalesOrderItems(Number(id))).data.data as SalesOrderItem[];
        for (const ex of existing) await deleteSalesOrderItem(Number(id), ex.id);
      }
      for (const item of items) {
        if (item.product_id) {
          await createSalesOrderItem(parentId, item as Record<string, unknown>);
        }
      }

      message.success(isEdit ? "更新成功" : "创建成功");
      navigate("/sales/orders");
    } catch { message.error("操作失败"); } finally { setLoading(false); }
  };

  const itemColumns = [
    { title: "产品", width: 200, render: (_: unknown, __: unknown, idx: number) => (
      <Select showSearch value={items[idx].product_id || undefined} onChange={(v) => updateItemField(idx, "product_id", v)}
        onSearch={loadProducts} filterOption={false} style={{ width: "100%" }} placeholder="选择产品">
        {products.map((p) => <Select.Option key={p.id} value={p.id}>{p.name}</Select.Option>)}
      </Select>
    )},
    { title: "数量", width: 100, render: (_: unknown, __: unknown, idx: number) => (
      <InputNumber min={1} value={items[idx].quantity} onChange={(v) => updateItemField(idx, "quantity", v || 0)} />
    )},
    { title: "单价", width: 120, render: (_: unknown, __: unknown, idx: number) => (
      <InputNumber min={0} value={items[idx].unit_price} onChange={(v) => updateItemField(idx, "unit_price", v || 0)} />
    )},
    { title: "金额", width: 120, render: (_: unknown, __: unknown, idx: number) => (
      `¥${(items[idx].amount || 0).toLocaleString()}`
    )},
    {
      title: "", width: 60, render: (_: unknown, __: unknown, idx: number) => (
        <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeItem(idx)} />
      ),
    },
  ];

  return (
    <div>
      <h3>{isEdit ? "编辑销售订单" : "新建销售订单"}</h3>
      <Card style={{ maxWidth: 800, marginBottom: 16 }}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="order_no" label="订单号"><Input /></Form.Item>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <Select showSearch allowClear placeholder="选择客户" onSearch={loadCustomers} filterOption={false}>
              {customers.map((c) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Space>
            <Form.Item name="status" label="状态">
              <Select style={{ width: 120 }}>{Object.keys(statusColors).map((k) => <Select.Option key={k} value={k}>{k}</Select.Option>)}</Select>
            </Form.Item>
            <Form.Item name="delivery_date" label="交货日期"><Input placeholder="YYYY-MM-DD" /></Form.Item>
          </Space>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Card>

      <Card title="订单项" extra={<Button icon={<PlusOutlined />} onClick={addItem}>添加行</Button>} style={{ marginBottom: 16 }}>
        <Table rowKey="idx" columns={itemColumns} dataSource={items.map((item, idx) => ({ ...item, idx }))} pagination={false} />
      </Card>

      <Button type="primary" loading={loading} onClick={() => form.submit()}>{isEdit ? "保存" : "创建"}</Button>
      <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/orders")}>取消</Button>
    </div>
  );
}
