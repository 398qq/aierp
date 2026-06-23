import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Table, Button, Input, Space, message, Card, Modal, Form, Tag, Popconfirm, Typography, Select, Tabs, Row, Col, Switch, Progress, Tooltip, Segmented, Alert } from "antd";
import { StatusTag } from "../../ui";
import { BankOutlined, PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, ImportOutlined, DownOutlined, DownloadOutlined, RobotOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getBrands, createBrand, updateBrand, deleteBrand, importBrandFromText, batchUpdateBrands, batchDeleteBrands, getBrandStats, getApiErrorMessage } from "../../api";
import type { Brand } from "../../types";
import { getBatchAiSummary, getBrandNextAction } from "./brandAiOrchestration";

const { Text, Title } = Typography;

const STATUS_OPTIONS = [
  { label: "启用", value: "active" },
  { label: "停用", value: "inactive" },
  { label: "冻结", value: "frozen" },
];
const LEVEL_OPTIONS = [
  { label: "A级", value: "A" },
  { label: "B级", value: "B" },
  { label: "C级", value: "C" },
];
const TYPE_OPTIONS = [
  { label: "自有品牌", value: "own_brand" },
  { label: "代理品牌", value: "agency" },
  { label: "OEM", value: "oem" },
];
const LIFECYCLE_OPTIONS = [
  { label: "Active", value: "active" },
  { label: "NRND", value: "nrnd" },
  { label: "EOL", value: "eol" },
];
const RISK_OPTIONS = [
  { label: "低", value: "low" },
  { label: "中", value: "medium" },
  { label: "高", value: "high" },
  { label: "严重", value: "critical" },
];
const AUTH_OPTIONS = [
  { label: "已授权", value: "authorized" },
  { label: "未授权", value: "unauthorized" },
  { label: "未知", value: "unknown" },
];
const ROHS_OPTIONS = [
  { label: "合规", value: "compliant" },
  { label: "不合规", value: "non_compliant" },
  { label: "豁免", value: "exempt" },
  { label: "未知", value: "unknown" },
];

const statusColor: Record<string, string> = { active: "green", inactive: "orange", frozen: "red" };
const statusLabel: Record<string, string> = { active: "启用", inactive: "停用", frozen: "冻结" };
const levelColor: Record<string, string> = { A: "red", B: "blue", C: "default" };
const typeLabel: Record<string, string> = { own_brand: "自有", agency: "代理", oem: "OEM" };
const riskTagColor: Record<string, string> = { low: "green", medium: "orange", high: "red", critical: "purple" };
const lcTagColor: Record<string, string> = { active: "green", nrnd: "orange", eol: "red" };
type BrandScene = "all" | "high_risk" | "eol_nrnd" | "pending_completion" | "no_products" | "automotive" | "unauthorized";

const SCENE_OPTIONS: { label: string; value: BrandScene }[] = [
  { label: "全部", value: "all" },
  { label: "高风险", value: "high_risk" },
  { label: "EOL/NRND", value: "eol_nrnd" },
  { label: "待完善", value: "pending_completion" },
  { label: "未铺货", value: "no_products" },
  { label: "车规", value: "automotive" },
  { label: "未授权", value: "unauthorized" },
];

const SORT_OPTIONS = [
  { label: "最新创建", value: "created_at_desc" },
  { label: "名称升序", value: "name_asc" },
  { label: "名称降序", value: "name_desc" },
  { label: "风险最高", value: "risk_score_desc" },
  { label: "产品最多", value: "product_count_desc" },
];

interface BrandStats {
  total: number; recent_30d: number; eol_nrnd_count: number;
  automotive_count: number; high_risk_count: number;
  pending_completion_count?: number; no_product_count?: number;
  by_status: { status: string; count: number }[];
  by_level: { level: string; count: number }[];
  by_risk: { level: string; count: number }[];
  by_lifecycle: { stage: string; count: number }[];
}

export default function BrandList() {
  const [data, setData] = useState<Brand[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Brand | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const [importLoading, setImportLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterLevel, setFilterLevel] = useState<string | undefined>();
  const [filterType, setFilterType] = useState<string | undefined>();
  const [filterLifecycle, setFilterLifecycle] = useState<string | undefined>();
  const [filterRisk, setFilterRisk] = useState<string | undefined>();
  const [scene, setScene] = useState<BrandScene>("all");
  const [sort, setSort] = useState("created_at_desc");
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchField, setBatchField] = useState<string>("");
  const [batchValue, setBatchValue] = useState<string>("");
  const [batchSubmitting, setBatchSubmitting] = useState(false);
  const [aiPlanOpen, setAiPlanOpen] = useState(false);
  const [stats, setStats] = useState<BrandStats | null>(null);
  const [activeBrandId, setActiveBrandId] = useState<number | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  const fetch = async (p = page, ps = pageSize, keyword = search) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: ps };
      if (keyword) params.q = keyword;
      if (filterStatus) params.status = filterStatus;
      if (filterLevel) params.level = filterLevel;
      if (filterType) params.brand_type = filterType;
      if (filterLifecycle) params.lifecycle_stage = filterLifecycle;
      if (filterRisk) params.risk_level = filterRisk;
      if (scene !== "all") params.scene = scene;
      if (sort) params.sort = sort;
      const resp = await getBrands(params);
      const d = resp.data.data as { list: Brand[]; total: number };
      setData(d.list || []);
      setTotal(d.total || 0);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载品牌失败")); }
    finally { setLoading(false); }
  };

  const fetchStats = async () => {
    try {
      const resp = await getBrandStats();
      setStats(resp.data.data as unknown as BrandStats);
    } catch { /* non-blocking */ }
  };

  useEffect(() => { fetch(); fetchStats(); }, [page, pageSize, filterStatus, filterLevel, filterType, filterLifecycle, filterRisk, scene, sort]);
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    setSearch(params.get("q") || params.get("keyword") || "");
    setFilterStatus(params.get("status") || undefined);
    setFilterLevel(params.get("level") || undefined);
    setFilterType(params.get("brand_type") || undefined);
    setFilterLifecycle(params.get("lifecycle_stage") || undefined);
    setFilterRisk(params.get("risk_level") || undefined);
    setScene((params.get("scene") as BrandScene) || "all");
    setSort(params.get("sort") || "created_at_desc");
    setPage(1);
  }, [location.search]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (page !== 1) {
        setPage(1);
      } else {
        fetch(1, pageSize, search);
      }
    }, 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ status: "active", is_automotive: false });
    setModalOpen(true);
  };

  const openEdit = (b: Brand) => {
    setEditing(b);
    form.setFieldsValue(b);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      if (editing) {
        await updateBrand(editing.id, form.getFieldsValue());
        message.success("更新成功");
      } else {
        await createBrand(form.getFieldsValue());
        message.success("创建成功");
      }
      setModalOpen(false);
      fetch();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "操作失败")); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteBrand(id);
      message.success("删除成功");
      fetch();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
  };

  const handleImport = async () => {
    setImportLoading(true);
    try {
      const resp = await importBrandFromText(importText, true);
      const d = resp.data.data as unknown as Record<string, unknown>;
      if (d.created_id) {
        message.success(`已创建品牌: ${d.name}`);
        navigate(`/brands/${d.created_id}`);
      } else {
        message.success(`已解析: ${d.name}`);
      }
      setImportOpen(false);
      setImportText("");
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "导入失败")); }
    finally { setImportLoading(false); }
  };

  const handleBatchUpdate = async () => {
    if (!batchField || !batchValue || selectedRowKeys.length === 0) {
      message.error("请选择字段和值");
      return;
    }
    setBatchSubmitting(true);
    try {
      await batchUpdateBrands(selectedRowKeys as number[], { [batchField]: batchValue });
      message.success(`已更新 ${selectedRowKeys.length} 个品牌`);
      setBatchModalOpen(false);
      setBatchField("");
      setBatchValue("");
      setSelectedRowKeys([]);
      fetch();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "批量更新失败")); }
    finally { setBatchSubmitting(false); }
  };

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) return;
    setBatchSubmitting(true);
    try {
      await batchDeleteBrands(selectedRowKeys as number[]);
      message.success(`已删除 ${selectedRowKeys.length} 个品牌`);
      setSelectedRowKeys([]);
      fetch();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "批量删除失败")); }
    finally { setBatchSubmitting(false); }
  };

  const resetFilters = () => {
    setSearch("");
    setFilterStatus(undefined);
    setFilterLevel(undefined);
    setFilterType(undefined);
    setFilterLifecycle(undefined);
    setFilterRisk(undefined);
    setScene("all");
    setSort("created_at_desc");
    setPage(1);
  };

  const exportCurrentPage = () => {
    if (!data.length) {
      message.warning("当前无可导出数据");
      return;
    }
    const headers = ["编码", "名称", "中文名", "状态", "类型", "等级", "生命周期", "风险", "风险分", "完整度", "产品数", "授权", "负责人", "产品线"];
    const rows = data.map((b) => [
      b.code || "",
      b.name || "",
      b.name_cn || "",
      statusLabel[b.status] || b.status || "",
      b.brand_type ? typeLabel[b.brand_type] || b.brand_type : "",
      b.level || "",
      b.lifecycle_stage || "",
      b.risk_level || "",
      b.risk_score ?? "",
      b.completion_score ?? "",
      b.product_count ?? 0,
      b.authorization_status || "",
      b.owner || "",
      b.product_lines || "",
    ]);
    const csv = [headers, ...rows].map((row) => row.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "brands_current_page.csv";
    a.click();
    URL.revokeObjectURL(url);
    message.success(`已导出 ${data.length} 条`);
  };

  const getBrandAction = (brand: Brand) => {
    const action = getBrandNextAction(brand);
    return <StatusTag tone={action.color}>{action.label}</StatusTag>;
  };

  const columns: ColumnsType<Brand> = [
    { title: "ID", dataIndex: "id", width: 50 },
    { title: "编码", dataIndex: "code", width: 80, render: (v) => v || "-" },
    {
      title: "名称", dataIndex: "name", width: 160,
      render: (v, r) => <a onClick={() => navigate(`/brands/${r.id}`)}>{v}</a>,
    },
    { title: "中文名", dataIndex: "name_cn", width: 100, render: (v) => v || "-" },
    {
      title: "状态", dataIndex: "status", width: 70,
      render: (v) => <StatusTag tone={statusColor[v] || "neutral"}>{statusLabel[v] || v}</StatusTag>,
    },
    {
      title: "类型", dataIndex: "brand_type", width: 70,
      render: (v) => v ? <StatusTag>{typeLabel[v] || v}</StatusTag> : "-",
    },
    {
      title: "等级", dataIndex: "level", width: 60,
      render: (v) => v ? <StatusTag tone={levelColor[v]}>{v}级</StatusTag> : "-",
    },
    {
      title: "生命周期", dataIndex: "lifecycle_stage", width: 80,
      render: (v) => v ? <StatusTag tone={lcTagColor[v] || "neutral"}>{v.toUpperCase()}</StatusTag> : "-",
    },
    {
      title: "风险", dataIndex: "risk_level", width: 70,
      render: (v, r) => v ? (
        <Space size={4}>
          <StatusTag tone={riskTagColor[v] || "neutral"}>{v === "low" ? "低" : v === "medium" ? "中" : v === "high" ? "高" : "严重"}</StatusTag>
          {r.risk_score != null && <Progress percent={r.risk_score} size="small" style={{ width: 40 }} showInfo={false} status={r.risk_score > 70 ? "exception" : "normal"} />}
        </Space>
      ) : "-",
    },
    {
      title: "RoHS", dataIndex: "rohs_status", width: 65,
      render: (v) => v === "compliant" ? <StatusTag tone="success">合规</StatusTag> : v === "exempt" ? <StatusTag tone="warning">豁免</StatusTag> : v === "non_compliant" ? <StatusTag tone="danger">不合规</StatusTag> : "-",
    },
    {
      title: "定位", dataIndex: "positioning", width: 60,
      render: (v) => v === "high" ? <StatusTag tone="success">高端</StatusTag> : v === "mid" ? <StatusTag>中端</StatusTag> : v === "low" ? <StatusTag tone="warning">低端</StatusTag> : "-",
    },
    {
      title: "MOQ", dataIndex: "moq", width: 60, align: "right",
      render: (v) => v != null ? v : "-",
    },
    {
      title: "完整度", dataIndex: "completion_score", width: 95,
      render: (v: number | null, r) => {
        const score = v ?? 0;
        const missing = r.missing_fields?.length ? `缺少：${r.missing_fields.join("、")}` : "资料完整";
        return (
          <Tooltip title={missing}>
            <Progress percent={score} size="small" showInfo={false} strokeColor={score >= 80 ? "#52c41a" : score >= 50 ? "#faad14" : "#ff4d4f"} />
          </Tooltip>
        );
      },
    },
    {
      title: "车规", dataIndex: "is_automotive", width: 55,
      render: (v) => v ? <StatusTag tone="info" style={{padding: "0 4px"}}>车规</StatusTag> : <Text type="secondary">-</Text>,
    },
    {
      title: "授权", dataIndex: "authorization_status", width: 70,
      render: (v) => v ? <StatusTag tone={v === "authorized" ? "success" : v === "unauthorized" ? "danger" : "neutral"}>{v === "authorized" ? "已授权" : v === "unauthorized" ? "未授权" : "未知"}</StatusTag> : "-",
    },
    {
      title: "产品", dataIndex: "product_count", width: 55,
      render: (v) => v != null && v > 0 ? <Text style={{ fontSize: 12 }}>{v}</Text> : <StatusTag tone="warning">未铺货</StatusTag>,
    },
    {
      title: "建议", key: "next_action", width: 90,
      render: (_: unknown, r) => getBrandAction(r),
    },
    {
      title: "操作", key: "action", width: 120, fixed: "right",
      render: (_: unknown, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
  };

  const applyScene = (nextScene: BrandScene) => {
    setScene(nextScene);
    setPage(1);
  };

  const activeFilterTags = [
    search ? { key: "search", label: `搜索: ${search}`, onClose: () => { setSearch(""); setPage(1); } } : null,
    filterStatus ? { key: "status", label: `状态: ${STATUS_OPTIONS.find((o) => o.value === filterStatus)?.label || filterStatus}`, onClose: () => { setFilterStatus(undefined); setPage(1); } } : null,
    filterLevel ? { key: "level", label: `等级: ${LEVEL_OPTIONS.find((o) => o.value === filterLevel)?.label || filterLevel}`, onClose: () => { setFilterLevel(undefined); setPage(1); } } : null,
    filterType ? { key: "type", label: `类型: ${TYPE_OPTIONS.find((o) => o.value === filterType)?.label || filterType}`, onClose: () => { setFilterType(undefined); setPage(1); } } : null,
    filterLifecycle ? { key: "lifecycle", label: `生命周期: ${filterLifecycle.toUpperCase()}`, onClose: () => { setFilterLifecycle(undefined); setPage(1); } } : null,
    filterRisk ? { key: "risk", label: `风险: ${RISK_OPTIONS.find((o) => o.value === filterRisk)?.label || filterRisk}`, onClose: () => { setFilterRisk(undefined); setPage(1); } } : null,
    scene !== "all" ? { key: "scene", label: `场景: ${SCENE_OPTIONS.find((o) => o.value === scene)?.label || scene}`, onClose: () => applyScene("all") } : null,
  ].filter((item): item is { key: string; label: string; onClose: () => void } => Boolean(item));
  const hasCustomView = activeFilterTags.length > 0 || sort !== "created_at_desc";
  const startIndex = total > 0 ? (page - 1) * pageSize + 1 : 0;
  const endIndex = Math.min(page * pageSize, total);
  const selectedBrands = data.filter((brand) => selectedRowKeys.includes(brand.id));
  const batchAiSummary = getBatchAiSummary(selectedBrands);
  const activeBrand = useMemo(
    () => data.find((brand) => brand.id === activeBrandId) || data[0] || null,
    [activeBrandId, data],
  );
  const activeBrandAction = activeBrand ? getBrandNextAction(activeBrand) : null;
  const operationTasks = useMemo(() => {
    if (!stats) return [];
    return [
      { key: "high_risk" as BrandScene, label: "高风险复核", count: stats.high_risk_count, color: "red", note: "风险评分或风险等级异常" },
      { key: "eol_nrnd" as BrandScene, label: "生命周期处理", count: stats.eol_nrnd_count, color: "orange", note: "EOL/NRND 替代与库存影响" },
      { key: "pending_completion" as BrandScene, label: "资料补全", count: stats.pending_completion_count ?? 0, color: "gold", note: "主数据字段仍不完整" },
      { key: "no_products" as BrandScene, label: "铺货规划", count: stats.no_product_count ?? 0, color: "blue", note: "尚未关联产品" },
      { key: "automotive" as BrandScene, label: "车规品牌", count: stats.automotive_count, color: "geekblue", note: "车规认证和交期跟踪" },
    ];
  }, [stats]);
  const healthMetrics = useMemo(() => {
    const totalCount = stats?.total || 0;
    const pct = (value: number) => totalCount > 0 ? Math.round((value / totalCount) * 100) : 0;
    return {
      highRiskRate: pct(stats?.high_risk_count || 0),
      lifecycleRate: pct(stats?.eol_nrnd_count || 0),
      automotiveRate: pct(stats?.automotive_count || 0),
      noProductRate: pct(stats?.no_product_count || 0),
    };
  }, [stats]);

  return (
    <div className="brand-page">
      <style>{`
        .brand-page {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .brand-command-strip {
          display: grid;
          grid-template-columns: 1.5fr repeat(4, minmax(120px, .75fr));
          gap: 10px;
          align-items: stretch;
        }
        .brand-command-main,
        .brand-command-metric,
        .brand-ops-panel,
        .brand-context-panel {
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .brand-command-main {
          padding: 16px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          min-height: 116px;
        }
        .brand-command-title {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 6px;
        }
        .brand-command-title h4 {
          margin: 0;
        }
        .brand-command-note {
          max-width: 620px;
        }
        .brand-command-actions {
          margin-top: 12px;
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .brand-command-metric {
          padding: 14px;
          min-height: 116px;
          cursor: pointer;
          transition: border-color .16s ease, box-shadow .16s ease;
        }
        .brand-command-metric:hover {
          border-color: #91caff;
          box-shadow: 0 2px 8px rgba(22, 119, 255, .1);
        }
        .brand-metric-label {
          display: block;
          font-size: 12px;
          margin-bottom: 10px;
        }
        .brand-metric-value {
          display: flex;
          align-items: baseline;
          gap: 6px;
          font-size: 24px;
          font-weight: 700;
          line-height: 1;
        }
        .brand-metric-value small {
          font-size: 12px;
          font-weight: 400;
          color: rgba(0,0,0,.45);
        }
        .brand-workbench-grid {
          display: grid;
          grid-template-columns: 240px minmax(0, 1fr) 280px;
          gap: 12px;
          align-items: start;
        }
        .brand-ops-panel,
        .brand-context-panel {
          padding: 12px;
          position: sticky;
          top: 76px;
        }
        .brand-panel-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          margin-bottom: 10px;
        }
        .brand-task-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .brand-task-item {
          width: 100%;
          padding: 10px;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          background: #fafafa;
          cursor: pointer;
          transition: border-color .16s ease, background .16s ease;
        }
        .brand-task-item:hover,
        .brand-task-item-active {
          border-color: #1677ff;
          background: #f0f7ff;
        }
        .brand-task-main {
          display: flex;
          justify-content: space-between;
          gap: 8px;
          align-items: center;
          margin-bottom: 4px;
        }
        .brand-task-note,
        .brand-context-note {
          font-size: 12px;
          color: rgba(0,0,0,.45);
        }
        .brand-table-zone {
          min-width: 0;
        }
        .brand-context-body {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .brand-context-title {
          display: flex;
          justify-content: space-between;
          gap: 8px;
          align-items: flex-start;
        }
        .brand-context-name {
          min-width: 0;
        }
        .brand-context-name a {
          font-weight: 600;
        }
        .brand-context-score {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }
        .brand-context-score > div {
          padding: 10px;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          background: #fafafa;
        }
        .brand-context-number {
          display: block;
          margin-top: 4px;
          font-size: 20px;
          font-weight: 700;
        }
        .brand-context-action {
          padding: 10px;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          background: #fafafa;
        }
        .brand-row-active td {
          background: #e6f4ff !important;
        }
        .brand-row-critical td { background: #fff2f0 !important; }
        .brand-row-eol td { background: #fff7e6 !important; }
        .brand-stat-card {
          text-align: center;
          cursor: pointer;
          border-color: #f0f0f0;
          transition: border-color .16s ease, box-shadow .16s ease, transform .16s ease;
        }
        .brand-stat-card:hover {
          border-color: #91caff;
          box-shadow: 0 2px 8px rgba(22, 119, 255, .12);
          transform: translateY(-1px);
        }
        .brand-stat-card-active {
          border-color: #1677ff;
          background: #f0f7ff;
        }
        .brand-list-card .ant-card-head {
          align-items: flex-start;
          gap: 8px;
        }
        .brand-list-card .ant-card-extra {
          margin-inline-start: 0;
        }
        .brand-toolbar {
          margin-bottom: 12px;
          padding: 12px;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .brand-toolbar-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          align-items: center;
          justify-content: space-between;
        }
        .brand-scene-switch {
          max-width: 100%;
          overflow-x: auto;
        }
        .brand-filter-row {
          margin-top: 10px;
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          align-items: center;
        }
        .brand-filter-search {
          flex: 1 1 280px;
          max-width: 360px;
          min-width: 220px;
        }
        .brand-filter-select {
          flex: 0 1 120px;
          min-width: 104px;
        }
        .brand-filter-tags {
          margin-top: 10px;
          min-height: 22px;
        }
        .brand-table-meta {
          margin-bottom: 10px;
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          align-items: center;
          justify-content: space-between;
        }
        .brand-empty {
          padding: 28px 8px;
        }
        .brand-ai-plan-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
        }
        .brand-ai-plan-item {
          padding: 10px;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .brand-ai-plan-label {
          display: block;
          margin-bottom: 4px;
          font-size: 12px;
        }
        @media (max-width: 768px) {
          .brand-command-strip {
            grid-template-columns: 1fr;
          }
          .brand-workbench-grid {
            grid-template-columns: 1fr;
          }
          .brand-ops-panel,
          .brand-context-panel {
            position: static;
          }
          .brand-list-card .ant-card-head {
            display: block;
          }
          .brand-list-card .ant-card-extra {
            margin-top: 10px;
          }
          .brand-toolbar-row {
            align-items: stretch;
          }
          .brand-toolbar-row > * {
            width: 100%;
          }
          .brand-filter-search,
          .brand-filter-select {
            flex-basis: 100%;
            max-width: none;
          }
          .brand-ai-plan-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
      <div className="brand-command-strip">
        <div className="brand-command-main">
          <div>
            <div className="brand-command-title">
              <BankOutlined />
              <Title level={4}>品牌管理</Title>
            </div>
            <Text type="secondary" className="brand-command-note">
              统一维护品牌主数据、风险、生命周期、授权和产品覆盖，优先处理高风险与资料缺口。
            </Text>
          </div>
          <div className="brand-command-actions">
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增品牌</Button>
            <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>AI 导入</Button>
            <Button icon={<DownOutlined />} onClick={() => navigate("/brands/stats")}>品牌看板</Button>
          </div>
        </div>
        <div className="brand-command-metric" onClick={() => applyScene("all")}>
          <Text type="secondary" className="brand-metric-label">品牌总数</Text>
          <span className="brand-metric-value">{stats?.total ?? 0}<small>个</small></span>
        </div>
        <div className="brand-command-metric" onClick={() => applyScene("high_risk")}>
          <Text type="secondary" className="brand-metric-label">高风险占比</Text>
          <span className="brand-metric-value">{healthMetrics.highRiskRate}<small>%</small></span>
        </div>
        <div className="brand-command-metric" onClick={() => applyScene("eol_nrnd")}>
          <Text type="secondary" className="brand-metric-label">生命周期风险</Text>
          <span className="brand-metric-value">{healthMetrics.lifecycleRate}<small>%</small></span>
        </div>
        <div className="brand-command-metric" onClick={() => applyScene("no_products")}>
          <Text type="secondary" className="brand-metric-label">未铺货占比</Text>
          <span className="brand-metric-value">{healthMetrics.noProductRate}<small>%</small></span>
        </div>
      </div>

      <div className="brand-workbench-grid">
        <aside className="brand-ops-panel">
          <div className="brand-panel-head">
            <Text strong>运营队列</Text>
            <Button size="small" type="link" onClick={() => navigate("/brands/stats")}>看板</Button>
          </div>
          <div className="brand-task-list">
            {operationTasks.map((item) => (
              <div
                key={item.key}
                className={`brand-task-item${scene === item.key ? " brand-task-item-active" : ""}`}
                onClick={() => applyScene(item.key)}
              >
                <div className="brand-task-main">
                  <Text strong>{item.label}</Text>
                  <StatusTag tone={item.color}>{item.count}</StatusTag>
                </div>
                <div className="brand-task-note">{item.note}</div>
              </div>
            ))}
          </div>
        </aside>

        <main className="brand-table-zone">

      <Card
        className="brand-list-card"
        title={
          <Space>
            品牌列表
            {selectedRowKeys.length > 0 && (
              <StatusTag tone="info">{selectedRowKeys.length} 已选</StatusTag>
            )}
          </Space>
        }
        extra={
          <Space wrap>
            <Button icon={<DownOutlined />} onClick={() => navigate("/brands/stats")}>看板</Button>
            <Button icon={<DownloadOutlined />} onClick={exportCurrentPage}>导出</Button>
            <Button icon={<ReloadOutlined />} onClick={() => { fetch(); fetchStats(); }}>刷新</Button>
            <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>AI 导入</Button>
            {selectedRowKeys.length > 0 && (
              <>
                <Button icon={<RobotOutlined />} onClick={() => setAiPlanOpen(true)}>AI 编排</Button>
                <Button icon={<EditOutlined />} onClick={() => setBatchModalOpen(true)}>批量更新</Button>
                <Popconfirm title={`确认删除选中的 ${selectedRowKeys.length} 个品牌？`} onConfirm={handleBatchDelete}>
                  <Button danger icon={<DeleteOutlined />}>批量删除</Button>
                </Popconfirm>
              </>
            )}
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增</Button>
          </Space>
        }
      >
        <div className="brand-toolbar">
          <div className="brand-toolbar-row">
            <Segmented
              className="brand-scene-switch"
              options={SCENE_OPTIONS}
              value={scene}
              onChange={(v) => applyScene(v as BrandScene)}
            />
            <Space wrap>
              <Select value={sort} style={{ width: 120 }} onChange={(v) => { setSort(v); setPage(1); }} options={SORT_OPTIONS} />
              <Button onClick={resetFilters}>重置</Button>
            </Space>
          </div>
          <div className="brand-filter-row">
            <Input.Search
              placeholder="搜索品牌、产品线、关键词"
              allowClear
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onSearch={(v) => {
                setSearch(v);
                if (page !== 1) setPage(1);
                else fetch(1, pageSize, v);
              }}
              className="brand-filter-search"
            />
            <Select className="brand-filter-select" placeholder="状态" allowClear value={filterStatus} onChange={setFilterStatus} options={STATUS_OPTIONS} />
            <Select className="brand-filter-select" placeholder="等级" allowClear value={filterLevel} onChange={setFilterLevel} options={LEVEL_OPTIONS} />
            <Select className="brand-filter-select" placeholder="类型" allowClear value={filterType} onChange={setFilterType} options={TYPE_OPTIONS} />
            <Select className="brand-filter-select" placeholder="生命周期" allowClear value={filterLifecycle} onChange={setFilterLifecycle} options={LIFECYCLE_OPTIONS} />
            <Select className="brand-filter-select" placeholder="风险" allowClear value={filterRisk} onChange={setFilterRisk} options={RISK_OPTIONS} />
          </div>
          <div className="brand-filter-tags">
            {activeFilterTags.length > 0 ? (
              <Space wrap>
                {activeFilterTags.map((item) => (
                  <StatusTag key={item.key} tone="info" closable onClose={item.onClose}>
                    {item.label}
                  </StatusTag>
                ))}
              </Space>
            ) : (
              <Text type="secondary">当前显示全部品牌</Text>
            )}
          </div>
        </div>
        <div className="brand-table-meta">
          <Text type="secondary">
            {total > 0 ? `显示 ${startIndex}-${endIndex} / 共 ${total} 个品牌` : "暂无品牌数据"}
          </Text>
          <Space wrap size={6}>
            {sort !== "created_at_desc" && <StatusTag tone="info">排序: {SORT_OPTIONS.find((o) => o.value === sort)?.label || sort}</StatusTag>}
            {hasCustomView && <Button size="small" onClick={resetFilters}>清空视图</Button>}
          </Space>
        </div>
        <Table
          rowKey="id" columns={columns} dataSource={data}
          rowSelection={rowSelection}
          rowClassName={(record) => {
            if (activeBrand?.id === record.id) return "brand-row-active";
            if (record.risk_level === "critical" || (record.risk_score ?? 0) >= 80) return "brand-row-critical";
            if (record.lifecycle_stage === "eol") return "brand-row-eol";
            return "";
          }}
          onRow={(record) => ({
            onClick: () => setActiveBrandId(record.id),
          })}
          loading={loading} size="small" pagination={{
            current: page, total, pageSize: pageSize,
            pageSizeOptions: ["10", "20", "50", "100"],
            showSizeChanger: true, showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
          }}
          locale={{
            emptyText: (
              <div className="brand-empty">
                <Text strong>{hasCustomView ? "没有匹配的品牌" : "还没有品牌"}</Text>
                <br />
                <Text type="secondary">{hasCustomView ? "调整筛选条件后再查看" : "点击右上角新增或使用 AI 导入创建品牌"}</Text>
              </div>
            ),
          }}
          scroll={{ x: 1300 }}
        />
      </Card>
        </main>

        <aside className="brand-context-panel">
          <div className="brand-panel-head">
            <Text strong>品牌上下文</Text>
            {activeBrand && <StatusTag tone={activeBrandAction?.color}>{activeBrandAction?.label}</StatusTag>}
          </div>
          {activeBrand ? (
            <div className="brand-context-body">
              <div className="brand-context-title">
                <div className="brand-context-name">
                  <a onClick={() => navigate(`/brands/${activeBrand.id}`)}>{activeBrand.name}</a>
                  <div className="brand-context-note">{activeBrand.name_cn || activeBrand.code || "未补充中文名/编码"}</div>
                </div>
                {activeBrand.level && <StatusTag tone={levelColor[activeBrand.level]}>{activeBrand.level}级</StatusTag>}
              </div>
              <Space wrap size={6}>
                {activeBrand.status && <StatusTag tone={statusColor[activeBrand.status] || "neutral"}>{statusLabel[activeBrand.status] || activeBrand.status}</StatusTag>}
                {activeBrand.brand_type && <StatusTag>{typeLabel[activeBrand.brand_type] || activeBrand.brand_type}</StatusTag>}
                {activeBrand.lifecycle_stage && <StatusTag tone={lcTagColor[activeBrand.lifecycle_stage] || "neutral"}>{activeBrand.lifecycle_stage.toUpperCase()}</StatusTag>}
                {activeBrand.is_automotive && <StatusTag tone="info">车规</StatusTag>}
              </Space>
              <div className="brand-context-score">
                <div>
                  <Text type="secondary">风险分</Text>
                  <span className="brand-context-number">{activeBrand.risk_score ?? "-"}</span>
                </div>
                <div>
                  <Text type="secondary">完整度</Text>
                  <span className="brand-context-number">{activeBrand.completion_score ?? 0}%</span>
                </div>
                <div>
                  <Text type="secondary">产品数</Text>
                  <span className="brand-context-number">{activeBrand.product_count ?? 0}</span>
                </div>
                <div>
                  <Text type="secondary">交期</Text>
                  <span className="brand-context-number">{activeBrand.lead_time_days ?? "-"}</span>
                </div>
              </div>
              <div className="brand-context-action">
                <Text strong>建议动作</Text>
                <div style={{ marginTop: 6 }}>
                  {activeBrandAction && <StatusTag tone={activeBrandAction.color}>{activeBrandAction.label}</StatusTag>}
                </div>
                <div className="brand-context-note" style={{ marginTop: 6 }}>
                  {activeBrand.missing_fields?.length
                    ? `缺少 ${activeBrand.missing_fields.slice(0, 4).join("、")}`
                    : activeBrand.product_lines || "资料完整后可进入常规维护"}
                </div>
              </div>
              <Space direction="vertical" style={{ width: "100%" }}>
                <Button block onClick={() => navigate(`/brands/${activeBrand.id}`)}>打开详情</Button>
                <Button block onClick={() => openEdit(activeBrand)}>编辑主数据</Button>
                <Button block onClick={() => { setSelectedRowKeys([activeBrand.id]); setAiPlanOpen(true); }}>AI 编排</Button>
              </Space>
            </div>
          ) : (
            <Text type="secondary">暂无品牌数据</Text>
          )}
        </aside>
      </div>

      <Modal
        title={editing ? "编辑品牌" : "新增品牌"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        okText={editing ? "保存" : "创建"}
        width={720}
      >
        <Form form={form} layout="vertical">
          <Tabs
            defaultActiveKey="basic"
            items={[
              {
                key: "basic", label: "基础信息",
                children: (
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item name="code" label="编码"><Input placeholder="唯一编码" /></Form.Item>
                    </Col>
                    <Col span={16}>
                      <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入品牌名称" }]}>
                        <Input placeholder="如 TI / STMicroelectronics" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="name_cn" label="中文名"><Input placeholder="如 德州仪器" /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="short_name" label="简称"><Input placeholder="系统显示用" /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="status" label="状态">
                        <Select options={STATUS_OPTIONS} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="brand_type" label="类型">
                        <Select placeholder="选择类型" allowClear options={TYPE_OPTIONS} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="category" label="分类"><Input placeholder="半导体/被动器件" /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="logo" label="Logo URL"><Input placeholder="https://..." /></Form.Item>
                    </Col>
                    <Col span={24}>
                      <Form.Item name="description" label="品牌介绍"><Input.TextArea rows={2} /></Form.Item>
                    </Col>
                    <Col span={24}>
                      <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
                    </Col>
                  </Row>
                ),
              },
              {
                key: "business", label: "商业信息",
                children: (
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item name="level" label="品牌等级"><Select placeholder="选择等级" allowClear options={LEVEL_OPTIONS} /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="positioning" label="品牌定位">
                        <Select placeholder="选择定位" allowClear options={[
                          { label: "高端", value: "high" }, { label: "中端", value: "mid" }, { label: "低端", value: "low" },
                        ]} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="owner" label="负责人"><Input /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="product_lines" label="产品线"><Input.TextArea rows={2} placeholder="MCU, MOS, 连接器..." /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="target_markets" label="目标市场"><Input.TextArea rows={2} placeholder="工业、医疗、车规..." /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="website" label="官网"><Input placeholder="https://..." /></Form.Item>
                    </Col>
                  </Row>
                ),
              },
              {
                key: "supply", label: "供应链",
                children: (
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="manufacturer_name" label="原厂名称"><Input /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="supplier_id" label="关联供应商"><Input type="number" /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="authorization_status" label="授权状态"><Select placeholder="选择" allowClear options={AUTH_OPTIONS} /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="lifecycle_stage" label="生命周期"><Select placeholder="选择" allowClear options={LIFECYCLE_OPTIONS} /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="is_automotive" label="车规" valuePropName="checked"><Switch /></Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="moq" label="MOQ"><Input type="number" /></Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="lead_time_days" label="交期(天)"><Input type="number" /></Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="risk_level" label="风险等级"><Select placeholder="选择" allowClear options={RISK_OPTIONS} /></Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="rohs_status" label="RoHS"><Select placeholder="选择" allowClear options={ROHS_OPTIONS} /></Form.Item>
                    </Col>
                  </Row>
                ),
              },
              {
                key: "ai", label: "AI参数",
                children: (
                  <Row gutter={16}>
                    <Col span={24}>
                      <Form.Item name="ai_keywords" label="AI关键词"><Input.TextArea rows={2} placeholder="逗号分隔，用于AI搜索匹配" /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="risk_score" label="风险评分 (0-100)"><Input type="number" min={0} max={100} /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="alternative_brands" label="替代品牌"><Input.TextArea rows={2} placeholder="逗号分隔品牌名或编码" /></Form.Item>
                    </Col>
                  </Row>
                ),
              },
            ]}
          />
        </Form>
      </Modal>

      <Modal
        title="AI 品牌导入"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        onOk={handleImport}
        confirmLoading={importLoading}
        okText="导入"
      >
        <Text>粘贴品牌描述文本（公司介绍、官网About、供应商目录等），AI 自动提取品牌信息：</Text>
        <Input.TextArea
          rows={6} value={importText}
          onChange={(e) => setImportText(e.target.value)}
          placeholder="例如：意法半导体 (STMicroelectronics) 是全球领先的半导体公司，专注于MCU、电源管理、传感器等产品线..."
          style={{ marginTop: 8 }}
        />
      </Modal>

      <Modal
        title={`批量更新 ${selectedRowKeys.length} 个品牌`}
        open={batchModalOpen}
        onCancel={() => { setBatchModalOpen(false); setBatchField(""); setBatchValue(""); }}
        onOk={handleBatchUpdate}
        confirmLoading={batchSubmitting}
        okText="更新"
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <div>
            <Text strong>选择更新字段：</Text>
            <Select
              style={{ width: "100%", marginTop: 4 }}
              placeholder="选择字段"
              value={batchField}
              onChange={(v) => setBatchField(v)}
              options={[
                { label: "状态", value: "status" },
                { label: "等级", value: "level" },
                { label: "风险等级", value: "risk_level" },
                { label: "生命周期", value: "lifecycle_stage" },
                { label: "授权状态", value: "authorization_status" },
                { label: "RoHS 状态", value: "rohs_status" },
                { label: "品牌定位", value: "positioning" },
                { label: "负责人", value: "owner" },
              ]}
            />
          </div>
          {batchField === "status" && (
            <Select style={{ width: "100%" }} placeholder="选择值" value={batchValue} onChange={setBatchValue} options={STATUS_OPTIONS} />
          )}
          {batchField === "level" && (
            <Select style={{ width: "100%" }} placeholder="选择值" value={batchValue} onChange={setBatchValue} options={LEVEL_OPTIONS} />
          )}
          {batchField === "risk_level" && (
            <Select style={{ width: "100%" }} placeholder="选择值" value={batchValue} onChange={setBatchValue} options={RISK_OPTIONS} />
          )}
          {batchField === "lifecycle_stage" && (
            <Select style={{ width: "100%" }} placeholder="选择值" value={batchValue} onChange={setBatchValue} options={LIFECYCLE_OPTIONS} />
          )}
          {batchField === "authorization_status" && (
            <Select style={{ width: "100%" }} placeholder="选择值" value={batchValue} onChange={setBatchValue} options={AUTH_OPTIONS} />
          )}
          {batchField === "rohs_status" && (
            <Select style={{ width: "100%" }} placeholder="选择值" value={batchValue} onChange={setBatchValue} options={ROHS_OPTIONS} />
          )}
          {batchField === "positioning" && (
            <Select style={{ width: "100%" }} placeholder="选择值" value={batchValue} onChange={setBatchValue} options={[
              { label: "高端", value: "high" }, { label: "中端", value: "mid" }, { label: "低端", value: "low" },
            ]} />
          )}
          {(batchField === "owner" || !["status", "level", "risk_level", "lifecycle_stage", "authorization_status", "rohs_status", "positioning"].includes(batchField)) && (
            <Input placeholder="输入值" value={batchValue} onChange={(e) => setBatchValue(e.target.value)} />
          )}
        </Space>
      </Modal>

      <Modal
        title={`AI 批量编排 ${selectedRowKeys.length} 个品牌`}
        open={aiPlanOpen}
        onCancel={() => setAiPlanOpen(false)}
        footer={[
          <Button key="close" onClick={() => setAiPlanOpen(false)}>关闭</Button>,
          <Button key="risk" onClick={() => { setAiPlanOpen(false); applyScene("high_risk"); }}>查看高风险</Button>,
          <Button key="eol" type="primary" onClick={() => { setAiPlanOpen(false); applyScene("eol_nrnd"); }}>处理生命周期</Button>,
        ]}
      >
        <Space direction="vertical" style={{ width: "100%" }} size={12}>
          <Text type="secondary">基于当前选中品牌的风险、完整度、生命周期、授权和产品覆盖自动生成处理队列。</Text>
          <div className="brand-ai-plan-grid">
            <div className="brand-ai-plan-item">
              <Text type="secondary" className="brand-ai-plan-label">选中品牌</Text>
              <Text strong>{batchAiSummary.total}</Text>
            </div>
            <div className="brand-ai-plan-item">
              <Text type="secondary" className="brand-ai-plan-label">风险复核</Text>
              <StatusTag tone={batchAiSummary.highRisk > 0 ? "danger" : "success"}>{batchAiSummary.highRisk}</StatusTag>
            </div>
            <div className="brand-ai-plan-item">
              <Text type="secondary" className="brand-ai-plan-label">生命周期处理</Text>
              <StatusTag tone={batchAiSummary.lifecycleRisk > 0 ? "warning" : "success"}>{batchAiSummary.lifecycleRisk}</StatusTag>
            </div>
            <div className="brand-ai-plan-item">
              <Text type="secondary" className="brand-ai-plan-label">资料补全</Text>
              <StatusTag tone={batchAiSummary.missingData > 0 ? "processing" : "success"}>{batchAiSummary.missingData}</StatusTag>
            </div>
            <div className="brand-ai-plan-item">
              <Text type="secondary" className="brand-ai-plan-label">铺货规划</Text>
              <StatusTag tone={batchAiSummary.noProducts > 0 ? "info" : "success"}>{batchAiSummary.noProducts}</StatusTag>
            </div>
            <div className="brand-ai-plan-item">
              <Text type="secondary" className="brand-ai-plan-label">授权核验</Text>
              <StatusTag tone={batchAiSummary.unauthorized > 0 ? "volcano" : "success"}>{batchAiSummary.unauthorized}</StatusTag>
            </div>
          </div>
          <Alert
            type="info"
            showIcon
            message="编排建议"
            description="优先处理高风险和 EOL/NRND 品牌；资料补全和铺货规划适合批量分派，授权核验需要人工确认渠道来源。"
          />
        </Space>
      </Modal>
    </div>
  );
}
