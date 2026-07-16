import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Button, Card, Empty, Flex, Input, Select, Space, Statistic, Tag, Tooltip, Typography } from "antd";
import { StatusTag } from "../../ui";
import {
  AimOutlined,
  AppstoreOutlined,
  AuditOutlined,
  BarChartOutlined,
  CarOutlined,
  DollarOutlined,
  DownloadOutlined,
  FileTextOutlined,
  MessageOutlined,
  PhoneOutlined,
  PlusOutlined,
  ReconciliationOutlined,
  ShoppingCartOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { getCustomer, getCustomers, getOpportunity, getOpportunities, getProduct, getProducts, getQuotation, getQuotations } from "../../api";
import type { Customer, Opportunity, Product, Quotation } from "../../types";

export const money = (value?: number | null) => `¥${Number(value || 0).toLocaleString()}`;

export const shortDate = (value?: string | null) => value?.slice(0, 10) || "-";

export const stageLabel: Record<string, string> = {
  lead: "线索",
  qualified: "需求确认",
  qualification: "需求确认",
  proposal: "方案/报价",
  negotiation: "谈判",
  closed_won: "赢单",
  closed_lost: "输单",
};

export const salesStatus: Record<string, { color: string; label: string }> = {
  active: { color: "blue", label: "活跃" },
  won: { color: "green", label: "赢单" },
  lost: { color: "red", label: "输单" },
  draft: { color: "default", label: "草稿" },
  sent: { color: "blue", label: "已发送" },
  pending: { color: "default", label: "待确认" },
  confirmed: { color: "blue", label: "已确认" },
  shipped: { color: "orange", label: "已发货" },
  delivered: { color: "green", label: "已签收" },
  returned: { color: "red", label: "已退回" },
  cancelled: { color: "red", label: "已取消" },
};

export function SalesStatusTag({ value }: { value?: string | null }) {
  const meta = salesStatus[value || ""] || { color: "default", label: value || "-" };
  return <StatusTag status={value || "-"} color={meta.color} label={meta.label} />;
}

export function SalesModuleShell({
  title,
  subtitle,
  activeKey,
  extra,
  children,
}: {
  title: string;
  subtitle?: string;
  activeKey?: string;
  extra?: ReactNode;
  children: ReactNode;
}) {
  const navigate = useNavigate();
  const tabs = [
    { key: "dashboard", label: "工作台", path: "/sales/dashboard", icon: <AppstoreOutlined /> },
    { key: "inquiry", label: "询价", path: "/sales/inquiry", icon: <MessageOutlined /> },
    { key: "opportunities", label: "商机", path: "/sales/opportunities", icon: <ThunderboltOutlined /> },
    { key: "quotations", label: "报价", path: "/sales/quotations", icon: <FileTextOutlined /> },
    { key: "orders", label: "订单", path: "/sales/orders", icon: <ShoppingCartOutlined /> },
    { key: "contracts", label: "合同", path: "/sales/contracts", icon: <AuditOutlined /> },
    { key: "delivery", label: "发货", path: "/sales/delivery-notes", icon: <CarOutlined /> },
    { key: "invoices", label: "开票", path: "/sales/invoices", icon: <ReconciliationOutlined /> },
    { key: "payments", label: "回款", path: "/sales/payments", icon: <DollarOutlined /> },
    { key: "targets", label: "目标", path: "/sales/targets", icon: <AimOutlined /> },
    { key: "analysis", label: "分析", path: "/reports/sales", icon: <BarChartOutlined /> },
  ];
  const flow = [
    { key: "inquiry", label: "询价" },
    { key: "opportunities", label: "商机" },
    { key: "quotations", label: "报价" },
    { key: "orders", label: "订单" },
    { key: "contracts", label: "合同" },
    { key: "delivery", label: "发货" },
    { key: "invoices", label: "开票" },
    { key: "payments", label: "回款" },
  ];

  return (
    <div className="sales-erp-shell">
      <style>{`
        .sales-erp-shell {
          width: 100%;
          padding: 0 0 12px;
        }
        .sales-erp-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 8px;
          padding: 10px 12px;
          background: var(--color-canvas, #fff);
          border: 1px solid var(--color-border, #e5e7eb);
          border-radius: 8px;
        }
        .sales-erp-title {
          margin: 0;
          color: var(--color-text, #111827);
          font-size: 17px;
          font-weight: 650;
          line-height: 24px;
        }
        .sales-erp-subtitle {
          display: block;
          margin-top: 1px;
          color: var(--color-text-secondary, #6b7280);
          font-size: 12px;
          line-height: 18px;
        }
        .sales-erp-actions {
          display: flex;
          justify-content: flex-end;
          flex: 1 1 360px;
        }
        .sales-erp-nav-card.ant-card-small > .ant-card-body {
          padding: 5px 8px;
        }
        .sales-erp-nav {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          overflow-x: auto;
        }
        .sales-erp-modules,
        .sales-erp-flow {
          display: flex;
          align-items: center;
          gap: 4px;
          min-width: max-content;
        }
        .sales-erp-flow {
          padding-left: 12px;
          border-left: 1px solid var(--color-border, #e3e8ee);
        }
        .sales-erp-flow-step {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          color: var(--color-text-secondary, #6b7280);
          font-size: 12px;
        }
        .sales-erp-flow-step.is-active {
          color: var(--color-primary, #1677ff);
          font-weight: 600;
        }
        .sales-erp-flow-dot {
          width: 6px;
          height: 6px;
          border-radius: 999px;
          background: var(--color-border, #e3e8ee);
        }
        .sales-erp-flow-step.is-active .sales-erp-flow-dot {
          background: var(--color-primary, #1677ff);
        }
        .sales-erp-flow-arrow {
          color: var(--color-border, #e3e8ee);
          font-size: 11px;
        }
        .sales-erp-metrics {
          display: grid;
          grid-template-columns: repeat(6, minmax(0, 1fr));
          gap: 8px;
          margin-bottom: 8px;
        }
        .sales-erp-metric {
          min-height: 60px;
          padding: 8px 10px;
          background: var(--color-canvas, #fff);
          border: 1px solid var(--color-border, #e5e7eb);
          border-radius: 6px;
        }
        .sales-erp-metric-title {
          color: var(--color-text-secondary, #6b7280);
          font-size: 11px;
          line-height: 16px;
        }
        .sales-erp-metric-value {
          margin-top: 4px;
          color: var(--color-text, #111827);
          font-size: 18px;
          font-weight: 650;
          line-height: 1;
        }
        .sales-erp-toolbar.ant-card-small > .ant-card-body {
          padding: 6px 10px;
        }
        .sales-erp-table-card.ant-card-small > .ant-card-body {
          padding: 0;
        }
        .sales-erp-table-card .ant-tabs {
          padding: 0 10px;
        }
        .sales-erp-table-card .ant-tabs-nav {
          margin-bottom: 8px;
        }
        .sales-erp-table-card .ant-card-head {
          min-height: 38px;
          padding: 0 10px;
          border-bottom-color: var(--color-border, #e5e7eb);
        }
        .sales-erp-table-card .ant-card-head-title,
        .sales-erp-table-card .ant-card-extra {
          padding: 6px 0;
        }
        .sales-erp-table-card .ant-table-thead > tr > th {
          background: var(--color-bg-layout, #f9fafb);
          color: var(--color-text-secondary, #374151);
          font-weight: 600;
        }
        .sales-erp-table-card .ant-table-tbody > tr > td {
          vertical-align: middle;
          padding: 3px 8px !important;
        }
        .sales-erp-table-card .ant-table-thead > tr > th {
          padding: 5px 8px !important;
        }
        .sales-erp-table-card .ant-table-tbody > tr.erp-row-even > td {
          background: var(--color-bg-layout, #f9fafb);
        }
        .sales-erp-table-card .ant-table-tbody > tr:hover > td {
          background: var(--color-primary-bg, #eef2ff) !important;
        }
        .sales-erp-table-card .erp-status-dot {
          display: inline-block;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          margin-right: 6px;
          vertical-align: middle;
        }
        .sales-erp-table-card .erp-cell-primary {
          color: var(--color-text, #111827);
          font-weight: 500;
          font-size: 13px;
        }
        .sales-erp-table-card .erp-cell-secondary {
          color: var(--color-text-tertiary, #94a3b8);
          font-size: 11px;
          line-height: 1.4;
        }
        @media (max-width: 1180px) {
          .sales-erp-metrics {
            grid-template-columns: repeat(3, minmax(0, 1fr));
          }
          .sales-erp-nav {
            align-items: flex-start;
            flex-direction: column;
          }
          .sales-erp-flow {
            padding-left: 0;
            border-left: 0;
          }
        }
        @media (max-width: 768px) {
          .sales-erp-header {
            flex-direction: column;
          }
          .sales-erp-actions {
            width: 100%;
            justify-content: flex-start;
          }
          .sales-erp-metrics {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .sales-list-toolbar {
            width: 100%;
          }
          .sales-list-toolbar > .ant-space-item {
            max-width: 100%;
          }
          .sales-list-toolbar .sales-customer-filter {
            width: 100% !important;
          }
          .sales-list-toolbar .ant-select {
            width: 100% !important;
          }
        }
      `}</style>
      <div className="sales-erp-header">
        <div>
          <h1 className="sales-erp-title">{title}</h1>
          {subtitle ? <span className="sales-erp-subtitle">{subtitle}</span> : null}
        </div>
        <div className="sales-erp-actions">
          <Space wrap>{extra}</Space>
        </div>
      </div>
      <Card size="small" className="sales-erp-nav-card" style={{ marginBottom: 12 }}>
        <div className="sales-erp-nav">
          <div className="sales-erp-modules">
            {tabs.map((tab) => (
              <Button
                key={tab.key}
                size="small"
                type={activeKey === tab.key ? "primary" : "text"}
                icon={tab.icon}
                onClick={() => navigate(tab.path)}
              >
                {tab.label}
              </Button>
            ))}
          </div>
          <div className="sales-erp-flow" aria-label="销售流程">
            {flow.map((step, index) => (
              <span className={`sales-erp-flow-step${activeKey === step.key ? " is-active" : ""}`} key={step.key}>
                <span className="sales-erp-flow-dot" />
                <span>{step.label}</span>
                {index < flow.length - 1 && <span className="sales-erp-flow-arrow">/</span>}
              </span>
            ))}
          </div>
        </div>
      </Card>
      {children}
    </div>
  );
}

export function MetricBand({
  items,
}: {
  items: Array<{ title: string; value: number | string; suffix?: string; prefix?: ReactNode; precision?: number }>;
}) {
  return (
    <div className="sales-erp-metrics">
      {items.map((item) => (
        <div className="sales-erp-metric" key={item.title}>
          <div className="sales-erp-metric-title">{item.title}</div>
          <Statistic
            className="sales-erp-metric-value"
            value={item.value}
            suffix={item.suffix}
            prefix={item.prefix}
            precision={item.precision}
          />
        </div>
      ))}
    </div>
  );
}

export function CustomerSelect({ value, onChange }: { value?: number; onChange?: (value?: number) => void }) {
  const [items, setItems] = useState<Customer[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      getCustomers({ page: 1, page_size: 30, q: search }).then((r) => setItems(r.data.data.list || [])).catch(() => {});
    }, 240);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (!value || items.some((item) => item.id === value)) return;
    getCustomer(value)
      .then((r) => setItems((prev) => (prev.some((item) => item.id === value) ? prev : [r.data.data, ...prev])))
      .catch(() => {});
  }, [items, value]);

  return (
    <Select
      showSearch
      allowClear
      value={value}
      placeholder="搜索客户名称"
      filterOption={false}
      onSearch={setSearch}
      onChange={onChange}
      notFoundContent={<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无匹配客户" />}
      options={items.map((c) => ({
        value: c.id,
        label: c.name,
      }))}
    />
  );
}

export function CustomerLink({ id }: { id?: number | null }) {
  const navigate = useNavigate();
  const [name, setName] = useState<string>("");

  useEffect(() => {
    if (!id) return;
    getCustomer(id).then((r) => setName(r.data.data.name)).catch(() => setName(""));
  }, [id]);

  if (!id) return <Typography.Text type="secondary">未关联客户</Typography.Text>;

  return (
    <Typography.Link onClick={() => navigate(`/customers/${id}`)}>
      {name || `客户 #${id}`}
    </Typography.Link>
  );
}

export function OpportunitySelect({
  value,
  onChange,
  customerId,
  onOpportunityPicked,
}: {
  value?: number;
  onChange?: (value?: number) => void;
  customerId?: number;
  onOpportunityPicked?: (opportunity: Opportunity) => void;
}) {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      getOpportunities({
        page: 1,
        page_size: 30,
        q: search,
        ...(customerId ? { customer_id: customerId } : {}),
      })
        .then((r) => setItems(r.data.data.list || []))
        .catch(() => {});
    }, 240);
    return () => window.clearTimeout(timer);
  }, [customerId, search]);

  useEffect(() => {
    if (!value || items.some((item) => item.id === value)) return;
    getOpportunity(value)
      .then((r) => setItems((prev) => (prev.some((item) => item.id === value) ? prev : [r.data.data, ...prev])))
      .catch(() => {});
  }, [items, value]);

  const byId = useMemo(() => new Map(items.map((item) => [item.id, item])), [items]);

  return (
    <Select
      showSearch
      allowClear
      value={value}
      placeholder="搜索商机标题"
      filterOption={false}
      onSearch={setSearch}
      onChange={(next) => {
        onChange?.(next);
        const opportunity = byId.get(Number(next));
        if (opportunity) onOpportunityPicked?.(opportunity);
      }}
      notFoundContent={<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无匹配商机" />}
      options={items.map((opportunity) => ({
        value: opportunity.id,
        label: opportunity.title,
      }))}
    />
  );
}

export function OpportunityLink({ id }: { id?: number | null }) {
  const navigate = useNavigate();
  const [title, setTitle] = useState<string>("");

  useEffect(() => {
    if (!id) return;
    getOpportunity(id).then((r) => setTitle(r.data.data.title)).catch(() => setTitle(""));
  }, [id]);

  if (!id) return <Typography.Text type="secondary">未关联商机</Typography.Text>;

  return (
    <Typography.Link onClick={() => navigate(`/sales/opportunities/${id}`)}>
      {title || `商机 #${id}`}
    </Typography.Link>
  );
}

export function QuotationSelect({
  value,
  onChange,
  customerId,
}: {
  value?: number;
  onChange?: (value?: number) => void;
  customerId?: number;
}) {
  const [items, setItems] = useState<Quotation[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      getQuotations({
        page: 1,
        page_size: 30,
        q: search,
        ...(customerId ? { customer_id: customerId } : {}),
      })
        .then((r) => setItems(r.data.data.list || []))
        .catch(() => {});
    }, 240);
    return () => window.clearTimeout(timer);
  }, [customerId, search]);

  useEffect(() => {
    if (!value || items.some((item) => item.id === value)) return;
    getQuotation(value)
      .then((r) => setItems((prev) => (prev.some((item) => item.id === value) ? prev : [r.data.data, ...prev])))
      .catch(() => {});
  }, [items, value]);

  return (
    <Select
      showSearch
      allowClear
      value={value}
      placeholder="搜索报价单号 / 标题 / 产品"
      filterOption={false}
      onSearch={setSearch}
      onChange={onChange}
      notFoundContent={<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无匹配报价" />}
      options={items.map((quotation) => ({
        value: quotation.id,
        label: [
          quotation.quotation_no || `报价 #${quotation.id}`,
          quotation.title,
          money(quotation.total_amount),
          salesStatus[quotation.status]?.label || quotation.status,
        ].filter(Boolean).join(" · "),
      }))}
    />
  );
}

export const getProductOptionLabel = (p: Product) => [
  p.name,
].filter(Boolean).join(" ");

const loadProductCandidates = async (search: string) => {
  const pageSize = 100;
  const first = await getProducts({ page: 1, page_size: pageSize, q: search, sort: "name_asc" });
  const data = first.data.data;
  const list = [...(data.list || [])];
  const total = data.total || list.length;
  const pageCount = Math.ceil(total / pageSize);

  if (pageCount <= 1) return list;

  const rest = await Promise.all(
    Array.from({ length: pageCount - 1 }, (_, index) =>
      getProducts({ page: index + 2, page_size: pageSize, q: search, sort: "name_asc" })
    )
  );
  rest.forEach((response) => list.push(...(response.data.data.list || [])));
  return list;
};

export function ProductSelect({
  value,
  onChange,
  onProductPicked,
}: {
  value?: number;
  onChange?: (value?: number) => void;
  onProductPicked?: (product: Product) => void;
}) {
  const [items, setItems] = useState<Product[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      loadProductCandidates(search)
        .then((list) => {
          if (!cancelled) setItems(list);
        })
        .catch(() => {});
    }, 240);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [search]);

  useEffect(() => {
    if (!value || items.some((item) => item.id === value)) return;
    getProduct(value)
      .then((r) => setItems((prev) => (prev.some((item) => item.id === value) ? prev : [r.data.data, ...prev])))
      .catch(() => {});
  }, [items, value]);

  const byId = useMemo(() => new Map(items.map((p) => [p.id, p])), [items]);

  return (
    <Select
      showSearch
      allowClear
      value={value}
      placeholder="搜索全局产品名称"
      filterOption={false}
      onSearch={setSearch}
      onChange={(next) => {
        onChange?.(next);
        const product = byId.get(Number(next));
        if (product) onProductPicked?.(product);
      }}
      notFoundContent={<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无匹配产品" />}
      options={items.map((p) => ({
        value: p.id,
        label: getProductOptionLabel(p),
      }))}
    />
  );
}

export function SalesQuickActions() {
  const navigate = useNavigate();
  return (
    <Space wrap>
      <Button icon={<PhoneOutlined />} onClick={() => navigate("/customers")}>客户池</Button>
      <Button icon={<ThunderboltOutlined />} onClick={() => navigate("/sales/opportunities/new")}>新建商机</Button>
      <Button icon={<FileTextOutlined />} onClick={() => navigate("/sales/quotations/new")}>新建报价</Button>
      <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/orders/new")}>新建订单</Button>
    </Space>
  );
}

// ─── ERP Professional Table Utilities ────────────────────────────

/** Shared rowClassName for striping — pass the page state & size */
export const erpRowClass = (_: unknown, index: number) => (index % 2 === 0 ? "erp-row-even" : "");

/** Status dot indicator: <span className="erp-status-dot" style={{background:"..."}} /> */
export const statusDot = (color: string) => <span className="erp-status-dot" style={{ background: color }} />;

/** Map status values to dot colors for consistent table display */
export const ERP_STATUS_DOT: Record<string, string> = {
  draft: "#d9d9d9", pending: "#d9d9d9", sent: "#1677ff", confirmed: "#1677ff",
  active: "#1677ff", signed: "#1677ff", shipped: "#faad14",
  delivered: "#52c41a", completed: "#52c41a", won: "#52c41a",
  expired: "#faad14", overdue: "#ff4d4f",
  lost: "#ff4d4f", cancelled: "#ff4d4f", terminated: "#ff4d4f",
};

export interface ExportColumn {
  key: string;
  title: string;
}

export function exportToCSV(data: Record<string, unknown>[], columns: ExportColumn[], filename: string): void {
  const header = columns.map((col) => col.title).join(",");
  const rows = data.map((row) =>
    columns
      .map((col) => {
        const val = row[col.key];
        const str = val == null ? "" : String(val);
        return str.includes(",") || str.includes('"') || str.includes("\n") ? `"${str.replace(/"/g, '""')}"` : str;
      })
      .join(","),
  );
  const csv = [header, ...rows].join("\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function ErpExportButton({
  data,
  columns,
  filename,
  disabled,
}: {
  data: Record<string, unknown>[];
  columns: ExportColumn[];
  filename?: string;
  disabled?: boolean;
}) {
  return (
    <Tooltip title="导出CSV">
      <Button icon={<DownloadOutlined />} disabled={disabled} onClick={() => exportToCSV(data, columns, filename || "export.csv")}>
        导出
      </Button>
    </Tooltip>
  );
}

export function ErpAuditInfo({ createdAt, updatedAt }: { createdAt?: string | null; updatedAt?: string | null }) {
  const formatRelative = (dateStr: string): string => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return "刚刚";
    if (minutes < 60) return `${minutes}分钟前`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}小时前`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}天前`;
    return shortDate(dateStr);
  };
  return (
    <Space direction="vertical" size={2} style={{ width: "100%" }}>
      {createdAt ? (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          创建于 {shortDate(createdAt)} ({formatRelative(createdAt)})
        </Typography.Text>
      ) : null}
      {updatedAt && updatedAt !== createdAt ? (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          更新于 {shortDate(updatedAt)} ({formatRelative(updatedAt)})
        </Typography.Text>
      ) : null}
    </Space>
  );
}

export interface StatusStep {
  key: string;
  label: string;
}

export function ErpStatusTimeline({
  currentStatus,
  steps,
  createdAt,
  lostStatus,
}: {
  currentStatus: string;
  steps: StatusStep[];
  createdAt?: string | null;
  lostStatus?: string;
}) {
  const isLost = currentStatus === (lostStatus || "lost") || currentStatus === "cancelled";
  const currentIndex = steps.findIndex((s) => s.key === currentStatus);

  const getStatus = (stepKey: string): "done" | "active" | "pending" => {
    if (isLost) return "pending";
    const stepIndex = steps.findIndex((s) => s.key === stepKey);
    if (stepIndex < currentIndex) return "done";
    if (stepIndex === currentIndex) return "active";
    return "pending";
  };

  const COLORS: Record<string, string> = { done: "#52c41a", active: "#1677ff", pending: "#d9d9d9" };

  return (
    <Space direction="vertical" size={6} style={{ width: "100%" }}>
      {steps.map((step) => {
        const status = getStatus(step.key);
        return (
          <div key={step.key} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: COLORS[status],
                boxShadow: status === "active" ? "0 0 0 3px rgba(22,119,255,0.2)" : "none",
              }}
            />
            <Typography.Text
              style={{
                fontSize: 13,
                color: status === "pending" ? "#bfbfbf" : undefined,
                fontWeight: status === "active" ? 600 : 400,
              }}
            >
              {step.label}
            </Typography.Text>
          </div>
        );
      })}
      {isLost ? (
        <div style={{ display: "flex", alignItems: "center", gap: 8, opacity: 0.45 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ff4d4f" }} />
          <Typography.Text style={{ fontSize: 13 }}>已取消/丢失</Typography.Text>
        </div>
      ) : null}
      {createdAt ? <ErpAuditInfo createdAt={createdAt} /> : null}
    </Space>
  );
}
