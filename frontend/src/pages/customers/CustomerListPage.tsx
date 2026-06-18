/**
 * CustomerListPage — 新版客户管理列表页
 * 排序: last_contacted_at ASC (最早互动在前)
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Dropdown,
  Input,
  message,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
  theme,
  Typography,
} from "antd";
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  EllipsisOutlined,
  PhoneFilled,
  ThunderboltOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { useNavigate } from "react-router-dom";
import { getCustomers, getApiErrorMessage } from "@/api";
import type { Customer } from "@/types";
import { ErrorBoundary, StatusTag, useColumnResize } from "@/ui";
import CustomerModuleShell from "./CustomerModuleShell";
import { CustomerDetailPanel } from "./CustomerDetailPanel";
import { CustomerFormDrawer } from "./CustomerFormDrawer";
import { CustomerBatchBar } from "./CustomerBatchBar";
import {
  GROUP_OPTIONS,
  GROUP_FILTERS,
  STATUS_CONFIG,
  type GroupValue,
} from "./constants";

const { Text } = Typography;

const CREDIT_COLORS: Record<string, string> = {
  A: "green", B: "blue", C: "orange", D: "red",
};

function relativeTime(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (diff === 0) return "今天";
  if (diff === 1) return "昨天";
  if (diff < 30) return `${diff}天前`;
  if (diff < 365) return `${Math.floor(diff / 30)}月前`;
  return `${Math.floor(diff / 365)}年前`;
}

interface CustomerColumnActions {
  onCreateOpportunity: (customer: Customer) => void;
  onFollowUp: (customer: Customer) => void;
  onEdit: (customer: Customer) => void;
}

function buildColumns(actions: CustomerColumnActions): ColumnsType<Customer> {
  return [
  {
    title: "客户名称", dataIndex: "name", width: 180,
    render: (name: string) => (
      <Text strong copyable={{ tooltips: false }} style={{ cursor: "pointer" }}>{name}</Text>
    ),
  },
  {
    title: "行业", dataIndex: "industry", width: 100, ellipsis: true,
    render: (v: string | null) => v || "-",
  },
  {
    title: "状态", dataIndex: "status", width: 100,
    render: (s: string) => {
      const c = STATUS_CONFIG[s] || { label: s || "-", color: "default" };
      return <StatusTag tone={c.color as "green" | "blue" | "gold"}>{c.label}</StatusTag>;
    },
  },
  {
    title: "信用等级", dataIndex: "credit_level", width: 100,
    render: (l: string) => l ? <Tag color={CREDIT_COLORS[l] || "default"}>{l}</Tag> : "-",
  },
  {
    title: "最后互动", dataIndex: "last_contacted_at", width: 120,
    render: (d: string | null) => d ? relativeTime(d) : <Text type="secondary">-</Text>,
  },
  {
    title: "交易金额", dataIndex: "total_amount", width: 140, align: "right",
    render: (v: number | null) =>
      v != null ? <Text style={{ fontVariantNumeric: "tabular-nums" }}>¥{v.toLocaleString("zh-CN")}</Text> : "-",
  },
  {
    title: "操作", key: "actions", width: 56, align: "center", fixed: "right",
    render: (_: unknown, r) => (
      <div onClick={(event) => event.stopPropagation()}>
        <Dropdown
          trigger={["click"]}
          placement="bottomRight"
          menu={{
            items: [
              { key: "opportunity", icon: <ThunderboltOutlined />, label: "新增机会" },
              { key: "follow-up", icon: <PhoneFilled />, label: "新增跟进" },
              { key: "edit", icon: <EditOutlined />, label: "编辑客户" },
            ],
            onClick: ({ key, domEvent }) => {
              domEvent.stopPropagation();
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
  const { token } = theme.useToken();
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
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [group, setGroup] = useState<GroupValue>("all");
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  // 搜索防抖 300ms
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  // 加载数据
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: 50,
        q: debouncedSearch || undefined,
        sort_by: "last_contacted_at",
        sort_order: "asc",
      };
      // Apply group preset filters
      if (group !== "all") {
        const gf = GROUP_FILTERS[group];
        if (gf.status) params.status = gf.status.join(",");
      }
      // Apply explicit status filter (overrides group)
      if (statusFilter) params.status = statusFilter;
      const res = await getCustomers(params);
      const payload = res.data?.data as { list?: Customer[]; total?: number } | undefined;
      setData(payload?.list || []);
      setTotal(payload?.total || 0);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载客户列表失败")); } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, group, statusFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const baseColumns = buildColumns({
    onCreateOpportunity: (customer) => navigate(`/sales/opportunities/new?customer_id=${customer.id}`),
    onFollowUp: (customer) => navigate(`/customers/${customer.id}/follow-ups/new`),
    onEdit: (customer) => {
      setEditingCustomer(customer);
      setFormOpen(true);
    },
  });
  const columns = useColumnResize(baseColumns);

  return (
    <ErrorBoundary>
      <CustomerModuleShell title="客户列表" subtitle="搜索客户、查看详情与商业洞察">
        <div className="customer-table-card" style={{ border: `1px solid ${token.colorBorderSecondary}`, borderRadius: 4, background: "#fff" }}>
          {/* 搜索筛选栏 */}
          <div style={{ padding: "10px 14px", borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
            <Space wrap>
              <Input
                placeholder="搜索客户名称、电话..."
                prefix={<SearchOutlined />}
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                style={{ width: 300 }}
                allowClear
              />
              <Segmented
                options={GROUP_OPTIONS.map((g) => ({ label: g.label, value: g.value }))}
                value={group}
                onChange={(v) => { setGroup(v as GroupValue); setPage(1); }}
              />
              <Select
                allowClear
                placeholder="状态"
                style={{ width: 110 }}
                value={statusFilter}
                onChange={(v) => { setStatusFilter(v); setPage(1); }}
                options={Object.entries(STATUS_CONFIG).map(([k, v]) => ({ value: k, label: v.label }))}
              />
              <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingCustomer(null); setFormOpen(true); }}>
                新增客户
              </Button>
            </Space>
          </div>

          {/* 批量操作栏 */}
          <CustomerBatchBar
            selectedIds={selectedRowKeys as number[]}
            selectedCount={selectedRowKeys.length}
            onClear={() => setSelectedRowKeys([])}
            onBatchComplete={fetchData}
          />

          {/* 表格 */}
          <Table<Customer>
            rowKey="id"
            columns={columns}
            dataSource={data}
            loading={loading}
            size="middle"
            scroll={{ x: "max-content" }}
            rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
            pagination={{
              current: page, pageSize: 50, total,
              showSizeChanger: false,
              showTotal: (t) => `共 ${t} 条`,
              onChange: (p) => setPage(p),
            }}
            onRow={(r) => ({
              onClick: () => { setSelectedCustomer(r); setDetailOpen(true); },
              style: { cursor: "pointer" },
            })}
          />
        </div>

        {/* 详情面板 */}
        {selectedCustomer && (
          <CustomerDetailPanel
            customerId={selectedCustomer.id as number}
            customerName={(selectedCustomer.name as string) || ""}
            customer={selectedCustomer as unknown as Record<string, unknown>}
            open={detailOpen}
            onClose={() => { setDetailOpen(false); setSelectedCustomer(null); }}
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
          onClose={() => { setFormOpen(false); setEditingCustomer(null); }}
          onSuccess={fetchData}
        />
      </CustomerModuleShell>
    </ErrorBoundary>
  );
}
