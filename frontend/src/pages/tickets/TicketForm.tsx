import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Form, Input, Select, Button, message, Spin } from "antd";
import { getTicket, createTicket, updateTicket } from "../../api";
import { getCustomers } from "../../api";
import type { Ticket } from "../../types";

const STATUS_OPTIONS = [
  { value: "open", label: "待处理" },
  { value: "in_progress", label: "处理中" },
  { value: "resolved", label: "已解决" },
  { value: "closed", label: "已关闭" },
];

const PRIORITY_OPTIONS = [
  { value: "low", label: "低" },
  { value: "medium", label: "中" },
  { value: "high", label: "高" },
];

const CATEGORY_OPTIONS = [
  { value: "质量问题", label: "质量问题" },
  { value: "技术咨询", label: "技术咨询" },
  { value: "售后支持", label: "售后支持" },
  { value: "产品需求", label: "产品需求" },
  { value: "其他", label: "其他" },
];

export default function TicketForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [customers, setCustomers] = useState<{ value: number; label: string }[]>([]);
  const isEdit = !!id;

  useEffect(() => {
    getCustomers({ page: 1, page_size: 200 }).then(r => {
      const list = r.data.data?.list || [];
      setCustomers(list.map((c: any) => ({ value: c.id, label: c.name })));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (isEdit) {
      setDetailLoading(true);
      getTicket(Number(id))
        .then((r) => {
          form.setFieldsValue(r.data.data);
        })
        .catch(() => message.error("加载工单失败"))
        .finally(() => setDetailLoading(false));
    }
  }, [id]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      if (isEdit) {
        await updateTicket(Number(id), values);
        message.success("工单已更新");
      } else {
        await createTicket(values);
        message.success("工单已创建");
      }
      navigate("/tickets");
    } catch { message.error("保存失败"); }
    finally { setLoading(false); }
  };

  if (detailLoading) return <Spin style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Card title={isEdit ? "编辑工单" : "新建工单"}>
      <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ status: "open", priority: "medium" }}>
        <Form.Item name="title" label="标题" rules={[{ required: true }]}>
          <Input placeholder="请输入工单标题" />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <Input.TextArea rows={4} placeholder="请输入工单描述" />
        </Form.Item>
        <Form.Item name="customer_id" label="客户">
          <Select placeholder="选择客户" allowClear options={customers} showSearch filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())} />
        </Form.Item>
        <Form.Item name="category" label="分类">
          <Select placeholder="选择分类" options={CATEGORY_OPTIONS} />
        </Form.Item>
        <Form.Item name="status" label="状态">
          <Select options={STATUS_OPTIONS} />
        </Form.Item>
        <Form.Item name="priority" label="优先级">
          <Select options={PRIORITY_OPTIONS} />
        </Form.Item>
        <Form.Item name="assigned_to" label="处理人">
          <Input placeholder="请输入处理人" />
        </Form.Item>
        <Form.Item name="notes" label="备注">
          <Input.TextArea rows={2} placeholder="备注信息" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate("/tickets")}>取消</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
