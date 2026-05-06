import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Form, Input, Select, Button, message, Card } from "antd";
import { getOpportunity, createOpportunity, updateOpportunity, getCustomers } from "../../api";
import type { Customer } from "../../types";

const stageColors: Record<string, string> = {
  lead: "default", qualified: "blue", proposal: "orange", negotiation: "purple",
  won: "green", lost: "red",
};

export default function OpportunityForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const isEdit = Boolean(id);

  const loadCustomers = async (q?: string) => {
    try {
      const resp = await getCustomers({ page: 1, page_size: 100, q });
      setCustomers(resp.data.data.list || []);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    loadCustomers();
    if (id) {
      getOpportunity(Number(id)).then((r) => {
        form.setFieldsValue(r.data.data);
      }).catch(() => message.error("加载失败"));
    }
  }, [id, form]);

  const handleSubmit = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      if (isEdit) {
        await updateOpportunity(Number(id), values);
        message.success("更新成功");
      } else {
        await createOpportunity(values);
        message.success("创建成功");
      }
      navigate("/sales/opportunities");
    } catch {
      message.error("操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h3>{isEdit ? "编辑机会" : "新建机会"}</h3>
      <Card style={{ maxWidth: 720 }}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <Select showSearch allowClear placeholder="选择客户" onSearch={loadCustomers} filterOption={false}>
              {customers.map((c) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="amount" label="金额"><Input type="number" /></Form.Item>
          <Form.Item name="stage" label="阶段">
            <Select>{Object.keys(stageColors).map((k) => <Select.Option key={k} value={k}>{k}</Select.Option>)}</Select>
          </Form.Item>
          <Form.Item name="probability" label="概率(%)"><Input type="number" min={0} max={100} /></Form.Item>
          <Form.Item name="expected_close_date" label="预计成交日期"><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
            <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/opportunities")}>取消</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
