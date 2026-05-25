import { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Button, Card, DatePicker, Form, Input, InputNumber, Select, Space, message } from "antd";
import { ArrowLeftOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { getQuotation, createQuotation, updateQuotation } from "../../api";
import dayjs from "dayjs";
import FormAIWarning from "../../components/sales/FormAIWarning";
import { CustomerSelect, ProductSelect, SalesModuleShell } from "./salesUi";

export default function QuotationForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const isEdit = !!id;

  useEffect(() => {
    if (isEdit) {
      getQuotation(Number(id)).then((r) => {
        const q = r.data.data;
        form.setFieldsValue({ ...q, valid_until: q.valid_until ? dayjs(q.valid_until) : null });
      });
    } else {
      const customerId = Number(searchParams.get("customer_id"));
      const opportunityId = Number(searchParams.get("opportunity_id"));
      if (customerId) form.setFieldValue("customer_id", customerId);
      if (opportunityId) form.setFieldValue("opportunity_id", opportunityId);
    }
  }, [id, isEdit, searchParams, form]);

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
    } catch (err: any) { message.error(err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "保存失败"); }
    finally { setLoading(false); }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑报价单" : "新增报价单"}
      subtitle="把客户需求转成可执行的产品报价，沉淀产品行和金额"
      activeKey="quotations"
      extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/quotations")}>返回</Button>}
    >
      <Card>
        <FormAIWarning entityType="quotation" formData={formValues} />
        <Form form={form} layout="vertical" onFinish={onFinish} onValuesChange={(_, v) => setFormValues(v)} initialValues={{ status: "draft", items: [{}] }}>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <CustomerSelect />
          </Form.Item>
          <Form.Item name="opportunity_id" label="关联商机"><InputNumber style={{ width: "100%" }} placeholder="可由商机页面带入" /></Form.Item>
          <Form.Item name="title" label="标题"><Input placeholder="报价主题" /></Form.Item>
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
              <Button onClick={() => navigate("/sales/quotations")}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </SalesModuleShell>
  );
}
