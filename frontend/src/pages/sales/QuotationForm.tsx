import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Form, Input, Select, Button, message, Card, Space, InputNumber, Table, Popconfirm, Modal, Tag, Progress, List, Typography, Row, Col } from "antd";
import { PlusOutlined, DeleteOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { getQuotation, createQuotation, updateQuotation, getQuotationItems, createQuotationItem, updateQuotationItem, deleteQuotationItem, getCustomers, getProducts, getQuoteAssist } from "../../api";
import type { Customer, Product, QuotationItem, QuoteAssistResult } from "../../types";

const { Text } = Typography;

const statusColors: Record<string, string> = {
  draft: "default", sent: "blue", approved: "green", rejected: "red", expired: "orange",
};

export default function QuotationForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [items, setItems] = useState<Partial<QuotationItem>[]>([]);
  const [assistOpen, setAssistOpen] = useState(false);
  const [assistResult, setAssistResult] = useState<QuoteAssistResult | null>(null);
  const [assistLoading, setAssistLoading] = useState(false);
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
      Promise.all([getQuotation(Number(id)), getQuotationItems(Number(id))]).then(([quoR, itemsR]) => {
        form.setFieldsValue(quoR.data.data);
        setItems((itemsR.data.data as QuotationItem[]) || []);
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

  const handleAssist = async () => {
    const customerId = form.getFieldValue("customer_id");
    if (!customerId) { message.warning("请先选择客户"); return; }
    if (items.length === 0) { message.warning("请先添加报价项"); return; }
    setAssistLoading(true);
    try {
      const resp = await getQuoteAssist(customerId, items.filter(i => i.product_id).map(i => ({ product_id: i.product_id!, quantity: i.quantity || 1 })));
      if (resp.data.code === 0) {
        setAssistResult(resp.data.data as QuoteAssistResult);
        setAssistOpen(true);
      }
    } catch { message.error("AI 辅助分析失败"); }
    finally { setAssistLoading(false); }
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const totalAmount = items.reduce((sum, item) => sum + (item.amount || 0), 0);
      const payload = { ...values, total_amount: totalAmount };
      const parentId = isEdit
        ? (await updateQuotation(Number(id), payload), Number(id))
        : ((await createQuotation(payload)).data.data as { id: number }).id;

      if (!isEdit) {
        for (const item of items) {
          if (item.product_id) await createQuotationItem(parentId, item as Record<string, unknown>);
        }
      } else {
        const existing = (await getQuotationItems(Number(id))).data.data as QuotationItem[];
        for (const ex of existing) await deleteQuotationItem(Number(id), ex.id);
        for (const item of items) {
          if (item.product_id) await createQuotationItem(Number(id), item as Record<string, unknown>);
        }
      }

      message.success(isEdit ? "更新成功" : "创建成功");
      navigate("/sales/quotations");
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
      <h3>{isEdit ? "编辑报价单" : "新建报价单"}</h3>
      <Card style={{ maxWidth: 800, marginBottom: 16 }}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="quotation_no" label="报价单号"><Input /></Form.Item>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <Select showSearch allowClear placeholder="选择客户" onSearch={loadCustomers} filterOption={false}>
              {customers.map((c) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Space>
            <Form.Item name="status" label="状态">
              <Select style={{ width: 120 }}>{Object.keys(statusColors).map((k) => <Select.Option key={k} value={k}>{k}</Select.Option>)}</Select>
            </Form.Item>
            <Form.Item name="valid_until" label="有效期至"><Input placeholder="YYYY-MM-DD" /></Form.Item>
          </Space>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Card>

      <Card title="报价项" extra={<Button icon={<PlusOutlined />} onClick={addItem}>添加行</Button>} style={{ marginBottom: 16 }}>
        <Table rowKey="idx" columns={itemColumns} dataSource={items.map((item, idx) => ({ ...item, idx }))} pagination={false} />
      </Card>

      <Button type="primary" loading={loading} onClick={() => form.submit()}>{isEdit ? "保存" : "创建"}</Button>
      <Button icon={<ThunderboltOutlined />} loading={assistLoading} onClick={handleAssist} style={{ marginLeft: 8 }}>AI 辅助</Button>
      <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/quotations")}>取消</Button>

      {/* AI Assist Modal */}
      <Modal title="AI 报价辅助" open={assistOpen} onCancel={() => setAssistOpen(false)} width={800}
        footer={<Button onClick={() => setAssistOpen(false)}>关闭</Button>}>
        {assistResult && (
          <div>
            <Row gutter={[12, 12]}>
              <Col span={6}>
                <Card size="small" type="inner" style={{ textAlign: "center" }}>
                  <Text type="secondary">赢单概率</Text>
                  <Progress type="circle" percent={assistResult.win_probability} size={80}
                    status={assistResult.win_probability > 60 ? "success" : assistResult.win_probability > 30 ? "normal" : "exception"} />
                  <div style={{ marginTop: 8 }}><Text style={{ fontSize: 12 }}>{assistResult.win_probability_reason}</Text></div>
                </Card>
              </Col>
              <Col span={10}>
                <Card size="small" type="inner" title="定价建议">
                  {assistResult.pricing_recommendations.map((p, i) => (
                    <div key={i} style={{ marginBottom: 8 }}>
                      <Text strong>{p.product_name}</Text><br/>
                      <Tag color="blue">建议价 ¥{p.recommended_price}</Tag>
                      <Tag>区间 ¥{p.price_range_low}~¥{p.price_range_high}</Tag>
                      <Tag color="green">毛利 {p.margin_pct}%</Tag>
                      <div><Text style={{ fontSize: 12 }} type="secondary">{p.rationale}</Text></div>
                    </div>
                  ))}
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" type="inner" title="风险提示" style={{ background: "#fffbe6" }}>
                  <Text>{assistResult.risk_summary}</Text>
                </Card>
              </Col>
              {assistResult.cross_sell_suggestions.length > 0 && (
                <Col span={12}>
                  <Card size="small" type="inner" title="交叉销售机会">
                    {assistResult.cross_sell_suggestions.map((s, i) => (
                      <Tag key={i} color="green" style={{ marginBottom: 4 }}>
                        [{s.brand_name}] {s.product_name} — {s.reason} (预计 ¥{s.estimated_value})
                      </Tag>
                    ))}
                  </Card>
                </Col>
              )}
              <Col span={12}>
                <Card size="small" type="inner" title="谈判建议">
                  <List size="small" dataSource={assistResult.negotiation_tips}
                    renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="blue">{s}</Tag></List.Item>} />
                </Card>
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  );
}
