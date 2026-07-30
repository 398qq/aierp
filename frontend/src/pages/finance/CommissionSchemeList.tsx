/** CommissionSchemeList — 提成方案配置（013 PRD）

ERP Operational Screens 风格：
- `<PageHeader>`, `<SearchBar>`, `<StatusTag>`, `<ErrorBoundary>`
- ProTable（size="middle"），固定操作列
- Drawer 720px 方案编辑
- 阶梯配置实时校验
*/

import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  App as AntdApp,
  Button,
  Drawer,
  Form,
  Input,
  InputNumber,
  Space,
  DatePicker,
  Switch,
  Tabs,
  Popconfirm,
  Tag,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType, ProColumns } from "@ant-design/pro-components";
import dayjs from "dayjs";
import { PageHeader } from "@/ui/PageHeader";
import { SearchBar } from "@/ui/SearchBar";
import { ErrorBoundary } from "@/ui/ErrorBoundary";
import { getApiErrorMessage } from "@/api";
import {
  getCommissionSchemes,
  createCommissionScheme,
  updateCommissionScheme,
  deleteCommissionScheme,
  activateCommissionScheme,
  deactivateCommissionScheme,
  type CommissionScheme,
} from "@/api/finance";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  pending: "待生效",
  active: "生效中",
  expired: "已过期",
  inactive: "已停用",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "default",
  pending: "processing",
  active: "success",
  expired: "default",
  inactive: "warning",
};

const TAB_KEYS = ["active", "pending", "expired", ""] as const;
const TAB_LABELS: Record<string, string> = {
  active: "生效中",
  pending: "待生效",
  expired: "已过期",
  "": "全部",
};

function SchemeList() {
  const { message } = AntdApp.useApp();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [tabKey, setTabKey] = useState<string>("active");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const actionRef = useRef<ActionType>(null);

  const reload = () => actionRef.current?.reload();

  const columns: ProColumns<CommissionScheme>[] = [
    { title: "方案名称", dataIndex: "name", ellipsis: true, width: 200 },
    { title: "版本", dataIndex: "version_no", width: 60, align: "right" },
    {
      title: "状态",
      dataIndex: "status",
      width: 80,
      render: (_, r) => (
        <Tag color={STATUS_COLORS[r.status]}>{STATUS_LABELS[r.status] || r.status}</Tag>
      ),
    },
    { title: "生效日", dataIndex: "effective_from", width: 100 },
    {
      title: "到期日",
      dataIndex: "effective_to",
      width: 100,
      render: (_, r) => r.effective_to || "—",
    },
    {
      title: "默认",
      dataIndex: "is_default",
      width: 60,
      render: (_, r) => (r.is_default ? "✅" : "—"),
    },
    {
      title: "操作",
      width: 220,
      fixed: "right",
      render: (_, r) => (
        <Space size="small">
          <a onClick={() => navigate(`/finance/commission-schemes/${r.id}`)}>详情</a>
          {r.status === "draft" && (
            <a
              onClick={() => {
                setEditId(r.id);
                form.setFieldsValue(r);
                setDrawerOpen(true);
              }}
            >
              编辑
            </a>
          )}
          {r.status === "draft" && (
            <Popconfirm
              title="激活此方案？"
              onConfirm={async () => {
                try {
                  await activateCommissionScheme(r.id);
                  message.success("已激活");
                  reload();
                } catch (e) {
                  message.error(getApiErrorMessage(e));
                }
              }}
            >
              <a>激活</a>
            </Popconfirm>
          )}
          {r.status === "active" && (
            <Popconfirm
              title="停用此方案？"
              onConfirm={async () => {
                try {
                  await deactivateCommissionScheme(r.id);
                  message.success("已停用");
                  reload();
                } catch (e) {
                  message.error(getApiErrorMessage(e));
                }
              }}
            >
              <a>停用</a>
            </Popconfirm>
          )}
          {(r.status === "draft" || r.status === "inactive") && (
            <Popconfirm
              title="删除此方案？"
              onConfirm={async () => {
                try {
                  await deleteCommissionScheme(r.id);
                  message.success("已删除");
                  reload();
                } catch (e) {
                  message.error(getApiErrorMessage(e));
                }
              }}
            >
              <Button type="link" danger size="small" style={{ padding: 0 }}>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = {
        ...values,
        effective_from: values.effective_from?.format("YYYY-MM-DD"),
        effective_to: values.effective_to?.format("YYYY-MM-DD"),
        tiers: (values.tiers || []).map((t: Record<string, unknown>, i: number) => ({
          tier_no: i + 1,
          metric_type: "monthly_sales",
          low_amount:
            i === 0 ? 0 : ((values.tiers?.[i - 1] as Record<string, unknown>)?.high_amount ?? 0),
          high_amount: t.high_amount ?? null,
          rate: (t.rate as number) / 100,
          cap_amount: t.cap_amount ?? 0,
          floor_amount: t.floor_amount ?? 0,
          product_category: null,
          customer_level: null,
        })),
      };
      if (editId) {
        await updateCommissionScheme(editId, payload);
        message.success("方案已更新");
      } else {
        await createCommissionScheme(payload);
        message.success("方案已创建");
      }
      setDrawerOpen(false);
      reload();
    } catch (e) {
      message.error(getApiErrorMessage(e, "保存失败"));
    } finally {
      setSaving(false);
    }
  };

  const openCreate = () => {
    setEditId(null);
    form.resetFields();
    form.setFieldsValue({
      effective_from: dayjs(),
      tiers: [{ rate: 3, cap_amount: 0, floor_amount: 0, high_amount: null }],
    });
    setDrawerOpen(true);
  };

  return (
    <ErrorBoundary>
      <PageHeader
        title="提成方案配置"
        description="管理销售提成计算规则——阶梯、封顶、保底、产品线差异"
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建方案
          </Button>
        }
      />
      <SearchBar placeholder="按方案名称搜索…" onSearch={(v) => setQ(v)} onReset={() => setQ("")} />
      <Tabs
        activeKey={tabKey}
        onChange={(k) => setTabKey(k)}
        items={TAB_KEYS.map((k) => ({ key: k, label: TAB_LABELS[k] }))}
      />
      <ProTable<CommissionScheme>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        options={{ reload: true, density: true, setting: true }}
        size="middle"
        scroll={{ x: 900 }}
        params={{ status: tabKey || undefined, q: q || undefined }}
        request={async (params) => {
          try {
            const apiParams: Record<string, unknown> = {
              page: params.current,
              page_size: params.pageSize,
            };
            if (tabKey) apiParams.status = tabKey;
            if (q) apiParams.q = q;
            const resp = await getCommissionSchemes(apiParams);
            return {
              data: resp.data.data.list,
              success: true,
              total: resp.data.data.total,
            };
          } catch (e) {
            message.error(getApiErrorMessage(e, "加载失败"));
            return { data: [], success: false, total: 0 };
          }
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100],
          showQuickJumper: true,
          showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条 / 共 ${total} 条`,
        }}
      />
      <Drawer
        title={editId ? "编辑方案" : "新建方案"}
        width={720}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" loading={saving} onClick={handleSave}>
              保存
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="方案名称"
            rules={[{ required: true, message: "请输入方案名称" }]}
          >
            <Input placeholder="例：2026-Q3 标准提成方案" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="方案说明（可选）" />
          </Form.Item>
          <Space style={{ width: "100%" }} size={16}>
            <Form.Item name="effective_from" label="生效日期" rules={[{ required: true }]}>
              <DatePicker />
            </Form.Item>
            <Form.Item name="effective_to" label="到期日期">
              <DatePicker />
            </Form.Item>
            <Form.Item name="is_default" label="默认方案" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>

          <Form.List name="tiers">
            {(fields, { add, remove }) => (
              <>
                <div style={{ fontWeight: 600, marginBottom: 8 }}>阶梯配置</div>
                {fields.map(({ key, name, ...rest }) => (
                  <Space key={key} style={{ display: "flex", marginBottom: 8 }} align="baseline">
                    <span style={{ minWidth: 20 }}>{name + 1}.</span>
                    <Form.Item {...rest} name={[name, "rate"]} rules={[{ required: true }]}>
                      <InputNumber min={0} max={100} addonAfter="%" style={{ width: 80 }} />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, "high_amount"]}>
                      <InputNumber
                        min={0}
                        addonBefore="上限¥"
                        style={{ width: 140 }}
                        placeholder="∞ 无上限"
                      />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, "cap_amount"]}>
                      <InputNumber min={0} addonBefore="封顶¥" style={{ width: 130 }} />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, "floor_amount"]}>
                      <InputNumber min={0} addonBefore="保底¥" style={{ width: 130 }} />
                    </Form.Item>
                    {fields.length > 1 && <a onClick={() => remove(name)}>×</a>}
                  </Space>
                ))}
                <Button
                  type="dashed"
                  onClick={() =>
                    add({ rate: 3, cap_amount: 0, floor_amount: 0, high_amount: null })
                  }
                  block
                >
                  + 添加阶梯
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Drawer>
    </ErrorBoundary>
  );
}

export default function CommissionSchemeListPage() {
  return (
    <ErrorBoundary>
      <SchemeList />
    </ErrorBoundary>
  );
}
