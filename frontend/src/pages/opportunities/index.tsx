import { useEffect, useState } from "react";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { getOpportunities, createOpportunity, getCustomers } from "../../api";
import type { Opportunity, Customer } from "../../types";

const stageColors: Record<string, string> = {
  lead: "default", qualified: "blue", proposal: "orange", negotiation: "purple",
  won: "green", lost: "red",
};

export default function OpportunityList() {
  const [data, setData] = useState<Opportunity[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [form] = Form.useForm();

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const resp = await getOpportunities({ page: p, page_size: 20 });
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch {
      message.error("加载机会列表失败");
    } finally {
      setLoading(false);
    }
  };

  const loadCustomers = async (q?: string) => {
    try {
      const resp = await getCustomers({ page: 1, page_size: 100, q });
      setCustomers(resp.data.data.list || []);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetch(); }, [page]);

  const handleCreate = async (values: Record<string, unknown>) => {
    try {
      await createOpportunity(values);
      message.success("机会创建成功");
      form.resetFields();
      setModalOpen(false);
      fetch(1);
    } catch {
      message.error("创建失败");
    }
  };

  const columns = [
    { title: "名称", dataIndex: "name", width: 200 },
    { title: "客户ID", dataIndex: "customer_id", width: 80 },
    { title: "阶段", dataIndex: "stage", width: 100, render: (v: string) => <Tag color={stageColors[v] || "default"}>{v}</Tag> },
    { title: "金额", dataIndex: "amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
    { title: "概率", dataIndex: "probability", width: 80, render: (v: number) => `${v}%` },
    { title: "预计成交", dataIndex: "expected_close_date", width: 120 },
    { title: "创建时间", dataIndex: "created_at", width: 180 },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: "space-between", width: "100%" }}>
        <h3>销售 Pipeline</h3>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { loadCustomers(); setModalOpen(true); }}>
          新建机会
        </Button>
      </Space>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
      <Modal title="新建机会" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
            <Select showSearch allowClear placeholder="选择客户" onSearch={loadCustomers} filterOption={false}>
              {customers.map((c) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="amount" label="金额"><Input type="number" /></Form.Item>
          <Form.Item name="stage" label="阶段">
            <Select>
              {Object.keys(stageColors).map((k) => <Select.Option key={k} value={k}>{k}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="probability" label="概率(%)"><Input type="number" min={0} max={100} /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
