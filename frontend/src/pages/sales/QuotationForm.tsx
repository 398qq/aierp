import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Form, Input, Select, InputNumber, DatePicker, Button, message, Space } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { getQuotation, createQuotation, updateQuotation, getCustomers, getProducts } from "../../api";
import dayjs from "dayjs";
import type { Customer, Product } from "../../types";
import FormAIWarning from "../../components/sales/FormAIWarning";

export default function QuotationForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [productOptions, setProductOptions] = useState<Product[]>([]);
  const [productSearch, setProductSearch] = useState("");
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const isEdit = !!id;

  useEffect(() => {
    getCustomers({ page: 1, page_size: 200 }).then((r) => setCustomers(r.data.data.list || []));
    if (isEdit) {
      getQuotation(Number(id)).then((r) => {
        const q = r.data.data;
        form.setFieldsValue({ ...q, valid_until: q.valid_until ? dayjs(q.valid_until) : null });
      });
    }
  }, [id]);

  const handleProductSearch = async (v: string) => {
    setProductSearch(v);
    if (v.length < 1) { setProductOptions([]); return; }
    try {
      const resp = await getProducts({ q: v, page_size: 20 });
      setProductOptions((resp.data.data.list || []) as Product[]);
    } catch { /* */ }
  };

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload = { ...values, valid_until: values.valid_until ? (values.valid_until as string) : null, items: values.items || [] };
      if (isEdit) {
        await updateQuotation(Number(id), payload);
        message.success("报价单已更新");
      } else {
        await createQuotation(payload);
        message.success("报价单已创建");
      }
      navigate("/sales/quotations");
    } catch { message.error("保存失败"); }
    finally { setLoading(false); }
  };

  return (
    <Card title={isEdit ? "编辑报价单" : "新增报价单"}>
      <FormAIWarning entityType="quotation" formData={formValues} />
      <Form form={form} layout="vertical" onFinish={onFinish} onValuesChange={(_, v) => setFormValues(v)} initialValues={{ status: "draft", items: [{}] }}>
        <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
          <Select showSearch placeholder="选择客户" options={customers.map((c) => ({ value: c.id, label: c.name }))} />
        </Form.Item>
        <Form.Item name="title" label="标题"><Input /></Form.Item>
        <Form.Item name="quotation_no" label="报价单号"><Input placeholder="留空自动生成" /></Form.Item>
        <Form.Item name="total_amount" label="总金额"><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
        <Form.Item name="status" label="状态">
          <Select options={[
            { value: "draft", label: "草稿" }, { value: "sent", label: "已发送" }, { value: "won", label: "成交" }, { value: "lost", label: "丢失" },
          ]} />
        </Form.Item>
        <Form.Item name="valid_until" label="有效期"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>

        <Form.List name="items">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...rest }) => (
                <Space key={key} style={{ display: "flex", marginBottom: 8 }} align="baseline">
                  <Form.Item {...rest} name={[name, "product_name"]} hidden />
                  <Form.Item {...rest} name={[name, "product_id"]} label="产品" rules={[{ required: true, message: "请选择产品" }]}>
                    <Select
                      showSearch placeholder="搜索并选择产品" filterOption={false} onSearch={handleProductSearch}
                      options={productOptions.map((p) => ({ value: p.id, label: `[${p.sku || "?"}] ${p.name}` }))}
                    />
                  </Form.Item>
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
          <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/quotations")}>取消</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
