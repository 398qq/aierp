import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Form, Input, Select, InputNumber, DatePicker, Button, message, Spin } from "antd";
import { getOpportunity, createOpportunity, updateOpportunity, getCustomers } from "../../api";
import dayjs from "dayjs";
import type { Customer } from "../../types";
import FormAIWarning from "../../components/sales/FormAIWarning";

export default function OpportunityForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const isEdit = !!id;

  useEffect(() => {
    getCustomers({ page: 1, page_size: 200 }).then((r) => setCustomers(r.data.data.list || []));
    if (isEdit) {
      getOpportunity(Number(id)).then((r) => {
        const o = r.data.data;
        form.setFieldsValue({ ...o, expected_close_date: o.expected_close_date ? dayjs(o.expected_close_date) : null });
      });
    }
  }, [id]);

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
    } catch { message.error("保存失败"); }
    finally { setLoading(false); }
  };

  return (
    <Card title={isEdit ? "编辑商机" : "新增商机"}>
      <FormAIWarning entityType="opportunity" formData={formValues} />
      <Form form={form} layout="vertical" onFinish={onFinish} onValuesChange={(_, v) => setFormValues(v)} initialValues={{ status: "active", win_probability: 10 }}>
        <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
          <Select showSearch placeholder="选择客户" options={customers.map((c) => ({ value: c.id, label: c.name }))} />
        </Form.Item>
        <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="description" label="描述"><Input.TextArea rows={3} /></Form.Item>
        <Form.Item name="amount" label="金额"><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
        <Form.Item name="stage" label="阶段">
          <Select options={[
            { value: "lead", label: "初步接触" }, { value: "qualified", label: "已确认" },
            { value: "proposal", label: "报价中" }, { value: "negotiation", label: "谈判" },
            { value: "closed_won", label: "赢单" }, { value: "closed_lost", label: "丢单" },
          ]} />
        </Form.Item>
        <Form.Item name="win_probability" label="赢单概率(%)"><InputNumber min={0} max={100} /></Form.Item>
        <Form.Item name="expected_close_date" label="预计成交日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="assigned_to" label="负责人"><Input /></Form.Item>
        <Form.Item name="source" label="来源"><Input /></Form.Item>
        <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/opportunities")}>取消</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
