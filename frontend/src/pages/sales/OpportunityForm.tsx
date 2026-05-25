import { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Button, Card, DatePicker, Form, Input, InputNumber, Select, Space, message } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { getOpportunity, createOpportunity, updateOpportunity } from "../../api";
import dayjs from "dayjs";
import FormAIWarning from "../../components/sales/FormAIWarning";
import { CustomerSelect, ProductSelect, SalesModuleShell } from "./salesUi";

export default function OpportunityForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const isEdit = !!id;

  useEffect(() => {
    if (isEdit) {
      getOpportunity(Number(id)).then((r) => {
        const o = r.data.data;
        form.setFieldsValue({ ...o, expected_close_date: o.expected_close_date ? dayjs(o.expected_close_date) : null });
      });
    } else {
      const customerId = Number(searchParams.get("customer_id"));
      if (customerId) form.setFieldValue("customer_id", customerId);
    }
  }, [id, searchParams, form, isEdit]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload = { ...values, expected_close_date: values.expected_close_date ? (values.expected_close_date as string) : null };
      if (isEdit) {
        await updateOpportunity(Number(id), payload);
        message.success("商机已更新");
      } else {
        await createOpportunity(payload);
        message.success("商机已创建");
      }
      navigate("/sales/opportunities");
    } catch (err: any) { message.error(err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "保存失败"); }
    finally { setLoading(false); }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑商机" : "新增商机"}
      subtitle="把客户需求、产品方向、预计金额和推进阶段沉淀为销售管道"
      activeKey="opportunities"
      extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/opportunities")}>返回</Button>}
    >
      <Card>
        <FormAIWarning entityType="opportunity" formData={formValues} />
        <Form form={form} layout="vertical" onFinish={onFinish} onValuesChange={(_, v) => setFormValues(v)} initialValues={{ status: "active", stage: "lead", win_probability: 10 }}>
          <Space direction="vertical" size={0} style={{ width: "100%" }}>
            <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
              <CustomerSelect />
            </Form.Item>
            <Form.Item name="product_id" label="意向产品">
              <ProductSelect />
            </Form.Item>
          </Space>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input placeholder="例如：华东车规 MCU 替代机会" /></Form.Item>
          <Form.Item name="description" label="需求描述"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="amount" label="预计金额"><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
          <Form.Item name="stage" label="阶段">
            <Select options={[
              { value: "lead", label: "线索" }, { value: "qualified", label: "需求确认" },
              { value: "proposal", label: "方案/报价" }, { value: "negotiation", label: "谈判" },
              { value: "closed_won", label: "赢单" }, { value: "closed_lost", label: "输单" },
            ]} />
          </Form.Item>
          <Form.Item name="win_probability" label="赢单概率(%)"><InputNumber min={0} max={100} style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="expected_close_date" label="预计成交日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="assigned_to" label="负责人"><Input /></Form.Item>
          <Form.Item name="source" label="来源"><Input /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
              <Button onClick={() => navigate("/sales/opportunities")}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </SalesModuleShell>
  );
}
