/**
 * CustomerListPage — 新版客户管理列表页
 * 排序: last_contacted_at ASC (最早互动在前)
 */

import React, { useCallback, useEffect, useState } from "react";
import { flushSync } from "react-dom";
import {
  Button,
  Dropdown,
  Empty,
  Form,
  Input,
  message,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  EyeOutlined,
  EllipsisOutlined,
  PhoneFilled,
  ThunderboltOutlined,
  ReloadOutlined,
  ExportOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import { createFollowUp, exportCustomers, getCustomers, getApiErrorMessage } from "@/api";
import type { Customer } from "@/types";
import { ErrorBoundary, StatusTag, useColumnResize } from "@/ui";
import CustomerModuleShell from "./CustomerModuleShell";
import { CustomerDetailPanel } from "./CustomerDetailPanel";
import { CustomerFormDrawer } from "./CustomerFormDrawer";
import { CustomerBatchBar } from "./CustomerBatchBar";
import CustomerQuickFollowUpDrawer from "./CustomerQuickFollowUpDrawer";
import { GROUP_OPTIONS, GROUP_FILTERS, STATUS_CONFIG, type GroupValue } from "./constants";

const { Text } = Typography;

const CREDIT_COLORS: Record<string, string> = {
  AAA: "green",
  AA: "cyan",
  A: "blue",
  B: "orange",
  C: "red",
  D: "red",
};

const LEVEL_COLORS: Record<string, string> = {
  A: "red",
  B: "gold",
  C: "blue",
  D: "default",
};

const TAX_STATUS = {
  complete: { label: "资料齐", color: "green" },
  missing: { label: "待补齐", color: "orange" },
};

const CUSTOMER_LEVELS = ["A", "B", "C", "D"];
const CUSTOMER_REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"];

function relativeTime(iso?: string | null): string {
  if (!iso) return "-";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (diff === 0) return "今天";
  if (diff === 1) return "昨天";
  if (diff < 30) return `${diff}天前`;
  if (diff < 365) return `${Math.floor(diff / 30)}月前`;
  return `${Math.floor(diff / 365)}年前`;
}

function formatMoney(value: number | null | undefined): string {
  if (value == null) return "-";
  return `¥${value.toLocaleString("zh-CN", { maximumFractionDigits: 0 })}`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  return value.slice(0, 10);
}

function isErpProfileComplete(customer: Customer): boolean {
  return Boolean(
    (customer.tax_id || customer.unified_social_credit_code) &&
    customer.invoice_title &&
    customer.invoice_address &&
    customer.payment_terms,
  );
}

function isStaleContact(iso?: string | null): boolean {
  if (!iso) return true;
  return Date.now() - new Date(iso).getTime() > 30 * 86400000;
}

function getSummary(data: Customer[]) {
  const active = data.filter((item) =>
    ["active", "vip", "converted"].includes(item.status || ""),
  ).length;
  const missingErp = data.filter((item) => !isErpProfileComplete(item)).length;
  const highValue = data.filter((item) => (item.total_amount || 0) > 0).length;
  const stale = data.filter((item) => isStaleContact(item.last_contacted_at)).length;
  const pageAmount = data.reduce((sum, item) => sum + (item.total_amount || 0), 0);
  return { active, missingErp, highValue, stale, pageAmount };
}

interface CustomerColumnActions {
  onCreateOpportunity: (customer: Customer) => void;
  onFollowUp: (customer: Customer) => void;
  onEdit: (customer: Customer) => void;
  onViewDetail: (customer: Customer) => void;
  onOpenPanel: (customer: Customer) => void;
}

function buildColumns(actions: CustomerColumnActions): ColumnsType<Customer> {
  return [
    {
      title: "客户",
      dataIndex: "name",
      width: 250,
      fixed: "left",
      render: (name: string, record) => (
        <Space direction="vertical" size={0}>
          <a onClick={(e) => { e.stopPropagation(); actions.onOpenPanel(record); }}>
            {name}
          </a>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.code || "-"} {record.short_name ? `· ${record.short_name}` : ""}
          </Text>
        </Space>
      ),
    },
    {
      title: "负责人",
      dataIndex: "owner",
      width: 110,
      render: (v: string | null) => v || <Text type="secondary">未分配</Text>,
    },
    {
      title: "生命周期",
      dataIndex: "status",
      width: 110,
      render: (s: string) => {
        const c = STATUS_CONFIG[s] || { label: s || "-", color: "default" };
        return <StatusTag tone={c.color as "green" | "blue" | "gold"}>{c.label}</StatusTag>;
      },
    },
    {
      title: "等级",
      dataIndex: "level",
      width: 80,
      render: (level: string | null) =>
        level ? <Tag color={LEVEL_COLORS[level] || "default"}>{level}</Tag> : "-",
    },
    {
      title: "行业/区域",
      dataIndex: "industry",
      width: 150,
      render: (_: string | null, record) => (
        <Space direction="vertical" size={0}>
          <Text>{record.industry || "-"}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.region || "-"}
          </Text>
        </Space>
      ),
    },
    {
      title: "主联系人",
      dataIndex: "contact_person",
      width: 170,
      render: (_: string | null, record) => (
        <Space direction="vertical" size={0}>
          <Text>{record.contact_person || "-"}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.phone || record.email || "-"}
          </Text>
        </Space>
      ),
    },
    {
      title: "交易额",
      dataIndex: "total_amount",
      width: 120,
      align: "right",
      sorter: false,
      render: (v: number | null) => (
        <Text style={{ fontVariantNumeric: "tabular-nums" }}>{formatMoney(v)}</Text>
      ),
    },
    {
      title: "信用/账期",
      dataIndex: "credit_level",
      width: 140,
      render: (level: string | null, record) => (
        <Space direction="vertical" size={0}>
          {level ? (
            <Tag color={CREDIT_COLORS[level] || "default"}>{level}</Tag>
          ) : (
            <Text type="secondary">无评级</Text>
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.payment_terms || "未设账期"}
          </Text>
        </Space>
      ),
    },
    {
      title: "开票资料",
      dataIndex: "tax_id",
      width: 120,
      render: (_: string | null, record) => {
        const complete = isErpProfileComplete(record);
        const tax = complete ? TAX_STATUS.complete : TAX_STATUS.missing;
        return (
          <Tooltip
            title={
              complete
                ? "税号、抬头、地址、账期已维护"
                : "税号/统一社会信用代码、发票抬头、发票地址或账期缺失"
            }
          >
            <Tag color={tax.color}>{tax.label}</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: "最近联系",
      dataIndex: "last_contacted_at",
      width: 125,
      render: (d: string | null) => (
        <Space direction="vertical" size={0}>
          <Text>{relativeTime(d)}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {formatDate(d)}
          </Text>
        </Space>
      ),
    },
    {
      title: "操作",
      key: "actions",
      width: 56,
      align: "center",
      fixed: "right",
      render: (_: unknown, r) => (
        <div onClick={(event) => event.stopPropagation()}>
          <Dropdown
            trigger={["click"]}
            placement="bottomRight"
            menu={{
              items: [
                { key: "detail", icon: <EyeOutlined />, label: "客户详情" },
                { key: "opportunity", icon: <ThunderboltOutlined />, label: "新增机会" },
                { key: "follow-up", icon: <PhoneFilled />, label: "新增跟进" },
                { type: "divider" },
                { key: "edit", icon: <EditOutlined />, label: "编辑客户" },
              ],
              onClick: ({ key, domEvent }) => {
                domEvent.stopPropagation();
                if (key === "detail") actions.onViewDetail(r);
                if (key === "opportunity") actions.onCreateOpportunity(r);
                if (key === "follow-up") actions.onFollowUp(r);
                if (key === "edit") actions.onEdit(r);
              },
            }}
          >
            <Button
              type="text"
              size="small"
              icon={<EllipsisOutlined />}
              aria-label={`操作客户 ${r.name}`}
              title="更多操作"
            />
          </Dropdown>
        </div>
      ),
    },
  ];
}

export default function CustomerListPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [followUpCustomer, setFollowUpCustomer] = useState<Customer | null>(null);
  const [followUpSaving, setFollowUpSaving] = useState(false);
  const [followUpForm] = Form.useForm();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [group, setGroup] = useState<GroupValue>("all");
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [levelFilter, setLevelFilter] = useState<string | undefined>();
  const [regionFilter, setRegionFilter] = useState<string | undefined>();
  const [missingErp, setMissingErp] = useState(false);

  const buildListParams = useCallback(() => {
    const params: Record<string, unknown> = {
      page,
      page_size: 50,
      q: debouncedSearch || undefined,
      sort_by: "last_contacted_at",
      sort_order: "asc",
    };
    if (group !== "all") {
      const gf = GROUP_FILTERS[group];
      if (gf.status) params.status = gf.status.join(",");
      if (gf.owner === null) params.owner = "null";
    }
    if (statusFilter) params.status = statusFilter;
    if (levelFilter) params.level = levelFilter;
    if (regionFilter) params.region = regionFilter;
    if (missingErp) params.missing_erp = true;
    return params;
  }, [page, debouncedSearch, group, statusFilter, levelFilter, regionFilter, missingErp]);

  // 搜索防抖 300ms
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  // 加载数据
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = buildListParams();
      const res = await getCustomers(params);
      const payload = res.data?.data as { list?: Customer[]; total?: number } | undefined;
      setData(payload?.list || []);
      setTotal(payload?.total || 0);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载客户失败"));
    } finally {
      setLoading(false);
    }
  }, [buildListParams]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const baseColumns = buildColumns({
    onViewDetail: (customer) => {
      navigate(`/customers/${customer.id}`);
    },
    onOpenPanel: (customer) => {
      setSelectedCustomer(customer);
      setDetailOpen(true);
    },
    onCreateOpportunity: (customer) =>
      navigate(`/sales/opportunities/new?customer_id=${customer.id}`),
    onFollowUp: (customer) => {
      setFollowUpCustomer(customer);
      followUpForm.resetFields();
      followUpForm.setFieldsValue({
        method: "phone",
        status: "planned",
        priority: "medium",
        assigned_to: customer.owner || undefined,
      });
    },
    onEdit: (customer) => {
      setEditingCustomer(customer);
      setFormOpen(true);
    },
  });
  const columns = useColumnResize(baseColumns);
  const summary = getSummary(data);
  const clearFilters = () => {
    setSearch("");
    setDebouncedSearch("");
    setGroup("all");
    setStatusFilter(undefined);
    setLevelFilter(undefined);
    setRegionFilter(undefined);
    setMissingErp(false);
    setPage(1);
  };
  const handleExport = async () => {
    try {
      const params = buildListParams();
      delete params.page;
      delete params.page_size;
      const response = await exportCustomers(params);
      const blob = response.data instanceof Blob ? response.data : new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `customers-${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "导出客户失败"));
    }
  };
  const closeQuickFollowUp = () => {
    setFollowUpCustomer(null);
    followUpForm.resetFields();
  };
  const submitQuickFollowUp = async () => {
    if (!followUpCustomer) return;
    try {
      const values = await followUpForm.validateFields();
      if (values.status === "planned" && !values.planned_at) {
        message.warning("计划中的跟进必须填写计划时间");
        return;
      }
      setFollowUpSaving(true);
      const submitData = {
        ...values,
        planned_at: values.planned_at
          ? (values.planned_at as dayjs.Dayjs).format("YYYY-MM-DD HH:mm:ss")
          : null,
        completed_at: values.completed_at
          ? (values.completed_at as dayjs.Dayjs).format("YYYY-MM-DD HH:mm:ss")
          : values.status === "completed"
            ? dayjs().format("YYYY-MM-DD HH:mm:ss")
            : null,
      };
      await createFollowUp(followUpCustomer.id, submitData);
      message.success("跟进记录已新增");
      flushSync(() => setFollowUpSaving(false));
      closeQuickFollowUp();
      fetchData();
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return;
      message.error(getApiErrorMessage(e, "保存跟进失败"));
    } finally {
      setFollowUpSaving(false);
    }
  };
  const activeFilters = [
    group !== "all"
      ? {
          key: "group",
          label: `分组: ${GROUP_OPTIONS.find((item) => item.value === group)?.label || group}`,
          clear: () => setGroup("all"),
        }
      : null,
    statusFilter
      ? {
          key: "status",
          label: `生命周期: ${STATUS_CONFIG[statusFilter]?.label || statusFilter}`,
          clear: () => setStatusFilter(undefined),
        }
      : null,
    levelFilter
      ? { key: "level", label: `等级: ${levelFilter}`, clear: () => setLevelFilter(undefined) }
      : null,
    regionFilter
      ? { key: "region", label: `区域: ${regionFilter}`, clear: () => setRegionFilter(undefined) }
      : null,
    missingErp
      ? { key: "missingErp", label: "待补ERP资料", clear: () => setMissingErp(false) }
      : null,
    search
      ? {
          key: "search",
          label: `搜索: ${search}`,
          clear: () => {
            setSearch("");
            setDebouncedSearch("");
          },
        }
      : null,
  ].filter(Boolean) as Array<{ key: string; label: string; clear: () => void }>;

  return (
    <ErrorBoundary>
      <CustomerModuleShell title="客户" subtitle="客户主数据、跟进状态与开票资料">
        <div className="customer-ledger">
          <div className="customer-ledger-command">
            <div className="customer-ledger-switch">
              <Segmented
                options={GROUP_OPTIONS.map((g) => ({ label: g.label, value: g.value }))}
                value={group}
                onChange={(v) => {
                  setGroup(v as GroupValue);
                  setPage(1);
                }}
              />
              <Button
                type={missingErp ? "primary" : "default"}
                icon={<FileTextOutlined />}
                onClick={() => {
                  setMissingErp((v) => !v);
                  setPage(1);
                }}
              >
                待补ERP资料
              </Button>
            </div>
            <Space wrap size={8}>
              <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
                刷新
              </Button>
              <Button icon={<ExportOutlined />} onClick={handleExport}>
                导出
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingCustomer(null);
                  setFormOpen(true);
                }}
              >
                新增客户
              </Button>
            </Space>
          </div>

          <div className="customer-ledger-filters">
            <Space wrap size={8}>
              <Input
                placeholder="客户名称、编码、联系人、电话、税号"
                prefix={<SearchOutlined />}
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                style={{ width: 320 }}
                allowClear
              />
              <Select
                allowClear
                placeholder="生命周期"
                style={{ width: 130 }}
                value={statusFilter}
                onChange={(v) => {
                  setStatusFilter(v);
                  setPage(1);
                }}
                options={Object.entries(STATUS_CONFIG).map(([k, v]) => ({
                  value: k,
                  label: v.label,
                }))}
              />
              <Select
                allowClear
                placeholder="客户等级"
                style={{ width: 110 }}
                value={levelFilter}
                onChange={(v) => {
                  setLevelFilter(v);
                  setPage(1);
                }}
                options={CUSTOMER_LEVELS.map((value) => ({ value, label: value }))}
              />
              <Select
                allowClear
                placeholder="区域"
                style={{ width: 120 }}
                value={regionFilter}
                onChange={(v) => {
                  setRegionFilter(v);
                  setPage(1);
                }}
                options={CUSTOMER_REGIONS.map((value) => ({ value, label: value }))}
              />
              <Button onClick={clearFilters}>重置</Button>
            </Space>
          </div>

          <div className="customer-filter-state">
            <Text type="secondary">筛选状态</Text>
            {activeFilters.length ? (
              activeFilters.map((item) => (
                <Tag key={item.key} closable onClose={item.clear}>
                  {item.label}
                </Tag>
              ))
            ) : (
              <Text type="secondary">全部客户</Text>
            )}
          </div>

          <div className="customer-ledger-metrics">
            <div className="customer-ledger-metric">
              <span>当前结果</span>
              <strong>{total.toLocaleString("zh-CN")}</strong>
              <em>家</em>
            </div>
            <div className="customer-ledger-metric">
              <span>本页交易额</span>
              <strong>{formatMoney(summary.pageAmount)}</strong>
            </div>
            <div className="customer-ledger-metric">
              <span>成交/活跃</span>
              <strong>{summary.active}</strong>
              <em>家</em>
            </div>
            <div className="customer-ledger-metric is-warning">
              <span>30天未联系</span>
              <strong>{summary.stale}</strong>
              <em>家</em>
            </div>
            <div className="customer-ledger-metric is-danger">
              <span>资料待补</span>
              <strong>{summary.missingErp}</strong>
              <em>家</em>
            </div>
          </div>

          {/* 批量操作栏 */}
          <CustomerBatchBar
            selectedIds={selectedRowKeys as number[]}
            selectedCount={selectedRowKeys.length}
            onClear={() => setSelectedRowKeys([])}
            onBatchComplete={fetchData}
          />

          <div className="customer-table-frame">
            <div className="customer-table-titlebar">
              <div>
                <Text strong>客户主数据台账</Text>
                <Text type="secondary"> 最近未联系优先，点击行查看客户 360</Text>
              </div>
              <Text type="secondary">
                已选 {selectedRowKeys.length} / 本页 {data.length}
              </Text>
            </div>

            {/* 表格 */}
            <Table<Customer>
              className="erp-table customer-ledger-table"
              rowKey="id"
              columns={columns}
              dataSource={data}
              loading={loading}
              size="small"
              bordered
              sticky
              tableLayout="fixed"
              scroll={{ x: 1480 }}
              rowClassName={(record) =>
                [
                  !isErpProfileComplete(record) ? "customer-row-missing-profile" : "",
                  isStaleContact(record.last_contacted_at) ? "customer-row-stale" : "",
                ]
                  .filter(Boolean)
                  .join(" ")
              }
              rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
              locale={{
                emptyText: (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description={activeFilters.length ? "没有符合筛选条件的客户" : "暂无客户"}
                  />
                ),
              }}
              pagination={{
                current: page,
                pageSize: 50,
                total,
                showSizeChanger: false,
                showTotal: (t, range) => `${range[0]}-${range[1]} / ${t}`,
                onChange: (p) => setPage(p),
              }}
              onRow={(r) => ({
                onClick: () => {
                  setSelectedCustomer(r);
                  setDetailOpen(true);
                },
                style: { cursor: "pointer" },
              })}
            />
          </div>
        </div>

        {/* 详情面板 */}
        {selectedCustomer && (
          <CustomerDetailPanel
            customerId={selectedCustomer.id as number}
            customerName={(selectedCustomer.name as string) || ""}
            customer={selectedCustomer as unknown as Record<string, unknown>}
            open={detailOpen}
            onClose={() => {
              setDetailOpen(false);
              setSelectedCustomer(null);
            }}
            onEdit={() => {
              setDetailOpen(false);
              setEditingCustomer(selectedCustomer);
              setFormOpen(true);
            }}
          />
        )}

        {/* 新建表单 */}
        <CustomerFormDrawer
          open={formOpen}
          customerId={editingCustomer?.id}
          initialValues={editingCustomer as unknown as Record<string, unknown> | undefined}
          onClose={() => {
            setFormOpen(false);
            setEditingCustomer(null);
          }}
          onSuccess={fetchData}
        />
        <CustomerQuickFollowUpDrawer
          open={Boolean(followUpCustomer)}
          saving={followUpSaving}
          customer={followUpCustomer}
          form={followUpForm}
          onClose={closeQuickFollowUp}
          onSubmit={submitQuickFollowUp}
        />
      </CustomerModuleShell>
    </ErrorBoundary>
  );
}
