import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Button, Card, Col, Empty, Input, Row, Select, Space, Statistic, Tag, Typography } from "antd";
import {
  AimOutlined,
  AppstoreOutlined,
  AuditOutlined,
  BarChartOutlined,
  CarOutlined,
  DollarOutlined,
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
  return <Tag color={meta.color}>{meta.label}</Tag>;
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
    { key: "opportunities", label: "商机", path: "/sales/opportunities", icon: <ThunderboltOutlined /> },
    { key: "quotations", label: "报价", path: "/sales/quotations", icon: <FileTextOutlined /> },
    { key: "orders", label: "订单", path: "/sales/orders", icon: <ShoppingCartOutlined /> },
    { key: "delivery", label: "发货", path: "/sales/delivery-notes", icon: <CarOutlined /> },
    { key: "contracts", label: "合同", path: "/sales/contracts", icon: <AuditOutlined /> },
    { key: "invoices", label: "开票", path: "/sales/invoices", icon: <ReconciliationOutlined /> },
    { key: "payments", label: "回款", path: "/sales/payments", icon: <DollarOutlined /> },
    { key: "targets", label: "目标", path: "/sales/targets", icon: <AimOutlined /> },
    { key: "inquiry", label: "询价", path: "/sales/inquiry", icon: <MessageOutlined /> },
    { key: "analysis", label: "分析", path: "/reports/sales", icon: <BarChartOutlined /> },
  ];

  return (
    <div style={{ maxWidth: 1440, margin: "0 auto", padding: "4px 0 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{title}</Typography.Title>
          {subtitle ? <Typography.Text type="secondary">{subtitle}</Typography.Text> : null}
        </div>
        <Space wrap>{extra}</Space>
      </div>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          {tabs.map((tab) => (
            <Button
              key={tab.key}
              type={activeKey === tab.key ? "primary" : "text"}
              icon={tab.icon}
              onClick={() => navigate(tab.path)}
            >
              {tab.label}
            </Button>
          ))}
        </Space>
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
    <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
      {items.map((item) => (
        <Col xs={12} md={8} xl={4} key={item.title}>
          <Card size="small">
            <Statistic
              title={item.title}
              value={item.value}
              suffix={item.suffix}
              prefix={item.prefix}
              precision={item.precision}
            />
          </Card>
        </Col>
      ))}
    </Row>
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
