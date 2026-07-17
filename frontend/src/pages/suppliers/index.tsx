import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Progress,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import { StatusTag } from "../../ui";
import { erpPagination } from "../../ui/pagination";
import {
  AuditOutlined,
  BankOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  GlobalOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  TeamOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  createSupplier,
  getSupplierStats,
  getSuppliers,
  updateSupplier,
  getApiErrorMessage,
} from "../../api";
import client from "../../api/client";
import type { Supplier } from "../../types";

const { Text } = Typography;

const SUPPLIER_TYPES = ["原厂", "代理商", "贸易商", "OEM", "代工厂", "其他"];
const PAGE_SIZE = 20;

type SupplierTaskKey =
  | "all"
  | "factory"
  | "agency"
  | "missing_contact"
  | "missing_profile"
  | "rated"
  | "overseas";

interface SupplierStats {
  total: number;
  certified: number;
  rated: number;
  recent_30d: number;
  missing_contact: number;
  missing_profile: number;
  overseas: number;
  by_type: { type: string; count: number }[];
  by_region: { region: string; count: number }[];
  by_rating: { rating: string; count: number }[];
  top_suppliers: { id: number; name: string; product_count: number }[];
}

const TASK_LABELS: Record<SupplierTaskKey, string> = {
  all: "全部供应商",
  factory: "原厂资源",
  agency: "代理渠道",
  missing_contact: "缺联系人",
  missing_profile: "资料待完善",
  rated: "已评级供应商",
  overseas: "海外供应商",
};

const hasContact = (supplier: Supplier) =>
  Boolean(supplier.contact_person || supplier.phone || supplier.email);
const isOverseas = (supplier: Supplier) =>
  /海外|香港|台湾|新加坡|美国|欧洲|日本|韩国/i.test(supplier.region || supplier.address || "");

const normalizeSupplierType = (value?: string | null) => {
  if (!value) return "";
  const normalized: Record<string, string> = {
    agency: "代理商",
    agent: "代理商",
    factory: "原厂",
    manufacturer: "原厂",
    trader: "贸易商",
    trade: "贸易商",
  };
  return normalized[value.toLowerCase()] || value;
};

const getSupplierCompletion = (supplier: Supplier) => {
  const fields = [
    supplier.name,
    supplier.contact_person,
    supplier.phone || supplier.email,
    normalizeSupplierType(supplier.supplier_type),
    supplier.product_lines,
    supplier.region,
    supplier.payment_terms,
    supplier.financial_rating,
    supplier.certifications,
  ];
  return Math.round((fields.filter(Boolean).length / fields.length) * 100);
};

const getMissingFields = (supplier: Supplier) => {
  const missing: string[] = [];
  if (!supplier.contact_person) missing.push("联系人");
  if (!supplier.phone && !supplier.email) missing.push("联系方式");
  if (!normalizeSupplierType(supplier.supplier_type)) missing.push("类型");
  if (!supplier.product_lines) missing.push("产品线");
  if (!supplier.region) missing.push("区域");
  if (!supplier.payment_terms) missing.push("付款条件");
  if (!supplier.financial_rating) missing.push("评级");
  if (!supplier.certifications) missing.push("认证");
  return missing;
};

const getSupplierAction = (supplier: Supplier) => {
  if (!hasContact(supplier))
    return { label: "补联系人", color: "red", note: "缺少联系人、电话或邮箱，无法快速询价。" };
  if (!supplier.product_lines)
    return { label: "补产品线", color: "orange", note: "缺少经营产品线，影响产品匹配。" };
  if (!supplier.financial_rating)
    return { label: "补评级", color: "gold", note: "缺少财务评级，建议补充供应商分层。" };
  if (!supplier.certifications)
    return { label: "补认证", color: "blue", note: "缺少认证信息，建议确认授权或资质。" };
  return { label: "正常维护", color: "green", note: "主数据较完整，可进入常规采购维护。" };
};

const isFormValidationError = (error: unknown) =>
  Boolean(error && typeof error === "object" && "errorFields" in error);

export default function SupplierList() {
  const [data, setData] = useState<Supplier[]>([]);
  const [stats, setStats] = useState<SupplierStats | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [search, setSearch] = useState("");
  const [supplierType, setSupplierType] = useState<string | undefined>();
  const [task, setTask] = useState<SupplierTaskKey>("all");
  const [activeSupplierId, setActiveSupplierId] = useState<number | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState(false);

  const [editOpen, setEditOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<Supplier | null>(null);
  const [editForm] = Form.useForm();
  const [editing, setEditing] = useState(false);

  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [batchDeleting, setBatchDeleting] = useState(false);

  const navigate = useNavigate();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const searchReadyRef = useRef(false);

  const fetch = async (p = page, q = search, st = supplierType) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: pageSize };
      if (q.trim()) params.keyword = q.trim();
      if (st) params.supplier_type = st;
      const resp = await getSuppliers(params);
      setData(resp.data.data.list as Supplier[]);
      setTotal(resp.data.data.total as number);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载供应商失败"));
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const resp = await getSupplierStats();
      setStats(resp.data.data as unknown as SupplierStats);
    } catch {
      setStats(null);
    }
  };

  useEffect(() => {
    fetch();
  }, [page, pageSize, supplierType]);

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    if (!searchReadyRef.current) {
      searchReadyRef.current = true;
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      fetch(1, search, supplierType);
    }, 350);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]);

  useEffect(() => {
    setSelectedRowKeys([]);
  }, [page, search, supplierType, task]);

  const supplierMatchesTask = (supplier: Supplier, key: SupplierTaskKey) => {
    const completion = getSupplierCompletion(supplier);
    const normalizedType = normalizeSupplierType(supplier.supplier_type);
    if (key === "all") return true;
    if (key === "factory") return normalizedType === "原厂";
    if (key === "agency") return normalizedType === "代理商";
    if (key === "missing_contact") return !hasContact(supplier);
    if (key === "missing_profile") return completion < 80 || getMissingFields(supplier).length > 0;
    if (key === "rated") return Boolean(supplier.financial_rating);
    if (key === "overseas") return isOverseas(supplier);
    return true;
  };

  const visibleData = useMemo(
    () => data.filter((item) => supplierMatchesTask(item, task)),
    [data, task],
  );

  const activeSupplier = useMemo(
    () => data.find((item) => item.id === activeSupplierId) || visibleData[0] || null,
    [activeSupplierId, data, visibleData],
  );

  const summary = useMemo(() => {
    const typeCounts = new Map<string, number>();
    let missingContact = 0;
    let missingProfile = 0;
    let rated = 0;
    let overseas = 0;
    for (const item of data) {
      const normalizedType = normalizeSupplierType(item.supplier_type);
      if (normalizedType) typeCounts.set(normalizedType, (typeCounts.get(normalizedType) || 0) + 1);
      if (!hasContact(item)) missingContact += 1;
      if (getSupplierCompletion(item) < 80 || getMissingFields(item).length > 0)
        missingProfile += 1;
      if (item.financial_rating) rated += 1;
      if (isOverseas(item)) overseas += 1;
    }
    return {
      factory: typeCounts.get("原厂") || 0,
      agency: typeCounts.get("代理商") || 0,
      missingContact,
      missingProfile,
      rated,
      overseas,
    };
  }, [data]);

  const taskItems = useMemo(
    () => [
      {
        key: "all" as SupplierTaskKey,
        label: TASK_LABELS.all,
        count: data.length,
        color: "default",
        note: "当前页供应商",
      },
      {
        key: "factory" as SupplierTaskKey,
        label: TASK_LABELS.factory,
        count: summary.factory,
        color: "blue",
        note: "原厂与直接资源",
      },
      {
        key: "agency" as SupplierTaskKey,
        label: TASK_LABELS.agency,
        count: summary.agency,
        color: "cyan",
        note: "代理商渠道",
      },
      {
        key: "missing_contact" as SupplierTaskKey,
        label: TASK_LABELS.missing_contact,
        count: summary.missingContact,
        color: "red",
        note: "无法快速联系",
      },
      {
        key: "missing_profile" as SupplierTaskKey,
        label: TASK_LABELS.missing_profile,
        count: summary.missingProfile,
        color: "orange",
        note: "主数据缺字段",
      },
      {
        key: "rated" as SupplierTaskKey,
        label: TASK_LABELS.rated,
        count: summary.rated,
        color: "green",
        note: "已有财务评级",
      },
      {
        key: "overseas" as SupplierTaskKey,
        label: TASK_LABELS.overseas,
        count: summary.overseas,
        color: "purple",
        note: "海外与跨境资源",
      },
    ],
    [data.length, summary],
  );

  const globalSummary = useMemo(() => {
    const factory = stats?.by_type.find((item) => item.type === "原厂")?.count ?? summary.factory;
    return {
      total: stats?.total ?? total,
      factory,
      missingContact: stats?.missing_contact ?? summary.missingContact,
      missingProfile: stats?.missing_profile ?? summary.missingProfile,
      certified: stats?.certified ?? 0,
      rated: stats?.rated ?? summary.rated,
    };
  }, [stats, summary, total]);

  const resetFilters = () => {
    setSearch("");
    setSupplierType(undefined);
    setTask("all");
    setActiveSupplierId(null);
    setPage(1);
    fetch(1, "", undefined);
  };

  const openCreate = () => {
    createForm.resetFields();
    setCreateOpen(true);
  };

  const handleCreate = async () => {
    setCreating(true);
    try {
      const values = await createForm.validateFields();
      await createSupplier(values);
      message.success("创建成功");
      setCreateOpen(false);
      createForm.resetFields();
      setPage(1);
      fetch(1);
      fetchStats();
    } catch (error) {
      if (!isFormValidationError(error)) message.error("创建失败");
    } finally {
      setCreating(false);
    }
  };

  const openEdit = (record: Supplier) => {
    setEditRecord(record);
    editForm.setFieldsValue({
      ...record,
      supplier_type: normalizeSupplierType(record.supplier_type) || undefined,
    });
    setEditOpen(true);
  };

  const handleEdit = async () => {
    if (!editRecord) return;
    setEditing(true);
    try {
      const values = await editForm.validateFields();
      await updateSupplier(editRecord.id, values);
      message.success("更新成功");
      setEditOpen(false);
      editForm.resetFields();
      setEditRecord(null);
      fetch();
      fetchStats();
    } catch (error) {
      if (!isFormValidationError(error)) message.error("更新失败");
    } finally {
      setEditing(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await client.delete(`/suppliers/${id}`);
      message.success("已删除");
      fetch();
      fetchStats();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "删除失败"));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) return;
    setBatchDeleting(true);
    let success = 0;
    let failed = 0;
    for (const id of selectedRowKeys) {
      try {
        await client.delete(`/suppliers/${id}`);
        success += 1;
      } catch {
        failed += 1;
      }
    }
    setBatchDeleting(false);
    setSelectedRowKeys([]);
    if (failed === 0) message.success(`已删除 ${success} 条`);
    else message.warning(`删除 ${success} 条，失败 ${failed} 条`);
    fetch();
    fetchStats();
  };

  const handleExport = () => {
    const headers = [
      "ID",
      "名称",
      "联系人",
      "电话",
      "邮箱",
      "地址",
      "产品线",
      "类型",
      "评级",
      "区域",
      "备注",
      "创建时间",
    ];
    const rows = visibleData.map((s) => [
      s.id,
      s.name,
      s.contact_person || "",
      s.phone || "",
      s.email || "",
      s.address || "",
      s.product_lines || "",
      normalizeSupplierType(s.supplier_type),
      s.financial_rating || "",
      s.region || "",
      s.notes || "",
      s.created_at?.slice(0, 10) || "",
    ]);
    const csv = [headers, ...rows]
      .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "suppliers.csv";
    a.click();
    URL.revokeObjectURL(url);
    message.success("导出成功");
  };

  const columns: ColumnsType<Supplier> = [
    {
      title: "供应商",
      dataIndex: "name",
      width: 220,
      fixed: "left",
      render: (v, r) => (
        <Space direction="vertical" size={0}>
          <a
            onClick={(event) => {
              event.stopPropagation();
              navigate(`/suppliers/${r.id}`);
            }}
          >
            {v}
          </a>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {r.region || normalizeSupplierType(r.supplier_type) || "-"}
            {r.status === "inactive" ? " · 停用" : r.status === "blacklisted" ? " · 黑名单" : ""}
          </Text>
        </Space>
      ),
    },
    {
      title: "类型",
      dataIndex: "supplier_type",
      width: 80,
      render: (v) =>
        normalizeSupplierType(v) ? <StatusTag>{normalizeSupplierType(v)}</StatusTag> : "-",
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 70,
      render: (v) =>
        v === "inactive" ? (
          <StatusTag tone="warning">停用</StatusTag>
        ) : v === "blacklisted" ? (
          <StatusTag tone="danger">黑名单</StatusTag>
        ) : (
          <StatusTag tone="success">正常</StatusTag>
        ),
    },
    { title: "联系人", dataIndex: "contact_person", width: 90, render: (v) => v || "-" },
    { title: "电话", dataIndex: "phone", width: 120, render: (v) => v || "-" },
    {
      title: "付款条件",
      dataIndex: "payment_terms",
      width: 110,
      render: (v) => (v ? <StatusTag tone="info">{v}</StatusTag> : "-"),
    },
    { title: "付款方式", dataIndex: "payment_method", width: 90, render: (v) => v || "-" },
    {
      title: "币种",
      dataIndex: "currency",
      width: 60,
      align: "center",
      render: (v) => <span style={{ fontFamily: "monospace", fontSize: 13 }}>{v || "CNY"}</span>,
    },
    { title: "贸易条款", dataIndex: "incoterms", width: 80, render: (v) => v || "-" },
    {
      title: "评分",
      dataIndex: "rating_score",
      width: 70,
      align: "center",
      render: (v) =>
        v != null ? (
          <StatusTag tone={v >= 4 ? "success" : v >= 3 ? "warning" : "danger"}>{v}</StatusTag>
        ) : (
          "-"
        ),
    },
    {
      title: "交期(天)",
      dataIndex: "lead_time_days",
      width: 80,
      align: "right",
      render: (v) => (v != null ? v : "-"),
    },
    {
      title: "评级",
      dataIndex: "financial_rating",
      width: 80,
      render: (v) => (v ? <StatusTag tone="success">{v}</StatusTag> : "-"),
    },
    {
      title: "产品线",
      dataIndex: "product_lines",
      width: 180,
      ellipsis: true,
      render: (v) => v || "-",
    },
    {
      title: "完整度",
      key: "completion",
      width: 100,
      render: (_: unknown, r) => {
        const score = getSupplierCompletion(r);
        const missing = getMissingFields(r);
        return (
          <Tooltip title={missing.length ? `缺少：${missing.join("、")}` : "资料完整"}>
            <Progress
              percent={score}
              size="small"
              showInfo={false}
              strokeColor={score >= 80 ? "#52c41a" : score >= 50 ? "#faad14" : "#ff4d4f"}
            />
          </Tooltip>
        );
      },
    },
    {
      title: "操作",
      key: "actions",
      width: 140,
      fixed: "right",
      render: (_: unknown, r: Supplier) => (
        <Space size={2} onClick={(e) => e.stopPropagation()}>
          <Tooltip title="详情">
            <Button
              size="small"
              type="link"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/suppliers/${r.id}`)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button size="small" type="link" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          </Tooltip>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const activeAction = activeSupplier ? getSupplierAction(activeSupplier) : null;
  const selectedCount = selectedRowKeys.length;

  return (
    <div className="supplier-workbench-page">
      <style>{`
        .supplier-workbench-page {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .supplier-health-strip {
          display: grid;
          grid-template-columns: 1.45fr repeat(4, minmax(120px, .8fr));
          gap: 10px;
        }
        .supplier-health-main,
        .supplier-health-metric,
        .supplier-panel {
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .supplier-health-main {
          min-height: 116px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }
        .supplier-health-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 18px;
          font-weight: 700;
        }
        .supplier-health-note,
        .supplier-task-note,
        .supplier-context-note {
          color: rgba(0,0,0,.45);
          font-size: 12px;
          line-height: 18px;
        }
        .supplier-health-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 12px;
        }
        .supplier-health-metric {
          min-height: 116px;
          padding: 14px;
          cursor: pointer;
          transition: border-color .16s ease, box-shadow .16s ease;
        }
        .supplier-health-metric:hover {
          border-color: #91caff;
          box-shadow: 0 2px 8px rgba(22,119,255,.1);
        }
        .supplier-health-label {
          display: block;
          margin-bottom: 10px;
          color: rgba(0,0,0,.45);
          font-size: 12px;
        }
        .supplier-health-value {
          display: flex;
          align-items: baseline;
          gap: 6px;
          font-size: 24px;
          font-weight: 700;
          line-height: 1;
        }
        .supplier-health-value small {
          color: rgba(0,0,0,.45);
          font-size: 12px;
          font-weight: 400;
        }
        .supplier-grid {
          display: grid;
          grid-template-columns: 230px minmax(0, 1fr) 280px;
          gap: 12px;
          align-items: start;
        }
        .supplier-side,
        .supplier-context {
          position: sticky;
          top: 76px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .supplier-panel-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          padding: 10px 12px;
          border-bottom: 1px solid #f0f0f0;
        }
        .supplier-panel-body {
          padding: 12px;
        }
        .supplier-task {
          width: 100%;
          padding: 10px 12px;
          border: 0;
          border-bottom: 1px solid #f5f5f5;
          background: transparent;
          text-align: left;
          cursor: pointer;
        }
        .supplier-task:hover,
        .supplier-task.is-active {
          background: #f0f7ff;
        }
        .supplier-task-main,
        .supplier-context-title {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .supplier-main {
          min-width: 0;
        }
        .supplier-toolbar {
          margin-bottom: 12px;
        }
        .supplier-toolbar .ant-card-body {
          padding: 12px;
        }
        .supplier-batch-bar {
          margin-bottom: 12px;
          padding: 10px 12px;
          background: #f0f5ff;
          border: 1px solid #adc6ff;
          border-radius: 8px;
        }
        .supplier-row-selected td {
          background: #e6f4ff !important;
        }
        .supplier-context-score {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
          margin-top: 10px;
        }
        .supplier-context-score > div {
          padding: 10px;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          background: #fafafa;
        }
        .supplier-context-number {
          display: block;
          margin-top: 4px;
          font-size: 20px;
          font-weight: 700;
        }
        .supplier-context-action {
          margin-top: 10px;
          padding: 10px;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          background: #fafafa;
        }
        @media (max-width: 1180px) {
          .supplier-health-strip {
            grid-template-columns: 1fr 1fr;
          }
          .supplier-health-main {
            grid-column: 1 / -1;
          }
          .supplier-grid {
            grid-template-columns: 1fr;
          }
          .supplier-side,
          .supplier-context {
            position: static;
          }
        }
        @media (max-width: 768px) {
          .supplier-health-strip {
            grid-template-columns: 1fr;
          }
        }
      `}</style>

      <div className="supplier-health-strip">
        <div className="supplier-health-main">
          <div>
            <div className="supplier-health-title">
              <TeamOutlined />
              <span>供应商管理工作台</span>
            </div>
            <div className="supplier-health-note">
              统一维护供应商主数据、联系人、产品线、评级、认证和区域信息。顶部为全量概览，左侧队列聚焦当前页待办。
            </div>
          </div>
          <div className="supplier-health-actions">
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新增供应商
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              导出当前视图
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => fetch()}>
              刷新
            </Button>
          </div>
        </div>
        <div className="supplier-health-metric" onClick={() => setTask("all")}>
          <span className="supplier-health-label">全量供应商</span>
          <span className="supplier-health-value">
            {globalSummary.total}
            <small>家</small>
          </span>
        </div>
        <div className="supplier-health-metric" onClick={() => setTask("factory")}>
          <span className="supplier-health-label">全量原厂资源</span>
          <span className="supplier-health-value">
            {globalSummary.factory}
            <small>家</small>
          </span>
        </div>
        <div className="supplier-health-metric" onClick={() => setTask("missing_contact")}>
          <span className="supplier-health-label">全量缺联系人</span>
          <span className="supplier-health-value">
            {globalSummary.missingContact}
            <small>家</small>
          </span>
        </div>
        <div className="supplier-health-metric" onClick={() => setTask("missing_profile")}>
          <span className="supplier-health-label">全量资料待完善</span>
          <span className="supplier-health-value">
            {globalSummary.missingProfile}
            <small>家</small>
          </span>
        </div>
      </div>

      <div className="supplier-grid">
        <aside className="supplier-side">
          <div className="supplier-panel">
            <div className="supplier-panel-head">
              <Space size={6}>
                <AuditOutlined />
                <Text strong>当前页队列</Text>
              </Space>
            </div>
            {taskItems.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`supplier-task${task === item.key ? " is-active" : ""}`}
                onClick={() => {
                  setTask(item.key);
                  setActiveSupplierId(null);
                  setPage(1);
                }}
              >
                <span className="supplier-task-main">
                  <span style={{ fontWeight: task === item.key ? 600 : 400 }}>{item.label}</span>
                  <StatusTag tone={item.color}>{item.count}</StatusTag>
                </span>
                <span className="supplier-task-note">{item.note}</span>
              </button>
            ))}
          </div>
        </aside>

        <main className="supplier-main">
          <Card size="small" className="supplier-toolbar">
            <Row gutter={[10, 10]} align="middle">
              <Col flex="320px">
                <Input
                  placeholder="搜索供应商名称/联系人/邮箱"
                  prefix={<SearchOutlined />}
                  allowClear
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setTask("all");
                    setPage(1);
                  }}
                />
              </Col>
              <Col>
                <Select
                  allowClear
                  placeholder="供应商类型"
                  style={{ width: 140 }}
                  value={supplierType}
                  onChange={(v) => {
                    setSupplierType(v);
                    setTask("all");
                    setPage(1);
                  }}
                  options={SUPPLIER_TYPES.map((t) => ({ value: t, label: t }))}
                />
              </Col>
              <Col flex="auto" />
              <Col>
                <Space wrap>
                  <Button icon={<ReloadOutlined />} onClick={() => fetch()}>
                    刷新
                  </Button>
                  <Button icon={<DownloadOutlined />} onClick={handleExport}>
                    导出
                  </Button>
                  <Button onClick={resetFilters}>重置</Button>
                  <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
                    新增
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>

          {selectedCount > 0 && (
            <div className="supplier-batch-bar">
              <Space wrap>
                <StatusTag tone="info">已选 {selectedCount} 家供应商</StatusTag>
                <Popconfirm
                  title={`确定删除选中的 ${selectedCount} 个供应商?`}
                  onConfirm={handleBatchDelete}
                >
                  <Button danger icon={<DeleteOutlined />} loading={batchDeleting}>
                    批量删除
                  </Button>
                </Popconfirm>
                <Button onClick={() => setSelectedRowKeys([])}>清空选择</Button>
              </Space>
            </div>
          )}

          <Card bodyStyle={{ padding: 0 }}>
            <Table
              rowKey="id"
              columns={columns}
              dataSource={visibleData}
              loading={loading}
              size="middle"
              rowSelection={{
                selectedRowKeys,
                onChange: (keys) => setSelectedRowKeys(keys as number[]),
              }}
              rowClassName={(record) =>
                activeSupplier?.id === record.id ? "supplier-row-selected" : ""
              }
              onRow={(record) => ({
                onClick: () => setActiveSupplierId(record.id),
              })}
              locale={{
                emptyText: (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无供应商数据" />
                ),
              }}
              scroll={{ x: 1260 }}
              pagination={erpPagination({
                current: page,
                total: task === "all" ? total : visibleData.length,
                pageSize,
                onChange: (p, ps) => { setPage(ps !== pageSize ? 1 : p); setPageSize(ps); },
              })}
            />
          </Card>
        </main>

        <aside className="supplier-context">
          <div className="supplier-panel">
            <div className="supplier-panel-head">
              <Space size={6}>
                <BankOutlined />
                <Text strong>供应商上下文</Text>
              </Space>
              {activeAction && (
                <StatusTag tone={activeAction.color}>{activeAction.label}</StatusTag>
              )}
            </div>
            {!activeSupplier ? (
              <div className="supplier-panel-body">
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择供应商查看上下文" />
              </div>
            ) : (
              <div className="supplier-panel-body">
                <div className="supplier-context-title">
                  <div>
                    <a
                      style={{ fontWeight: 600 }}
                      onClick={() => navigate(`/suppliers/${activeSupplier.id}`)}
                    >
                      {activeSupplier.name}
                    </a>
                    <div className="supplier-context-note">
                      {normalizeSupplierType(activeSupplier.supplier_type) || "未分类"} ·{" "}
                      {activeSupplier.region || "未维护区域"}
                    </div>
                  </div>
                  {activeSupplier.financial_rating && (
                    <StatusTag tone="success">{activeSupplier.financial_rating}</StatusTag>
                  )}
                </div>
                <Space size={[4, 6]} wrap style={{ marginTop: 10 }}>
                  {activeSupplier.contact_person && (
                    <StatusTag>{activeSupplier.contact_person}</StatusTag>
                  )}
                  {activeSupplier.phone && (
                    <StatusTag tone="info">{activeSupplier.phone}</StatusTag>
                  )}
                  {activeSupplier.email && (
                    <StatusTag tone="info">{activeSupplier.email}</StatusTag>
                  )}
                </Space>
                <div className="supplier-context-score">
                  <div>
                    <Text type="secondary">完整度</Text>
                    <span className="supplier-context-number">
                      {getSupplierCompletion(activeSupplier)}%
                    </span>
                  </div>
                  <div>
                    <Text type="secondary">缺字段</Text>
                    <span className="supplier-context-number">
                      {getMissingFields(activeSupplier).length}
                    </span>
                  </div>
                </div>
                <div className="supplier-context-action">
                  <Text strong>建议动作</Text>
                  <div style={{ marginTop: 6 }}>
                    {activeAction && (
                      <StatusTag tone={activeAction.color}>{activeAction.label}</StatusTag>
                    )}
                  </div>
                  <div className="supplier-context-note" style={{ marginTop: 6 }}>
                    {activeAction?.note}
                  </div>
                </div>
                <Descriptions column={1} size="small" style={{ marginTop: 10 }}>
                  <Descriptions.Item label="产品线">
                    {activeSupplier.product_lines || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="付款条件">
                    {activeSupplier.payment_terms || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="认证">
                    {activeSupplier.certifications || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="官网">
                    {activeSupplier.website ? (
                      <a href={activeSupplier.website} target="_blank" rel="noreferrer">
                        {activeSupplier.website}
                      </a>
                    ) : (
                      "-"
                    )}
                  </Descriptions.Item>
                </Descriptions>
                {getMissingFields(activeSupplier).length > 0 && (
                  <div className="supplier-context-note">
                    缺少：{getMissingFields(activeSupplier).join("、")}
                  </div>
                )}
                <Space direction="vertical" style={{ width: "100%", marginTop: 10 }}>
                  <Button
                    block
                    type="primary"
                    icon={<EyeOutlined />}
                    onClick={() => navigate(`/suppliers/${activeSupplier.id}`)}
                  >
                    打开详情
                  </Button>
                  <Button block icon={<EditOutlined />} onClick={() => openEdit(activeSupplier)}>
                    编辑主数据
                  </Button>
                  <Button
                    block
                    icon={<ToolOutlined />}
                    onClick={() => navigate(`/suppliers/${activeSupplier.id}/360`)}
                  >
                    供应商 360
                  </Button>
                </Space>
              </div>
            )}
          </div>

          <div className="supplier-panel">
            <div className="supplier-panel-head">
              <Space size={6}>
                <GlobalOutlined />
                <Text strong>当前视图</Text>
              </Space>
            </div>
            <div className="supplier-panel-body">
              <Space size={[4, 6]} wrap>
                <StatusTag>{TASK_LABELS[task]}</StatusTag>
                {supplierType && <StatusTag tone="info">类型：{supplierType}</StatusTag>}
                {search.trim() && <StatusTag tone="info">搜索：{search.trim()}</StatusTag>}
                <StatusTag>显示 {visibleData.length}</StatusTag>
              </Space>
            </div>
          </div>
        </aside>
      </div>

      <SupplierFormModal
        title="新增供应商"
        open={createOpen}
        form={createForm}
        confirmLoading={creating}
        okText="创建"
        onCancel={() => {
          setCreateOpen(false);
          createForm.resetFields();
        }}
        onOk={handleCreate}
      />

      <SupplierFormModal
        title="编辑供应商"
        open={editOpen}
        form={editForm}
        confirmLoading={editing}
        okText="保存"
        onCancel={() => {
          setEditOpen(false);
          editForm.resetFields();
          setEditRecord(null);
        }}
        onOk={handleEdit}
      />
    </div>
  );
}

function SupplierFormModal({
  title,
  open,
  form,
  confirmLoading,
  okText,
  onCancel,
  onOk,
}: {
  title: string;
  open: boolean;
  form: ReturnType<typeof Form.useForm>[0];
  confirmLoading: boolean;
  okText: string;
  onCancel: () => void;
  onOk: () => void;
}) {
  return (
    <Modal
      title={title}
      open={open}
      onCancel={onCancel}
      onOk={onOk}
      confirmLoading={confirmLoading}
      okText={okText}
      width={720}
    >
      <Form form={form} layout="vertical">
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
              <Input placeholder="供应商名称" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="supplier_type" label="供应商类型">
              <Select
                placeholder="选择类型"
                allowClear
                options={SUPPLIER_TYPES.map((t) => ({ value: t, label: t }))}
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={12}>
          <Col span={8}>
            <Form.Item name="contact_person" label="联系人">
              <Input />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="phone" label="电话">
              <Input />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="email" label="邮箱">
              <Input />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item name="region" label="区域">
              <Input />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="financial_rating" label="财务评级">
              <Input placeholder="A/B/C 或自定义评级" />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="address" label="地址">
          <Input />
        </Form.Item>
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item name="payment_terms" label="付款条件">
              <Input placeholder="月结30天/预付等" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="website" label="官网">
              <Input placeholder="https://..." />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="certifications" label="认证">
          <Input.TextArea rows={2} placeholder="ISO、授权资质、代理证书等" />
        </Form.Item>
        <Form.Item name="product_lines" label="产品线">
          <Input.TextArea rows={3} placeholder="描述供应商经营的产品线" />
        </Form.Item>
        <Form.Item name="notes" label="备注">
          <Input.TextArea rows={2} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
