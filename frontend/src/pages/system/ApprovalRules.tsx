import { useEffect, useState } from "react";
import { Table, Button, Space, Modal, Form, Input, InputNumber, Select, Switch, message, Card, Popconfirm, Tag } from "antd";
import { StatusTag } from "../../ui";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import client from "../../api/client";

interface ApprovalRule {
  id: number; doc_type: string; min_amount: number;
  customer_level: string | null; flow_config: { level: number; approver_role?: string; approver_id?: number }[];
  enabled: boolean; created_at: string;
}

const docTypeOptions = [
  { value: "quotation", label: "报价单" },
  { value: "purchase_order", label: "采购订单" },
];

export default function ApprovalRules() {
  const [data, setData] = useState<ApprovalRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ApprovalRule | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const fetch = async () => {
    setLoading(true);
    try {
      const resp = await client.get("/approvals/rules");
      setData(resp.data.data || []);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ enabled: true, min_amount: 0, flow_config: [] }); setModalOpen(true); };
  const openEdit = (r: ApprovalRule) => { setEditing(r); form.setFieldsValue(r); setModalOpen(true); };

  const handleSave = async () => {
    const vals = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await client.put(`/approvals/rules/${editing.id}`, vals);
      } else {
        await client.post("/approvals/rules", vals);
      }
      message.success(editing ? "更新成功" : "创建成功");
      setModalOpen(false);
      fetch();
    } catch { message.error("保存失败"); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    try { await client.delete(`/approvals/rules/${id}`); message.success("已删除"); fetch(); }
    catch { message.error("删除失败"); }
  };

  const columns: ColumnsType<ApprovalRule> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "单据类型", dataIndex: "doc_type", width: 100, render: (v: string) => docTypeOptions.find(d => d.value === v)?.label || v },
    { title: "最小金额", dataIndex: "min_amount", width: 100, render: (v: number) => `¥${v.toLocaleString()}` },
    { title: "审批层级", key: "levels", width: 100, render: (_, r) => (r.flow_config || []).length || 1 },
    {
      title: "状态", dataIndex: "enabled", width: 80,
      render: (v: boolean) => <StatusTag tone={v ? "success" : "neutral"}>{v ? "启用" : "禁用"}</StatusTag>,
    },
    { title: "创建时间", dataIndex: "created_at", width: 160, render: (v: string) => v?.slice(0, 19).replace("T", " ") },
    {
      title: "操作", key: "op", width: 160,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card title="审批规则" extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建规则</Button>}>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={false} />
      <Modal title={editing ? "编辑规则" : "新建规则"} open={modalOpen}
        onOk={handleSave} onCancel={() => setModalOpen(false)} confirmLoading={saving} width={500}>
        <Form form={form} layout="vertical">
          <Form.Item name="doc_type" label="单据类型" rules={[{ required: true }]}>
            <Select options={docTypeOptions} />
          </Form.Item>
          <Form.Item name="min_amount" label="最小金额阈值">
            <InputNumber min={0} style={{ width: "100%" }} addonBefore="¥" />
          </Form.Item>
          <Form.Item name="customer_level" label="客户等级要求">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.List name="flow_config">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...rest }) => (
                  <Space key={key} align="baseline">
                    <Form.Item {...rest} name={[name, "level"]} label="级别">
                      <InputNumber min={1} style={{ width: 70 }} />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, "approver_role"]} label="审批角色">
                      <Input placeholder="如: sales_manager" />
                    </Form.Item>
                    <Button size="small" danger onClick={() => remove(name)}>删除</Button>
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add({ level: fields.length + 1 })} block>
                  + 添加审批层级
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </Card>
  );
}
