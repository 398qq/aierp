import { useCallback, useEffect, useRef, useState } from "react";

import {
  App,
  Button,
  Dropdown,
  Form,
  Input,
  Segmented,
  Select,
  Space,
  Tag,
  Typography,
  Grid,
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
  MergeCellsOutlined,
} from "@ant-design/icons";
import type { ProColumns, ActionType } from "@ant-design/pro-components";
import { ProForm, ProTable } from "@ant-design/pro-components";
import { useNavigate, useSearchParams } from "react-router-dom";
import dayjs from "dayjs";
import {
  createFollowUp,
  detectDuplicates,
  exportCustomers,
  getApiErrorMessage,
  mergeCustomers,
} from "@/api";
import type { Customer, DuplicatePair, PageData } from "@/types";
import { useApiQuery } from "@/lib/queries";
import { ErrorBoundary, StatusTag } from "@/ui";
import CustomerModuleShell from "./CustomerModuleShell";
import { CustomerDetailPanel } from "./CustomerDetailPanel";
import { CustomerFormDrawer } from "./CustomerFormDrawer";
import { CustomerBatchBar } from "./CustomerBatchBar";
import CustomerQuickFollowUpDrawer from "./CustomerQuickFollowUpDrawer";
import { CustomerDuplicateListModal, CustomerMergeModal } from "./CustomerDuplicateModals";
import {
  CREDIT_COLORS,
  GROUP_OPTIONS,
  GROUP_FILTERS,
  STATUS_CONFIG,
  type GroupValue,
} from "./constants";

const { Text } = Typography;

const LEVEL_COLORS: Record<string, string> = { A: "red", B: "gold", C: "blue", D: "default" };

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

export default function CustomerListPage() {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>(null);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const [search, setSearch] = useState(() => searchParams.get("q") || "");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [followUpCustomer, setFollowUpCustomer] = useState<Customer | null>(null);
  const [followUpSaving, setFollowUpSaving] = useState(false);
  const [followUpForm] = ProForm.useForm();
  const [duplicateLoading, setDuplicateLoading] = useState(false);
  const [duplicateOpen, setDuplicateOpen] = useState(false);
  const [duplicatePairs, setDuplicatePairs] = useState<DuplicatePair[]>([]);
  const [mergePair, setMergePair] = useState<DuplicatePair | null>(null);
  const [mergeLoading, setMergeLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const customersQuery = useApiQuery<PageData<Customer>>(
    ["customers", { ...Object.fromEntries(searchParams), debouncedSearch, page, pageSize }],
    "/api/v1/customers",
    {
      ...Object.fromEntries(searchParams),
      q: debouncedSearch || undefined,
      page,
      page_size: pageSize,
    },
    { staleTime: 30 * 1000, keepPreviousData: true },
  );
  const [group, setGroup] = useState<GroupValue>(
    () => (searchParams.get("group") as GroupValue) || "all",
  );
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    () => searchParams.get("status") || undefined,
  );
  const [levelFilter, setLevelFilter] = useState<string | undefined>(
    () => searchParams.get("level") || undefined,
  );
  const [regionFilter, setRegionFilter] = useState<string | undefined>(
    () => searchParams.get("region") || undefined,
  );
  const [missingErp, setMissingErp] = useState(() => searchParams.get("missing_erp") === "1");
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const buildRequestParams = useCallback(() => {
    const params: Record<string, unknown> = { sort_by: "operational_priority", sort_order: "desc" };
    if (debouncedSearch) params.q = debouncedSearch;
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
  }, [debouncedSearch, group, statusFilter, levelFilter, regionFilter, missingErp]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set("q", search);
    if (group !== "all") params.set("group", group);
    if (statusFilter) params.set("status", statusFilter);
    if (levelFilter) params.set("level", levelFilter);
    if (regionFilter) params.set("region", regionFilter);
    if (missingErp) params.set("missing_erp", "1");
    setSearchParams(params, { replace: true });
    setPage(1);
  }, [search, group, statusFilter, levelFilter, regionFilter, missingErp, setSearchParams]);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const reload = useCallback(() => {
    actionRef.current?.reload();
  }, []);

  const columns: ProColumns<Customer>[] = [
    {
      title: "客户",
      dataIndex: "name",
      width: 235,
      fixed: "left",
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <a
            onClick={(e) => {
              e.stopPropagation();
              setSelectedCustomer(r);
              setDetailOpen(true);
            }}
          >
            {r.name}
          </a>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {r.code || "-"} · {r.owner || "未分配"}
          </Text>
        </Space>
      ),
    },
    {
      title: "状态/等级",
      dataIndex: "status",
      width: 125,
      responsive: ["md" as const],
      render: (_, r) => {
        const c = STATUS_CONFIG[r.status || ""] || { label: r.status || "-", color: "default" };
        return (
          <Space size={4} wrap>
            <StatusTag tone={c.color as "green" | "blue" | "gold"}>{c.label}</StatusTag>
            {r.level && <Tag color={LEVEL_COLORS[r.level] || "default"}>{r.level}</Tag>}
          </Space>
        );
      },
    },
    {
      title: "行业/区域",
      dataIndex: "industry",
      width: 150,
      responsive: ["lg" as const],
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <Text>{r.industry || "-"}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {r.region || "-"}
          </Text>
        </Space>
      ),
    },
    {
      title: "主联系人",
      dataIndex: "contact_person",
      width: 160,
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <Text>{r.contact_person || "-"}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {r.phone || r.email || "-"}
          </Text>
        </Space>
      ),
    },
    {
      title: "交易额",
      dataIndex: "total_amount",
      width: 120,
      align: "right",
      responsive: ["lg" as const],
      render: (_, r) => (
        <Text style={{ fontVariantNumeric: "tabular-nums" }}>{formatMoney(r.total_amount)}</Text>
      ),
    },
    {
      title: "信用/账期",
      dataIndex: "credit_level",
      width: 140,
      responsive: ["xl" as const],
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          {r.credit_level ? (
            <Tag color={CREDIT_COLORS[r.credit_level] || "default"}>{r.credit_level}</Tag>
          ) : (
            <Text type="secondary">无评级</Text>
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            {r.payment_terms || "未设账期"}
          </Text>
        </Space>
      ),
    },
    {
      title: "最近联系",
      dataIndex: "last_contacted_at",
      width: 125,
      responsive: ["md" as const],
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <Text>{relativeTime(r.last_contacted_at)}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {formatDate(r.last_contacted_at)}
          </Text>
        </Space>
      ),
    },
    {
      title: "操作",
      key: "actions",
      width: 178,
      fixed: "right",
      render: (_, r) => (
        <Space size={4} onClick={(e) => e.stopPropagation()}>
          <Button
            size="small"
            type="link"
            icon={<PhoneFilled />}
            onClick={() => {
              setFollowUpCustomer(r);
              followUpForm.resetFields();
              followUpForm.setFieldsValue({
                method: "phone",
                status: "planned",
                priority: "medium",
                assigned_to: r.owner || undefined,
              });
            }}
          >
            跟进
          </Button>
          <Button
            size="small"
            type="link"
            icon={<ThunderboltOutlined />}
            onClick={() => navigate(`/sales/opportunities/new?customer_id=${r.id}`)}
          >
            机会
          </Button>
          <Dropdown
            trigger={["click"]}
            placement="bottomRight"
            menu={{
              items: [
                { key: "detail", icon: <EyeOutlined />, label: "客户详情" },
                { key: "edit", icon: <EditOutlined />, label: "编辑客户" },
              ],
              onClick: ({ key, domEvent }) => {
                domEvent.stopPropagation();
                if (key === "detail") navigate(`/customers/${r.id}`);
                if (key === "edit") {
                  setEditingCustomer(r);
                  setFormOpen(true);
                }
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
        </Space>
      ),
    },
  ];

  const activeFilters = [
    group !== "all"
      ? {
          key: "group",
          label: `分组: ${GROUP_OPTIONS.find((g) => g.value === group)?.label || group}`,
          clear: () => {
            setGroup("all");
          },
        }
      : null,
    statusFilter
      ? {
          key: "status",
          label: `生命周期: ${STATUS_CONFIG[statusFilter]?.label || statusFilter}`,
          clear: () => {
            setStatusFilter(undefined);
          },
        }
      : null,
    levelFilter
      ? {
          key: "level",
          label: `等级: ${levelFilter}`,
          clear: () => {
            setLevelFilter(undefined);
          },
        }
      : null,
    regionFilter
      ? {
          key: "region",
          label: `区域: ${regionFilter}`,
          clear: () => {
            setRegionFilter(undefined);
          },
        }
      : null,
    missingErp
      ? {
          key: "missingErp",
          label: "待补ERP资料",
          clear: () => {
            setMissingErp(false);
          },
        }
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

  const handleExport = async () => {
    try {
      const params = buildRequestParams();
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

  const loadDuplicates = async () => {
    setDuplicateLoading(true);
    try {
      const response = await detectDuplicates();
      const pairs = response.data.data?.pairs || [];
      setDuplicatePairs(pairs);
      setDuplicateOpen(true);
      if (pairs.length === 0) message.success("未发现疑似重复客户");
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "客户查重失败"));
    } finally {
      setDuplicateLoading(false);
    }
  };

  const confirmMerge = async () => {
    if (!mergePair) return;
    setMergeLoading(true);
    try {
      await mergeCustomers(mergePair.customer_a.id, mergePair.customer_b.id);
      message.success(`已将"${mergePair.customer_a.name}"合并到"${mergePair.customer_b.name}"`);
      setMergePair(null);
      await Promise.all([reload(), loadDuplicates()]);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "客户合并失败"));
    } finally {
      setMergeLoading(false);
    }
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
      await createFollowUp(followUpCustomer.id, {
        ...values,
        planned_at: values.planned_at
          ? (values.planned_at as dayjs.Dayjs).format("YYYY-MM-DD HH:mm:ss")
          : null,
        completed_at: values.completed_at
          ? (values.completed_at as dayjs.Dayjs).format("YYYY-MM-DD HH:mm:ss")
          : values.status === "completed"
            ? dayjs().format("YYYY-MM-DD HH:mm:ss")
            : null,
      });
      message.success("跟进记录已新增");
      setFollowUpSaving(false);
      setFollowUpCustomer(null);
      followUpForm.resetFields();
      reload();
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return;
      message.error(getApiErrorMessage(e, "保存跟进失败"));
    } finally {
      setFollowUpSaving(false);
    }
  };

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
                }}
              />
              <Button
                type={missingErp ? "primary" : "default"}
                icon={<FileTextOutlined />}
                onClick={() => setMissingErp((v) => !v)}
              >
                待补ERP资料
              </Button>
            </div>
            <Space wrap size={8}>
              <Button icon={<ReloadOutlined />} onClick={reload}>
                刷新
              </Button>
              <Button icon={<ExportOutlined />} onClick={handleExport}>
                导出
              </Button>
              <Button
                icon={<MergeCellsOutlined />}
                onClick={loadDuplicates}
                loading={duplicateLoading}
              >
                客户去重
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
                }}
                style={{ width: 320 }}
                allowClear
              />
              <Select
                allowClear
                placeholder="生命周期"
                style={{ width: 130 }}
                value={statusFilter}
                onChange={(v) => setStatusFilter(v)}
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
                onChange={(v) => setLevelFilter(v)}
                options={["A", "B", "C", "D"].map((value) => ({ value, label: value }))}
              />
              <Select
                allowClear
                placeholder="区域"
                style={{ width: 120 }}
                value={regionFilter}
                onChange={(v) => setRegionFilter(v)}
                options={["华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"].map(
                  (value) => ({ value, label: value }),
                )}
              />
              <Button
                onClick={() => {
                  setSearch("");
                  setDebouncedSearch("");
                  setGroup("all");
                  setStatusFilter(undefined);
                  setLevelFilter(undefined);
                  setRegionFilter(undefined);
                  setMissingErp(false);
                }}
              >
                重置
              </Button>
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

          <CustomerBatchBar
            selectedIds={selectedRowKeys as number[]}
            selectedCount={selectedRowKeys.length}
            onClear={() => setSelectedRowKeys([])}
            onBatchComplete={reload}
          />

          <ProTable<Customer>
            actionRef={actionRef}
            rowKey="id"
            columns={columns}
            loading={customersQuery.isLoading || customersQuery.isFetching}
            dataSource={customersQuery.data?.list || []}
            search={false}
            options={
              isMobile
                ? false
                : { reload: () => customersQuery.refetch(), density: true, setting: true }
            }
            onSubmit={customersQuery.refetch}
            pagination={{
              total: customersQuery.data?.total,
              current: page,
              pageSize,
              showSizeChanger: true,
              pageSizeOptions: isMobile ? undefined : [20, 50, 100],
              showQuickJumper: !isMobile,
              showTotal: (t, range) => `第 ${range[0]}-${range[1]} 条 / 共 ${t} 条`,
              onChange: (p, ps) => {
                setPage(ps !== pageSize ? 1 : p);
                setPageSize(ps);
              },
            }}
            rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
            scroll={{ x: isMobile ? 800 : 1300 }}
            sticky
            tableStyle={{ cursor: "pointer" }}
            onRow={(r) => ({
              onClick: () => {
                setSelectedCustomer(r);
                setDetailOpen(true);
              },
            })}
          />
        </div>

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
        <CustomerFormDrawer
          open={formOpen}
          customerId={editingCustomer?.id}
          initialValues={editingCustomer as unknown as Record<string, unknown> | undefined}
          onClose={() => {
            setFormOpen(false);
            setEditingCustomer(null);
          }}
          onSuccess={reload}
        />
        <CustomerQuickFollowUpDrawer
          open={Boolean(followUpCustomer)}
          saving={followUpSaving}
          customer={followUpCustomer}
          form={followUpForm}
          onClose={() => {
            setFollowUpCustomer(null);
            followUpForm.resetFields();
          }}
          onSubmit={submitQuickFollowUp}
        />
        <CustomerDuplicateListModal
          open={duplicateOpen}
          pairs={duplicatePairs}
          onClose={() => setDuplicateOpen(false)}
          onMerge={(pair) => setMergePair(pair)}
        />
        <CustomerMergeModal
          open={Boolean(mergePair)}
          loading={mergeLoading}
          pair={mergePair}
          onCancel={() => setMergePair(null)}
          onConfirm={confirmMerge}
          onSwap={() => {
            if (!mergePair) return;
            setMergePair({
              ...mergePair,
              customer_a: mergePair.customer_b,
              customer_b: mergePair.customer_a,
            });
          }}
        />
      </CustomerModuleShell>
    </ErrorBoundary>
  );
}
