import { useRef, useState } from "react";
import { App, Button, Modal, Form, Input, InputNumber, Select, Switch, Tag, Space, Popconfirm, Tooltip } from "antd";
import { PlusOutlined, PlayCircleOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ProColumns, ActionType } from "@ant-design/pro-components";
import { ProForm, ProTable } from "@ant-design/pro-components";
import { getApiErrorMessage } from "@/api/client";
import client from "@/api/client";
import type { APIResponse } from "@/types";

interface Condition { id?: number; field: string; operator: string; value: string; }

interface AssignmentRule {
  id: number; name: string; priority: number; condition_logic: "all" | "any";
  assigned_to: string; max_customers: number | null; is_enabled: boolean;
  created_at: string | null; conditions: Condition[];
}

const FIELD_LABELS: Record<string, string> = { industry: "行业", region: "区域", source: "来源", level: "客户等级", customer_type: "客户类型" };
const OPERATOR_LABELS: Record<string, string> = { equals: "等于", in: "包含于", contains: "包含", not_empty: "不为空" };
const CONDITION_LOGIC_LABELS: Record<string, string> = { all: "满足全部条件", any: "满足任一条件" };

export default function AssignmentRulesPage() {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AssignmentRule | null>(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [form] = ProForm.useForm();

  const handleCreate = () => {
    setEditingRule(null);
    form.resetFields();
    form.setFieldsValue({ priority: 0, condition_logic: "all", is_enabled: true, max_customers: 100, conditions: [{ field: "industry", operator: "equals", value: "" }] });
    setModalOpen(true);
  };

  const handleEdit = (rule: AssignmentRule) => {
    setEditingRule(rule);
    form.setFieldsValue({
      ...rule,
      conditions: rule.conditions.length > 0 ? rule.conditions : [{ field: "industry", operator: "equals", value: "" }],
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      if (editingRule) {
        await client.put(`/customers/assignment-rules/${editingRule.id}`, values);
        message.success("规则已更新");
      } else {
        await client.post("/customers/assignment-rules", values);
        message.success("规则已创建");
      }
      setModalOpen(false);
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "保存失败"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await client.delete(`/customers/assignment-rules/${id}`);
      message.success("规则已删除");
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "删除失败"));
    }
  };

  const handleRunAssign = async () => {
    setRunning(true);
    try {
      const res = await client.post<APIResponse<{ assigned: number; rules_checked: number }>>("/customers/assignment-rules/run");
      const d = res.data?.data;
      if (d) message.success(`自动分配完成：已分配 ${d.assigned} 个客户，检查了 ${d.rules_checked} 条规则`);
      else message.success("自动分配完成");
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "自动分配失败"));
    } finally {
      setRunning(false);
    }
  };

  const handleMoveUp = async (rules: AssignmentRule[], index: number) => {
    if (index <= 0) return;
    const ids = rules.map((r) => r.id);
    [ids[index - 1], ids[index]] = [ids[index], ids[index - 1]];
    try {
      await client.post("/customers/assignment-rules/reorder", { ids });
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "排序失败"));
    }
  };

  const handleMoveDown = async (rules: AssignmentRule[], index: number) => {
    if (index >= rules.length - 1) return;
    const ids = rules.map((r) => r.id);
    [ids[index], ids[index + 1]] = [ids[index + 1], ids[index]];
    try {
      await client.post("/customers/assignment-rules/reorder", { ids });
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "排序失败"));
    }
  };

  const columns: ProColumns<AssignmentRule>[] = [
    {
      title: "排序", key: "sort", width: 80,
      render: (_, r, index) => (
        <Space>
          <Tooltip title="上移"><Button size="small" type="text" disabled={index === 0} onClick={() => handleMoveUp(_rules, index)}>↑</Button></Tooltip>
          <Tooltip title="下移"><Button size="small" type="text" disabled={index === _rules.length - 1} onClick={() => handleMoveDown(_rules, index)}>↓</Button></Tooltip>
        </Space>
      ),
    },
    { title: "规则名称", dataIndex: "name" },
    { title: "匹配逻辑", dataIndex: "condition_logic", width: 120, render: (_, r) => <Tag>{CONDITION_LOGIC_LABELS[r.condition_logic]}</Tag> },
    { title: "分配给", dataIndex: "assigned_to", width: 100 },
    { title: "上限", dataIndex: "max_customers", width: 80, render: (_, r) => r.max_customers ?? "不限" },
    {
      title: "条件", key: "conditions",
      render: (_, r) => r.conditions.length > 0
        ? r.conditions.map((c, i) => <Tag key={i} style={{ marginBottom: 2 }}>{FIELD_LABELS[c.field]} {OPERATOR_LABELS[c.operator]} {c.value}</Tag>)
        : <Tag color="default">无条件</Tag>,
    },
    { title: "启用", dataIndex: "is_enabled", width: 60, render: (_, r) => r.is_enabled ? <Tag color="green">是</Tag> : <Tag>否</Tag> },
    {
      title: "操作", key: "actions", width: 150,
      render: (_, r) => (
        <Space>
          <Button size="small" onClick={() => handleEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除此规则？" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  let _rules: AssignmentRule[] = [];

  return (
    <>
      <ProTable<AssignmentRule>
        actionRef={actionRef}
        rowKey="id"
        headerTitle="自动分配规则管理"
        columns={columns}
        request={async () => {
          const res = await client.get<APIResponse<AssignmentRule[]>>("/customers/assignment-rules");
          _rules = (res.data?.data as AssignmentRule[]) || [];
          return { data: _rules, success: true };
        }}
        toolBarRender={() => [
          <Button key="run" icon={<PlayCircleOutlined />} loading={running} onClick={handleRunAssign}>
            立即执行自动分配
          </Button>,
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建规则
          </Button>,
        ]}
        search={false}
        pagination={false}
      />

      <Modal
        title={editingRule ? "编辑分配规则" : "新建分配规则"}
        open={modalOpen}
        okText="保存"
        cancelText="取消"
        confirmLoading={saving}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        width={640}
      >
        <ProForm form={form} layout="vertical" submitter={false} style={{ marginTop: 16 }}>
          <Form.Item name="name" label="规则名称" rules={[{ required: true, message: "请输入规则名称" }]}>
            <Input placeholder="例：高价值制造业客户自动分配" />
          </Form.Item>
          <Form.Item name="assigned_to" label="分配给（用户名）" rules={[{ required: true, message: "请输入负责人用户名" }]}>
            <Input placeholder="输入用户名" />
          </Form.Item>
          <Space style={{ width: "100%" }} size="middle">
            <Form.Item name="condition_logic" label="条件匹配逻辑" rules={[{ required: true }]}>
              <Select style={{ width: 180 }} options={[
                { label: "满足全部条件（AND）", value: "all" },
                { label: "满足任一条件（OR）", value: "any" },
              ]} />
            </Form.Item>
            <Form.Item name="max_customers" label="分配上限（留空不限）">
              <InputNumber min={1} style={{ width: 140 }} placeholder="留空则不限制" />
            </Form.Item>
          </Space>
          <Form.Item name="is_enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
          <Form.List name="conditions">
            {(fields, { add, remove }) => (
              <>
                <div style={{ fontWeight: 500, marginBottom: 8 }}>匹配条件</div>
                {fields.map(({ key, name, ...restField }) => (
                  <Space key={key} align="baseline" style={{ display: "flex", marginBottom: 8 }}>
                    <Form.Item {...restField} name={[name, "field"]} rules={[{ required: true }]}>
                      <Select style={{ width: 130 }} options={Object.entries(FIELD_LABELS).map(([k, v]) => ({ label: v, value: k }))} />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, "operator"]} rules={[{ required: true }]}>
                      <Select style={{ width: 160 }} options={Object.entries(OPERATOR_LABELS).map(([k, v]) => ({ label: v, value: k }))} />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, "value"]} rules={[{ required: true }]}>
                      <Input style={{ width: 160 }} placeholder="值" />
                    </Form.Item>
                    <DeleteOutlined onClick={() => remove(name)} style={{ color: "#ff4d4f" }} />
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add({ field: "industry", operator: "equals", value: "" })} block icon={<PlusOutlined />}>
                  添加条件
                </Button>
              </>
            )}
          </Form.List>
        </ProForm>
      </Modal>
    </>
  );
}
