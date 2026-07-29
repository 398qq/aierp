import { useRef, useState } from "react";
import { App, Button, Modal, Tag, Space, Popconfirm } from "antd";
import { PlusOutlined, PlayCircleOutlined } from "@ant-design/icons";
import type { ProColumns, ActionType } from "@ant-design/pro-components";
import {
  ProForm,
  ProFormDigit,
  ProFormSelect,
  ProFormSwitch,
  ProFormText,
  ProTable,
} from "@ant-design/pro-components";
import { getApiErrorMessage } from "@/api/client";
import client from "@/api/client";
import type { APIResponse } from "@/types";

interface ReleaseRule {
  id: number;
  name: string;
  rule_type: "no_followup" | "no_order";
  condition_days: number;
  target_status: string | null;
  is_enabled: boolean;
  priority: number;
  notify_owner: boolean;
  created_at: string | null;
}

const RULE_TYPE_LABELS: Record<string, string> = { no_followup: "无跟进释放", no_order: "无订单释放" };
const RULE_TYPE_COLORS: Record<string, string> = { no_followup: "orange", no_order: "blue" };

export default function ReleaseRulesPage() {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ReleaseRule | null>(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [form] = ProForm.useForm();

  const handleCreate = () => {
    setEditingRule(null);
    form.resetFields();
    form.setFieldsValue({ rule_type: "no_followup", condition_days: 90, is_enabled: true, notify_owner: true, priority: 0 });
    setModalOpen(true);
  };

  const handleEdit = (rule: ReleaseRule) => {
    setEditingRule(rule);
    form.setFieldsValue(rule);
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      if (editingRule) {
        await client.put(`/customers/release-rules/${editingRule.id}`, values);
        message.success("规则已更新");
      } else {
        await client.post("/customers/release-rules", values);
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
      await client.delete(`/customers/release-rules/${id}`);
      message.success("规则已删除");
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "删除失败"));
    }
  };

  const handleRunCheck = async () => {
    setRunning(true);
    try {
      await client.post("/customers/release-rules/run-check");
      message.success("释放检查已完成");
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "释放检查失败"));
    } finally {
      setRunning(false);
    }
  };

  const columns: ProColumns<ReleaseRule>[] = [
    { title: "优先级", dataIndex: "priority", width: 60 },
    { title: "规则名称", dataIndex: "name" },
    {
      title: "类型", dataIndex: "rule_type", width: 120,
      render: (_, r) => <Tag color={RULE_TYPE_COLORS[r.rule_type]}>{RULE_TYPE_LABELS[r.rule_type]}</Tag>,
    },
    {
      title: "触发天数", dataIndex: "condition_days", width: 100,
      render: (_, r) => `${r.condition_days} 天`,
    },
    {
      title: "通知原负责人", dataIndex: "notify_owner", width: 120,
      render: (_, r) => r.notify_owner ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: "启用", dataIndex: "is_enabled", width: 60,
      render: (_, r) => r.is_enabled ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
    },
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

  return (
    <>
      <ProTable<ReleaseRule>
        actionRef={actionRef}
        rowKey="id"
        headerTitle="释放规则管理"
        columns={columns}
        request={async () => {
          const res = await client.get<APIResponse<ReleaseRule[]>>("/customers/release-rules");
          return { data: (res.data?.data as ReleaseRule[]) || [], success: true };
        }}
        toolBarRender={() => [
          <Button key="run" icon={<PlayCircleOutlined />} loading={running} onClick={handleRunCheck}>
            立即执行释放检查
          </Button>,
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建规则
          </Button>,
        ]}
        search={false}
        pagination={false}
      />

      <Modal
        title={editingRule ? "编辑释放规则" : "新建释放规则"}
        open={modalOpen}
        okText="保存"
        cancelText="取消"
        confirmLoading={saving}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
      >
        <ProForm form={form} layout="vertical" submitter={false} style={{ marginTop: 16 }}>
          <ProFormText
            name="name"
            label="规则名称"
            rules={[{ required: true, message: "请输入规则名称" }]}
            placeholder="例：90天无跟进自动释放"
          />
          <ProFormSelect
            name="rule_type"
            label="规则类型"
            rules={[{ required: true }]}
            options={[
              { label: "无跟进释放", value: "no_followup" },
              { label: "无订单释放", value: "no_order" },
            ]}
          />
          <ProFormDigit
            name="condition_days"
            label="触发天数"
            rules={[{ required: true }]}
            min={1}
            max={9999}
            fieldProps={{ style: { width: "100%" }, placeholder: "超过此天数无跟进/订单则释放" }}
          />
          <ProFormDigit
            name="priority"
            label="优先级（数字越小越优先）"
            min={0}
            fieldProps={{ style: { width: "100%" } }}
          />
          <ProFormSwitch name="is_enabled" label="启用" />
          <ProFormSwitch name="notify_owner" label="释放前通知原负责人" />
        </ProForm>
      </Modal>
    </>
  );
}
