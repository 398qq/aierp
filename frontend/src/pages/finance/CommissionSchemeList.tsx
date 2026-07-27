/** CommissionSchemeList — 提成方案配置（013 PRD）

ERP Operational Screens 风格：
- `<PageHeader>`, `<SearchBar>`, `<StatusTag>`, `<EmptyState>`, `<ErrorBoundary>`
- `size="middle"` 表格，固定操作列
- Drawer 720px 方案编辑
- 阶梯配置实时校验
*/

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "@/router";
import {
  App as AntdApp,
  Button,
  Drawer,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Table,
  DatePicker,
  Switch,
  Tabs,
  Popconfirm,
  Tag,
  Tooltip,
} from "antd";
import { PlusOutlined, SettingOutlined, StopOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { StatusTag } from "../../ui";
import { erpPagination } from "../../ui/pagination";
import { PageHeader } from "@/ui/PageHeader";
import { SearchBar } from "@/ui/SearchBar";
import { EmptyState } from "@/ui/EmptyState";
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
  type SchemeTier,
  type SchemeStatus,
} from "@/api/finance";
import { numericStyle } from "@/design-tokens";

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
  const [data, setData] = useState<CommissionScheme[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [q, setQ] = useState("");
  const [tabKey, setTabKey] = useState<string>("active");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = async (p?: number, requestedPageSize = pageSize) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p ?? page, page_size: requestedPageSize, q: q || undefined };
      if (tabKey) params.status = tabKey;
      const resp = await getCommissionSchemes(params);
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch (e) {
      message.error(getApiErrorMessage(e, "加载失败"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(1);
  }, [tabKey]);

  const columns: ColumnsType<CommissionScheme> = [
    { title: "方案名称", dataIndex: "name", ellipsis: true, width: 200 },
    { title: "版本", dataIndex: "version_no", width: 60, align: "right" },
    {
      title: "状态",
      dataIndex: "status",
      width: 80,
      render: (s: string) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s] || s}</Tag>,
    },
    { title: "生效日", dataIndex: "effective_from", width: 100 },
    {
      title: "到期日",
      dataIndex: "effective_to",
      width: 100,
      render: (v: string | null) => v || "—",
    },
    { title: "默认", dataIndex: "is_default", width: 60, render: (v: boolean) => (v ? "✅" : "—") },
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
                  load();
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
                  load();
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
                  load();
                } catch (e) {
                  message.error(getApiErrorMessage(e));
                }
              }}
            >
              <a style={{ color: "#ef4444" }}>删除</a>
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
      load();
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
      <SearchBar
        placeholder="按方案名称搜索…"
        onSearch={(v) => {
          setQ(v);
          load(1);
        }}
        onReset={() => {
          setQ("");
          load(1);
        }}
      />
      <Tabs
        activeKey={tabKey}
        onChange={(k) => setTabKey(k)}
        items={TAB_KEYS.map((k) => ({ key: k, label: TAB_LABELS[k] }))}
      />
      <Table<CommissionScheme>
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        size="middle"
        scroll={{ x: 900 }}
        pagination={erpPagination({
          current: page,
          pageSize,
          total,
          onChange: (p, ps) => {
            const nextPage = ps !== pageSize ? 1 : p;
            setPage(nextPage);
            setPageSize(ps);
            load(nextPage, ps);
          },
        })}
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
