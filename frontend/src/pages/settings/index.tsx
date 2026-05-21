import { useEffect, useState } from "react";
import {
  Card, Descriptions, Typography, Tabs, Table, Button, Modal, Form, Input, InputNumber,
  Select, Switch, Tag, Space, message, Popconfirm, Badge,
} from "antd";
import { PlusOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { useAuthStore } from "../../store/auth";
import {
  getAlertRules, createAlertRule, updateAlertRule, deleteAlertRule,
  getAlertEvents, markAlertRead, markAllAlertsRead, checkAlerts,
  getLevelRules, createLevelRule, updateLevelRule, deleteLevelRule,
  autoLevel,
  changePassword,
} from "../../api";
import type { AlertRule, AlertEvent, LevelRule } from "../../types";

const { Title, Text } = Typography;

const RULE_TYPE_LABELS: Record<string, string> = {
  no_order: "长期未下单", credit_over: "信用额度使用率", order_drop: "订单下降", ar_overdue: "应收逾期",
};
const SEVERITY_COLORS: Record<string, string> = { info: "blue", warning: "orange", critical: "red" };
const CONDITION_LABELS: Record<string, string> = {
  revenue: "累计营收", order_count: "订单数", no_order_days: "未下单天数",
};
const OPERATOR_LABELS: Record<string, string> = { ">": ">", "<": "<", ">=": ">=", "<=": "<=" };
const LEVEL_COLORS: Record<string, string> = { A: "red", B: "orange", C: "blue", D: "default" };

export default function Settings() {
  const username = useAuthStore((s) => s.username);
  const [activeTab, setActiveTab] = useState("account");
  const [passwordForm] = Form.useForm();
  const [passwordSaving, setPasswordSaving] = useState(false);

  // Alert Rules
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [arLoading, setArLoading] = useState(false);
  const [arModalOpen, setArModalOpen] = useState(false);
  const [editingAR, setEditingAR] = useState<AlertRule | null>(null);
  const [arForm] = Form.useForm();

  // Alert Events
  const [alertEvents, setAlertEvents] = useState<AlertEvent[]>([]);
  const [aeTotal, setAeTotal] = useState(0);
  const [aePage, setAePage] = useState(1);
  const [aeLoading, setAeLoading] = useState(false);
  const [aeReadFilter, setAeReadFilter] = useState<boolean | undefined>();
  const [checkLoading, setCheckLoading] = useState(false);

  // Level Rules
  const [levelRules, setLevelRules] = useState<LevelRule[]>([]);
  const [lrLoading, setLrLoading] = useState(false);
  const [lrModalOpen, setLrModalOpen] = useState(false);
  const [editingLR, setEditingLR] = useState<LevelRule | null>(null);
  const [lrForm] = Form.useForm();
  const [autoLevelLoading, setAutoLevelLoading] = useState(false);

  // ---- Data loading ----
  const loadAlertRules = async () => {
    setArLoading(true);
    try { const r = await getAlertRules(); setAlertRules(r.data.data); } catch { /* */ }
    finally { setArLoading(false); }
  };

  const loadAlertEvents = async () => {
    setAeLoading(true);
    try {
      const params: Record<string, unknown> = { page: aePage, page_size: 20 };
      if (aeReadFilter !== undefined) params.is_read = aeReadFilter;
      const r = await getAlertEvents(params);
      setAlertEvents(r.data.data.list);
      setAeTotal(r.data.data.total);
    } catch { /* */ }
    finally { setAeLoading(false); }
  };

  const loadLevelRules = async () => {
    setLrLoading(true);
    try { const r = await getLevelRules(); setLevelRules(r.data.data); } catch { /* */ }
    finally { setLrLoading(false); }
  };

  useEffect(() => { if (activeTab === "alert-rules") loadAlertRules(); }, [activeTab]);
  useEffect(() => { if (activeTab === "alert-events") loadAlertEvents(); }, [activeTab, aePage, aeReadFilter]);
  useEffect(() => { if (activeTab === "level-rules") loadLevelRules(); }, [activeTab]);

  // ---- Alert Rules CRUD ----
  const openARForm = (rule?: AlertRule) => {
    setEditingAR(rule || null);
    if (rule) arForm.setFieldsValue(rule);
    else arForm.resetFields();
    setArModalOpen(true);
  };

  const onARFinish = async (values: Record<string, unknown>) => {
    try {
      if (editingAR) {
        await updateAlertRule(editingAR.id, values as Record<string, unknown>);
        message.success("更新成功");
      } else {
        await createAlertRule(values as Record<string, unknown>);
        message.success("创建成功");
      }
      setArModalOpen(false);
      loadAlertRules();
    } catch { message.error("保存失败"); }
  };

  const handleDeleteAR = async (id: number) => {
    try { await deleteAlertRule(id); message.success("已删除"); loadAlertRules(); } catch { message.error("删除失败"); }
  };

  // ---- Alert Events ----
  const handleMarkRead = async (id: number) => {
    try { await markAlertRead(id); loadAlertEvents(); } catch { message.error("操作失败"); }
  };

  const handleMarkAllRead = async () => {
    try { await markAllAlertsRead(); message.success("已全部标记已读"); loadAlertEvents(); } catch { message.error("操作失败"); }
  };

  const handleCheckAlerts = async () => {
    setCheckLoading(true);
    try {
      const resp = await checkAlerts();
      message.success(`预警检查完成，生成 ${resp.data.data.generated} 条预警`);
      loadAlertEvents();
    } catch { message.error("预警检查失败"); }
    finally { setCheckLoading(false); }
  };

  // ---- Level Rules CRUD ----
  const openLRForm = (rule?: LevelRule) => {
    setEditingLR(rule || null);
    if (rule) lrForm.setFieldsValue(rule);
    else lrForm.resetFields();
    setLrModalOpen(true);
  };

  const onLRFinish = async (values: Record<string, unknown>) => {
    try {
      if (editingLR) {
        await updateLevelRule(editingLR.id, values as Record<string, unknown>);
        message.success("更新成功");
      } else {
        await createLevelRule(values as Record<string, unknown>);
        message.success("创建成功");
      }
      setLrModalOpen(false);
      loadLevelRules();
    } catch { message.error("保存失败"); }
  };

  const handleDeleteLR = async (id: number) => {
    try { await deleteLevelRule(id); message.success("已删除"); loadLevelRules(); } catch { message.error("删除失败"); }
  };

  const handleAutoLevel = async () => {
    setAutoLevelLoading(true);
    try {
      const resp = await autoLevel();
      message.success(`自动分级完成，更新 ${resp.data.data.updated} 个客户`);
    } catch { message.error("自动分级失败"); }
    finally { setAutoLevelLoading(false); }
  };

  const handleChangePassword = async (values: { current_password: string; new_password: string }) => {
    setPasswordSaving(true);
    try {
      await changePassword(values.current_password, values.new_password);
      message.success("密码已更新");
      passwordForm.resetFields();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.response?.data?.msg || "修改密码失败");
    } finally {
      setPasswordSaving(false);
    }
  };

  // ---- Column definitions ----
  const arColumns = [
    { title: "名称", dataIndex: "name", width: 160 },
    { title: "规则类型", dataIndex: "rule_type", width: 120, render: (v: string) => RULE_TYPE_LABELS[v] || v },
    { title: "阈值天数", dataIndex: "threshold_days", width: 90 },
    { title: "阈值%", dataIndex: "threshold_pct", width: 80 },
    { title: "阈值金额", dataIndex: "threshold_amount", width: 90 },
    {
      title: "严重级别", dataIndex: "severity", width: 90,
      render: (v: string) => <Tag color={SEVERITY_COLORS[v]}>{v}</Tag>,
    },
    {
      title: "启用", dataIndex: "enabled", width: 60,
      render: (v: boolean, r: AlertRule) => (
        <Switch size="small" checked={v} onChange={async () => {
          try { await updateAlertRule(r.id, { enabled: !v }); loadAlertRules(); } catch { message.error("操作失败"); }
        }} />
      ),
    },
    {
      title: "操作", key: "actions", width: 120,
      render: (_: unknown, r: AlertRule) => (
        <Space>
          <Button size="small" onClick={() => openARForm(r)}>编辑</Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDeleteAR(r.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const aeColumns = [
    { title: "客户ID", dataIndex: "customer_id", width: 80 },
    { title: "规则名称", dataIndex: "rule_name", width: 120 },
    {
      title: "严重级别", dataIndex: "severity", width: 80,
      render: (v: string) => <Tag color={SEVERITY_COLORS[v]}>{v}</Tag>,
    },
    { title: "预警消息", dataIndex: "message", ellipsis: true },
    { title: "时间", dataIndex: "created_at", width: 160, render: (v: string) => v?.slice(0, 19) },
    {
      title: "状态", dataIndex: "is_read", width: 70,
      render: (v: boolean) => v ? <Tag color="default">已读</Tag> : <Badge status="processing" text="未读" />,
    },
    {
      title: "操作", key: "actions", width: 80,
      render: (_: unknown, r: AlertEvent) => (
        r.is_read ? null : <Button size="small" onClick={() => handleMarkRead(r.id)}>已读</Button>
      ),
    },
  ];

  const lrColumns = [
    { title: "名称", dataIndex: "name", width: 160 },
    {
      title: "目标等级", dataIndex: "target_level", width: 80,
      render: (v: string) => <Tag color={LEVEL_COLORS[v]}>{v}</Tag>,
    },
    { title: "条件", dataIndex: "condition_type", width: 100, render: (v: string) => CONDITION_LABELS[v] || v },
    { title: "运算符", dataIndex: "operator", width: 60, render: (v: string) => OPERATOR_LABELS[v] || v },
    { title: "阈值", dataIndex: "threshold_value", width: 80 },
    { title: "周期(天)", dataIndex: "period_days", width: 80 },
    { title: "优先级", dataIndex: "priority", width: 60 },
    {
      title: "启用", dataIndex: "enabled", width: 60,
      render: (v: boolean, r: LevelRule) => (
        <Switch size="small" checked={v} onChange={async () => {
          try { await updateLevelRule(r.id, { enabled: !v }); loadLevelRules(); } catch { message.error("操作失败"); }
        }} />
      ),
    },
    {
      title: "操作", key: "actions", width: 120,
      render: (_: unknown, r: LevelRule) => (
        <Space>
          <Button size="small" onClick={() => openLRForm(r)}>编辑</Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDeleteLR(r.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: "account", label: "账户信息",
      children: (
        <Space direction="vertical" size={16} style={{ width: "100%", maxWidth: 720 }}>
          <Card>
            <Descriptions title="账户信息" column={1}>
              <Descriptions.Item label="用户名">{username}</Descriptions.Item>
              <Descriptions.Item label="角色">管理员</Descriptions.Item>
              <Descriptions.Item label="AI 分析模型">Qwen/Qwen2.5-7B-Instruct (RFM/流失/建议)</Descriptions.Item>
              <Descriptions.Item label="AI 助手模型">Qwen/Qwen2.5-7B-Instruct (Chat)</Descriptions.Item>
              <Descriptions.Item label="嵌入模型">BAAI/bge-large-zh-v1.5</Descriptions.Item>
              <Descriptions.Item label="数据库">PostgreSQL 16 + pgvector</Descriptions.Item>
              <Descriptions.Item label="后端框架">FastAPI + SQLAlchemy 2.0</Descriptions.Item>
              <Descriptions.Item label="前端框架">React 19 + TypeScript + Ant Design</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="修改当前密码">
            <Form
              form={passwordForm}
              layout="vertical"
              onFinish={handleChangePassword}
              autoComplete="off"
              style={{ maxWidth: 420 }}
            >
              <Form.Item
                label="当前密码"
                name="current_password"
                rules={[{ required: true, message: "请输入当前密码" }]}
              >
                <Input.Password autoComplete="current-password" />
              </Form.Item>
              <Form.Item
                label="新密码"
                name="new_password"
                rules={[
                  { required: true, message: "请输入新密码" },
                  { min: 8, message: "新密码至少 8 位" },
                ]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <Form.Item
                label="确认新密码"
                name="confirm_password"
                dependencies={["new_password"]}
                rules={[
                  { required: true, message: "请再次输入新密码" },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue("new_password") === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error("两次输入的新密码不一致"));
                    },
                  }),
                ]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={passwordSaving}>
                更新密码
              </Button>
            </Form>
          </Card>
        </Space>
      ),
    },
    {
      key: "alert-rules", label: "预警规则",
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => openARForm()}>新建规则</Button>
          </Space>
          <Table rowKey="id" columns={arColumns} dataSource={alertRules} loading={arLoading}
            pagination={false} size="small" />
        </div>
      ),
    },
    {
      key: "alert-events", label: "预警事件",
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<ThunderboltOutlined />} loading={checkLoading} onClick={handleCheckAlerts}>
              执行预警检查
            </Button>
            <Select allowClear placeholder="读取状态" style={{ width: 110 }}
              value={aeReadFilter} onChange={(v) => { setAeReadFilter(v); setAePage(1); }}
              options={[{ value: false, label: "未读" }, { value: true, label: "已读" }]} />
            <Button onClick={handleMarkAllRead}>全部标记已读</Button>
          </Space>
          <Table rowKey="id" columns={aeColumns} dataSource={alertEvents} loading={aeLoading}
            pagination={{ current: aePage, total: aeTotal, pageSize: 20, onChange: (p) => setAePage(p), showTotal: (t) => `共 ${t} 条` }}
            size="small" />
        </div>
      ),
    },
    {
      key: "level-rules", label: "客户分级",
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => openLRForm()}>新建规则</Button>
            <Button icon={<ThunderboltOutlined />} loading={autoLevelLoading} onClick={handleAutoLevel}>
              执行自动分级
            </Button>
          </Space>
          <Table rowKey="id" columns={lrColumns} dataSource={levelRules} loading={lrLoading}
            pagination={false} size="small" />
        </div>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>系统设置</Title>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
    </div>
  );
}
