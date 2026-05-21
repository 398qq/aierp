import { useEffect, useMemo, useRef, useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Popover,
  Progress,
  Row,
  Segmented,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  message,
} from "antd";
import {
  CheckCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FileTextOutlined,
  InboxOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
  SearchOutlined,
  SettingOutlined,
  StopOutlined,
  ThunderboltOutlined,
  UploadOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import type { SorterResult } from "antd/es/table/interface";
import {
  aiParseBom,
  aiParseProduct,
  aiSearchProducts,
  batchDeleteProducts,
  batchUpdateProducts,
  createProduct,
  deleteProduct,
  getBrands,
  getProduct,
  getProductInventories,
  getProducts,
  getProductSales,
  getProductStats,
  importProducts,
  updateProduct,
  updateProductInventory,
} from "../../api";
import type { Brand, InventoryItem, Product } from "../../types";

type SceneValue = "all" | "in_stock" | "low_stock" | "out_of_stock" | "pending_completion" | "stale_30d";
type BatchTaskType = "update" | "delete" | "export";
type ProductTaskKey = "replenish" | "out" | "complete" | "stale" | "no_supplier" | "ai_search" | "all";

type ProductStats = {
  total: number;
  in_stock_count: number;
  out_of_stock_count: number;
  low_stock_count: number;
  pending_completion_count: number;
  stale_30d_count: number;
};

type SavedView = {
  name: string;
  scene: SceneValue;
  q: string;
  category?: string;
  brandId?: number;
  stockStatus?: string;
  sort: string;
  visibleCols: string[];
};

type ProductSalesData = {
  quotations: Record<string, unknown>[];
  orders: Record<string, unknown>[];
  deliveries: Record<string, unknown>[];
};

const CATEGORIES = ["MLCC", "IC", "电阻", "电容", "连接器", "晶体管", "传感器", "电源管理", "存储", "其他"];
const STOCK_OPTIONS = [
  { value: "", label: "全部" },
  { value: "in_stock", label: "在库" },
  { value: "out_of_stock", label: "缺货" },
  { value: "low_stock", label: "低库存" },
];
const SORT_OPTIONS = [
  { value: "created_at_desc", label: "最新优先" },
  { value: "created_at_asc", label: "最旧优先" },
  { value: "name_asc", label: "名称升序" },
  { value: "name_desc", label: "名称降序" },
];
const SCENE_OPTIONS: { label: string; value: SceneValue }[] = [
  { label: "全部", value: "all" },
  { label: "待补货", value: "low_stock" },
  { label: "缺货", value: "out_of_stock" },
  { label: "待完善", value: "pending_completion" },
  { label: "30天无动销", value: "stale_30d" },
];

const PRODUCT_TASK_LABELS: Record<ProductTaskKey, string> = {
  replenish: "补货预警",
  out: "缺货处理",
  complete: "资料完善",
  stale: "无动销复盘",
  no_supplier: "供应商缺口",
  ai_search: "AI选型搜索",
  all: "全部产品",
};

const COL_LABEL_MAP: Record<string, string> = {
  sku: "SKU",
  name: "产品名称",
  category: "分类",
  package_type: "封装",
  specs: "规格",
  unit: "单位",
  brand_name: "品牌",
  completion_score: "完整度",
  supplier_count: "供应商",
  inventory_location_count: "分仓",
  stock_state: "库存状态",
  quantity: "库存",
  available: "可用",
  locked: "锁定",
  safety_stock: "安全库存",
  unit_price: "单价",
  last_sale_at: "最近销售",
  actions: "操作",
};

const PAGE_SIZE = 20;
const SAVED_VIEW_STORAGE_KEY = "aierp.products.saved_views.v1";

const getAvailableQty = (p: Product) => {
  if (typeof p.available === "number") return p.available;
  return (p.quantity ?? 0) - (p.locked_quantity ?? 0);
};

const getStockState = (p: Product): "in" | "low" | "out" => {
  const available = getAvailableQty(p);
  const safety = p.safety_stock ?? 0;
  if (available <= 0) return "out";
  if (available <= safety) return "low";
  return "in";
};

const getDaysSince = (value?: string | null) => {
  if (!value) return null;
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return null;
  return Math.floor((Date.now() - time) / (24 * 60 * 60 * 1000));
};

const getProductPriorityScore = (product: Product) => {
  let score = 35;
  const stockState = getStockState(product);
  if (stockState === "out") score += 32;
  if (stockState === "low") score += 24;
  if ((product.completion_score ?? 100) < 60) score += 18;
  if ((product.supplier_count ?? 0) <= 0) score += 12;
  if ((product.inventory_location_count ?? 0) <= 0) score += 8;
  const staleDays = getDaysSince(product.last_sale_at);
  if (staleDays == null) score += 8;
  else if (staleDays > 90) score += 16;
  else if (staleDays > 30) score += 8;
  return Math.min(100, score);
};

const getProductSuggestedAction = (product: Product) => {
  const stockState = getStockState(product);
  if (stockState === "out") return "优先确认可替代库存或发起采购补货";
  if (stockState === "low") return "检查安全库存并补充采购计划";
  if ((product.completion_score ?? 100) < 60) return "补齐品牌、封装、规格和资料字段";
  if ((product.supplier_count ?? 0) <= 0) return "补充可供货供应商并维护采购关系";
  const staleDays = getDaysSince(product.last_sale_at);
  if (staleDays == null || staleDays > 30) return "复盘动销，生成客户推荐或清理策略";
  return "维护价格与库存，保持可销售状态";
};

const formatDateTime = (value?: string | null) => {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
};

const exportProductsCsv = (rows: Product[], filename: string) => {
  if (!rows.length) return false;
  const headers = ["SKU", "产品名称", "分类", "封装", "规格", "单位", "品牌", "完整度", "供应商数", "分仓数", "库存", "可用", "锁定", "安全库存", "单价", "最近销售"];
  const body = rows.map((p) => [
    p.sku || "",
    p.name || "",
    p.category || "",
    p.package_type || "",
    p.specs || "",
    p.unit || "",
    p.brand_name || "",
    p.completion_score ?? "",
    p.supplier_count ?? 0,
    p.inventory_location_count ?? 0,
    p.quantity ?? 0,
    getAvailableQty(p),
    p.locked_quantity ?? 0,
    p.safety_stock ?? "",
    p.unit_price != null ? `¥${p.unit_price.toFixed(2)}` : "",
    p.last_sale_at || "",
  ]);
  const csv = [headers, ...body].map((row) => row.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  return true;
};

export default function ProductList() {
  const [data, setData] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [scene, setScene] = useState<SceneValue>("all");
  const [aiSearchMode, setAiSearchMode] = useState(false);
  const [aiSearchResults, setAiSearchResults] = useState<Record<string, unknown>[] | null>(null);
  const [aiSearching, setAiSearching] = useState(false);
  const [category, setCategory] = useState<string | undefined>();
  const [brandId, setBrandId] = useState<number | undefined>();
  const [stockStatus, setStockStatus] = useState<string | undefined>();
  const [sort, setSort] = useState<string>("created_at_desc");
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiText, setAiText] = useState("");
  const [aiParsing, setAiParsing] = useState(false);
  const [bomModalOpen, setBomModalOpen] = useState(false);
  const [bomText, setBomText] = useState("");
  const [bomParsing, setBomParsing] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [batchTaskModalOpen, setBatchTaskModalOpen] = useState(false);
  const [batchTaskType, setBatchTaskType] = useState<BatchTaskType>("update");
  const [batchTaskConfirm, setBatchTaskConfirm] = useState(false);
  const [batchEditForm] = Form.useForm();
  const [batchEditing, setBatchEditing] = useState(false);
  const [saveViewModalOpen, setSaveViewModalOpen] = useState(false);
  const [saveViewName, setSaveViewName] = useState("");
  const [savedViews, setSavedViews] = useState<SavedView[]>([]);
  const [activeSavedView, setActiveSavedView] = useState<string>("");
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailProduct, setDetailProduct] = useState<Product | null>(null);
  const [detailInventories, setDetailInventories] = useState<InventoryItem[]>([]);
  const [detailSales, setDetailSales] = useState<ProductSalesData | null>(null);
  const [quickActionOpen, setQuickActionOpen] = useState(false);
  const [quickActionLoading, setQuickActionLoading] = useState(false);
  const [quickActionSaving, setQuickActionSaving] = useState(false);
  const [quickActionType, setQuickActionType] = useState<"price" | "safety">("price");
  const [quickActionProduct, setQuickActionProduct] = useState<Product | null>(null);
  const [quickInventoryOptions, setQuickInventoryOptions] = useState<InventoryItem[]>([]);
  const [quickInventoryId, setQuickInventoryId] = useState<number | undefined>();
  const [quickValue, setQuickValue] = useState<number | null>(null);
  const [productTask, setProductTask] = useState<ProductTaskKey>("replenish");
  const [contextProductId, setContextProductId] = useState<number | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [stats, setStats] = useState<ProductStats>({
    total: 0,
    in_stock_count: 0,
    out_of_stock_count: 0,
    low_stock_count: 0,
    pending_completion_count: 0,
    stale_30d_count: 0,
  });

  const [form] = Form.useForm();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const allColKeys = [
    "sku",
    "name",
    "category",
    "package_type",
    "specs",
    "unit",
    "brand_name",
    "completion_score",
    "supplier_count",
    "inventory_location_count",
    "stock_state",
    "quantity",
    "available",
    "locked",
    "safety_stock",
    "unit_price",
    "last_sale_at",
    "actions",
  ];
  const [visibleCols, setVisibleCols] = useState<string[]>([...allColKeys]);

  const selectedProducts = useMemo(
    () => data.filter((item) => selectedRowKeys.includes(item.id)),
    [data, selectedRowKeys],
  );

  const selectedMetrics = useMemo(() => {
    const result = { inStock: 0, lowStock: 0, outOfStock: 0 };
    selectedProducts.forEach((item) => {
      const state = getStockState(item);
      if (state === "in") result.inStock += 1;
      if (state === "low") result.lowStock += 1;
      if (state === "out") result.outOfStock += 1;
    });
    return result;
  }, [selectedProducts]);

  const productMatchesTask = (product: Product, task: ProductTaskKey) => {
    const stockState = getStockState(product);
    const staleDays = getDaysSince(product.last_sale_at);
    if (task === "all") return true;
    if (task === "replenish") return stockState === "low";
    if (task === "out") return stockState === "out";
    if (task === "complete") return (product.completion_score ?? 100) < 80 || Boolean(product.missing_fields?.length);
    if (task === "stale") return staleDays == null || staleDays > 30;
    if (task === "no_supplier") return (product.supplier_count ?? 0) <= 0;
    if (task === "ai_search") return getProductPriorityScore(product) >= 65;
    return true;
  };

  const filteredProducts = useMemo(
    () => data
      .filter((item) => productMatchesTask(item, productTask))
      .sort((a, b) => getProductPriorityScore(b) - getProductPriorityScore(a)),
    [data, productTask],
  );

  const productTaskItems = useMemo(() => [
    { key: "replenish" as ProductTaskKey, label: PRODUCT_TASK_LABELS.replenish, count: data.filter((item) => productMatchesTask(item, "replenish")).length, color: "orange", note: "可用库存低于安全线" },
    { key: "out" as ProductTaskKey, label: PRODUCT_TASK_LABELS.out, count: data.filter((item) => productMatchesTask(item, "out")).length, color: "red", note: "当前无可用库存" },
    { key: "complete" as ProductTaskKey, label: PRODUCT_TASK_LABELS.complete, count: data.filter((item) => productMatchesTask(item, "complete")).length, color: "gold", note: "资料字段不完整" },
    { key: "stale" as ProductTaskKey, label: PRODUCT_TASK_LABELS.stale, count: data.filter((item) => productMatchesTask(item, "stale")).length, color: "blue", note: "超过30天无销售" },
    { key: "no_supplier" as ProductTaskKey, label: PRODUCT_TASK_LABELS.no_supplier, count: data.filter((item) => productMatchesTask(item, "no_supplier")).length, color: "purple", note: "未维护供应商" },
    { key: "ai_search" as ProductTaskKey, label: PRODUCT_TASK_LABELS.ai_search, count: data.filter((item) => productMatchesTask(item, "ai_search")).length, color: "cyan", note: "综合优先级较高" },
    { key: "all" as ProductTaskKey, label: PRODUCT_TASK_LABELS.all, count: data.length, color: "default", note: "回到普通清单" },
  ], [data]);

  const tableProducts = useMemo(
    () => aiSearchMode ? ((aiSearchResults ?? []) as unknown as Product[]) : filteredProducts,
    [aiSearchMode, aiSearchResults, filteredProducts],
  );
  const contextProduct = useMemo(
    () => data.find((item) => item.id === contextProductId) || tableProducts[0] || null,
    [contextProductId, data, tableProducts],
  );
  const contextStockState = contextProduct ? getStockState(contextProduct) : "in";
  const contextPriorityScore = contextProduct ? getProductPriorityScore(contextProduct) : 0;
  const contextSuggestedAction = contextProduct ? getProductSuggestedAction(contextProduct) : "";

  const loadSavedViews = () => {
    try {
      const raw = localStorage.getItem(SAVED_VIEW_STORAGE_KEY);
      if (!raw) {
        setSavedViews([]);
        return;
      }
      const parsed = JSON.parse(raw) as SavedView[];
      setSavedViews(Array.isArray(parsed) ? parsed : []);
    } catch {
      setSavedViews([]);
    }
  };

  const persistSavedViews = (next: SavedView[]) => {
    setSavedViews(next);
    localStorage.setItem(SAVED_VIEW_STORAGE_KEY, JSON.stringify(next));
  };

  const loadStats = async () => {
    setStatsLoading(true);
    try {
      const resp = await getProductStats();
      setStats(resp.data.data);
    } catch {
      // no-op
    } finally {
      setStatsLoading(false);
    }
  };

  const fetch = async (nextPage = page, search = q) => {
    if (aiSearchMode) return;
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: nextPage, page_size: PAGE_SIZE, sort };
      if (search) params.q = search;
      if (scene && scene !== "all") params.scene = scene;
      if (category) params.category = category;
      if (brandId) params.brand_id = brandId;
      if (stockStatus) params.stock_status = stockStatus;
      const resp = await getProducts(params);
      const list = (resp.data.data.list || []) as Product[];
      setData(list);
      setTotal(resp.data.data.total || 0);
    } catch {
      message.error("加载产品列表失败");
    } finally {
      setLoading(false);
    }
  };

  const handleAiSearch = async (text: string) => {
    if (!text.trim()) {
      setAiSearchResults(null);
      return;
    }
    setAiSearching(true);
    try {
      const r = await aiSearchProducts(text, 20);
      if (r.data.code === 0) {
        setAiSearchResults(r.data.data as Record<string, unknown>[]);
      } else {
        message.error(r.data.msg || "搜索失败");
      }
    } catch {
      message.error("AI 搜索失败");
    } finally {
      setAiSearching(false);
    }
  };

  const loadBrands = async () => {
    try {
      const r = await getBrands();
      const payload = r.data.data as Brand[] | { list?: Brand[] };
      setBrands(Array.isArray(payload) ? payload : (payload.list || []));
    } catch {
      // no-op
    }
  };

  const resetAllFilters = () => {
    setQ("");
    setScene("all");
    setCategory(undefined);
    setBrandId(undefined);
    setStockStatus(undefined);
    setSort("created_at_desc");
    setAiSearchMode(false);
    setAiSearchResults(null);
    setPage(1);
    setActiveSavedView("");
  };

  const applySavedView = (view: SavedView) => {
    setScene(view.scene || "all");
    setQ(view.q || "");
    setCategory(view.category || undefined);
    setBrandId(view.brandId || undefined);
    setStockStatus(view.stockStatus || undefined);
    setSort(view.sort || "created_at_desc");
    setVisibleCols(view.visibleCols?.length ? view.visibleCols : [...allColKeys]);
    setAiSearchMode(false);
    setAiSearchResults(null);
    setPage(1);
  };

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    loadBrands();
    setModalOpen(true);
  };

  const openEdit = (p: Product) => {
    setEditing(p);
    form.setFieldsValue(p);
    loadBrands();
    setModalOpen(true);
  };

  const handleSave = async (values: Record<string, unknown>) => {
    try {
      if (editing) {
        await updateProduct(editing.id, values);
        message.success("已更新");
      } else {
        await createProduct(values);
        message.success("已创建");
      }
      setModalOpen(false);
      await Promise.all([fetch(), loadStats()]);
    } catch {
      message.error(editing ? "更新失败" : "创建失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteProduct(id);
      message.success("已删除");
      await Promise.all([fetch(), loadStats()]);
    } catch {
      message.error("删除失败");
    }
  };

  const handleBatchDelete = async () => {
    try {
      await batchDeleteProducts(selectedRowKeys);
      message.success(`已删除 ${selectedRowKeys.length} 个产品`);
      setSelectedRowKeys([]);
      await Promise.all([fetch(), loadStats()]);
    } catch {
      message.error("批量删除失败");
    }
  };

  const handleBatchUpdate = async (values: Record<string, unknown>) => {
    if (!selectedRowKeys.length) {
      message.warning("未选中产品");
      return;
    }
    setBatchEditing(true);
    try {
      const fields = Object.fromEntries(Object.entries(values).filter(([, v]) => v !== undefined && v !== null && v !== ""));
      await batchUpdateProducts(selectedRowKeys, fields);
      message.success(`批量更新成功：${selectedRowKeys.length} 个产品`);
      setBatchTaskModalOpen(false);
      setSelectedRowKeys([]);
      setBatchTaskConfirm(false);
      await Promise.all([fetch(), loadStats()]);
    } catch {
      message.error("批量更新失败");
    } finally {
      setBatchEditing(false);
    }
  };

  const executeBatchTask = async () => {
    if (!batchTaskConfirm) {
      message.warning("请先确认影响范围");
      return;
    }
    if (batchTaskType === "delete") {
      await handleBatchDelete();
      setBatchTaskModalOpen(false);
      setBatchTaskConfirm(false);
      return;
    }
    if (batchTaskType === "export") {
      if (!exportProductsCsv(selectedProducts, "products_selected.csv")) {
        message.warning("无可导出数据");
        return;
      }
      message.success(`已导出 ${selectedProducts.length} 条`);
      setBatchTaskModalOpen(false);
      setBatchTaskConfirm(false);
      return;
    }
    const values = await batchEditForm.validateFields();
    await handleBatchUpdate(values);
  };

  const handleExportAll = () => {
    if (!exportProductsCsv(data, "products.csv")) {
      message.warning("无数据可导出");
      return;
    }
    message.success("导出成功");
  };

  const openSaveCurrentView = () => {
    setSaveViewName(activeSavedView || "");
    setSaveViewModalOpen(true);
  };

  const saveCurrentView = () => {
    const name = saveViewName.trim();
    if (!name) {
      message.warning("请输入视图名称");
      return;
    }
    const nextView: SavedView = {
      name,
      scene,
      q,
      category,
      brandId,
      stockStatus,
      sort,
      visibleCols,
    };
    const exists = savedViews.find((v) => v.name === name);
    const next = exists
      ? savedViews.map((v) => (v.name === name ? nextView : v))
      : [nextView, ...savedViews];
    persistSavedViews(next);
    setActiveSavedView(name);
    setSaveViewModalOpen(false);
    message.success("视图已保存");
  };

  const deleteCurrentView = () => {
    if (!activeSavedView) return;
    const next = savedViews.filter((v) => v.name !== activeSavedView);
    persistSavedViews(next);
    setActiveSavedView("");
    message.success("视图已删除");
  };

  const openDetail = async (product: Product) => {
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const [prodResp, invResp, salesResp] = await Promise.all([
        getProduct(product.id),
        getProductInventories({ product_id: product.id, page: 1, page_size: 200 }),
        getProductSales(product.id),
      ]);
      setDetailProduct(prodResp.data.data);
      setDetailInventories((invResp.data.data.list || []) as InventoryItem[]);
      setDetailSales((salesResp.data.data || null) as ProductSalesData | null);
    } catch {
      message.error("加载产品详情失败");
    } finally {
      setDetailLoading(false);
    }
  };

  const openQuickAction = async (product: Product, type: "price" | "safety") => {
    setQuickActionType(type);
    setQuickActionProduct(product);
    setQuickActionOpen(true);
    setQuickActionLoading(true);
    try {
      const invResp = await getProductInventories({ product_id: product.id, page: 1, page_size: 200 });
      const invList = (invResp.data.data.list || []) as InventoryItem[];
      setQuickInventoryOptions(invList);
      if (!invList.length) {
        setQuickInventoryId(undefined);
        setQuickValue(null);
        message.warning("该产品尚无库存记录，请先在库存管理中创建");
        return;
      }
      const first = invList[0];
      setQuickInventoryId(first.id);
      setQuickValue(type === "price" ? (first.unit_price ?? 0) : (first.safety_stock ?? 0));
    } catch {
      message.error("加载库存记录失败");
    } finally {
      setQuickActionLoading(false);
    }
  };

  const onQuickInventoryChange = (inventoryId: number) => {
    setQuickInventoryId(inventoryId);
    const selected = quickInventoryOptions.find((item) => item.id === inventoryId);
    if (!selected) return;
    if (quickActionType === "price") setQuickValue(selected.unit_price ?? 0);
    else setQuickValue(selected.safety_stock ?? 0);
  };

  const saveQuickAction = async () => {
    if (!quickInventoryId || quickValue == null) {
      message.warning("请完善参数");
      return;
    }
    setQuickActionSaving(true);
    try {
      if (quickActionType === "price") {
        await updateProductInventory(quickInventoryId, { unit_price: quickValue });
      } else {
        await updateProductInventory(quickInventoryId, { safety_stock: quickValue });
      }
      message.success("已保存");
      setQuickActionOpen(false);
      await Promise.all([fetch(), loadStats()]);
      if (detailProduct && quickActionProduct && detailProduct.id === quickActionProduct.id) {
        await openDetail(quickActionProduct);
      }
    } catch {
      message.error("保存失败");
    } finally {
      setQuickActionSaving(false);
    }
  };

  const handleAiParse = async () => {
    if (!aiText.trim()) return;
    setAiParsing(true);
    try {
      const resp = await aiParseProduct(aiText.trim());
      const parsed = resp.data.data as Record<string, unknown>;
      const specsStr = parsed.specs && typeof parsed.specs === "object"
        ? JSON.stringify(parsed.specs)
        : String(parsed.specs || "");
      let brandIdVal: number | undefined;
      const brandName = String(parsed.brand_name || "").toLowerCase();
      if (brandName) {
        const match = brands.find(
          (b) => b.name.toLowerCase().includes(brandName) || (b.name_cn || "").toLowerCase().includes(brandName),
        );
        if (match) brandIdVal = match.id;
      }
      form.setFieldsValue({
        name: parsed.name,
        sku: parsed.sku || undefined,
        category: parsed.category || undefined,
        package_type: parsed.package_type || undefined,
        specs: specsStr,
        unit: parsed.unit || undefined,
        brand_id: brandIdVal,
        notes: parsed.description || undefined,
      });
      setAiModalOpen(false);
      setAiText("");
      setModalOpen(true);
      message.success("AI 解析完成，请确认后保存");
    } catch {
      message.error("AI 解析失败");
    } finally {
      setAiParsing(false);
    }
  };

  const handleBomParse = async () => {
    if (!bomText.trim()) return;
    setBomParsing(true);
    try {
      const resp = await aiParseBom(bomText.trim());
      const items = (resp.data.data as { items: Record<string, unknown>[] }).items || [];
      let created = 0;
      for (const item of items) {
        try {
          await createProduct({
            name: String(item.mfr_pn || item.description || "未知型号"),
            sku: String(item.mfr_pn || item.customer_pn || ""),
            category: String(item.category || ""),
            package_type: String(item.package || ""),
            specs: String(item.description || ""),
            notes: `BOM导入: 客户料号=${item.customer_pn || ""} 位号=${item.reference || ""} 用量=${item.quantity || ""}`,
          });
          created += 1;
        } catch {
          // skip invalid line
        }
      }
      setBomModalOpen(false);
      setBomText("");
      message.success(`BOM 解析完成，成功创建 ${created}/${items.length} 个产品`);
      await Promise.all([fetch(1), loadStats()]);
    } catch {
      message.error("BOM 解析失败");
    } finally {
      setBomParsing(false);
    }
  };

  const handleImport = async () => {
    if (!importFile) {
      message.warning("请先选择文件");
      return;
    }
    setImporting(true);
    try {
      const resp = await importProducts(importFile);
      if (resp.data.code === 0) {
        const payload = resp.data.data as { created: number; errors: string[] };
        message.success(`导入成功：新增 ${payload.created} 个产品`);
        if (payload.errors?.length) {
          message.warning(`部分行失败：${payload.errors.slice(0, 3).join("；")}`);
        }
        setImportModalOpen(false);
        setImportFile(null);
        await Promise.all([fetch(1), loadStats()]);
      } else {
        message.error(resp.data.msg || "导入失败");
      }
    } catch {
      message.error("导入失败，请检查文件格式");
    } finally {
      setImporting(false);
    }
  };

  const handleTableChange = (
    pagination: TablePaginationConfig,
    _filters: unknown,
    sorter: SorterResult<Product> | SorterResult<Product>[],
  ) => {
    if (!aiSearchMode && pagination.current && pagination.current !== page) {
      setPage(pagination.current);
    }
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    if (!s.field) return;
    const fieldMap: Record<string, string> = { name: "name_asc", created_at: "created_at_asc" };
    const field = String(s.field);
    if (s.order === "ascend") setSort(fieldMap[field] || "created_at_asc");
    else if (s.order === "descend") setSort(fieldMap[field]?.replace("_asc", "_desc") || "created_at_desc");
  };

  useEffect(() => {
    loadSavedViews();
    loadBrands();
    loadStats();
  }, []);

  useEffect(() => {
    fetch();
  }, [page, sort, scene]);

  useEffect(() => {
    if (aiSearchMode) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      fetch(1, q);
    }, 350);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [q, aiSearchMode]);

  useEffect(() => {
    if (aiSearchMode && q.trim()) {
      const t = setTimeout(() => {
        handleAiSearch(q);
      }, 500);
      return () => clearTimeout(t);
    }
    setAiSearchResults(null);
  }, [q, aiSearchMode]);

  useEffect(() => {
    setPage(1);
    fetch(1);
  }, [category, brandId, stockStatus]);

  const columns: ColumnsType<Product> = [
    {
      title: "SKU",
      dataIndex: "sku",
      key: "sku",
      width: 140,
      fixed: "left",
      render: (v: string | null) => <span style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>{v || "-"}</span>,
    },
    {
      title: "产品名称",
      dataIndex: "name",
      key: "name",
      width: 220,
      fixed: "left",
      sorter: true,
      render: (text: string, r: Product) => <a onClick={() => openDetail(r)}>{text}</a>,
    },
    { title: "分类", dataIndex: "category", key: "category", width: 100, render: (v: string) => (v ? <Tag>{v}</Tag> : "-") },
    { title: "封装", dataIndex: "package_type", key: "package_type", width: 100, render: (v: string | null) => v || "-" },
    { title: "规格", dataIndex: "specs", key: "specs", width: 220, ellipsis: true, render: (v: string | null) => v || "-" },
    { title: "单位", dataIndex: "unit", key: "unit", width: 80, render: (v: string | null) => v || "-" },
    { title: "品牌", dataIndex: "brand_name", key: "brand_name", width: 130, render: (v: string | null) => v || "-" },
    {
      title: "完整度",
      dataIndex: "completion_score",
      key: "completion_score",
      width: 120,
      render: (v: number | null, r: Product) => {
        const score = v ?? 0;
        const missing = r.missing_fields?.length ? `缺少：${r.missing_fields.join("、")}` : "资料完整";
        return (
          <Tooltip title={missing}>
            <Progress percent={score} size="small" showInfo={false} strokeColor={score >= 80 ? "#52c41a" : score >= 50 ? "#faad14" : "#ff4d4f"} />
          </Tooltip>
        );
      },
    },
    { title: "供应商", dataIndex: "supplier_count", key: "supplier_count", width: 90, align: "right", render: (v: number | null) => v ?? 0 },
    { title: "分仓", dataIndex: "inventory_location_count", key: "inventory_location_count", width: 80, align: "right", render: (v: number | null) => v ?? 0 },
    {
      title: "库存状态",
      key: "stock_state",
      width: 110,
      render: (_: unknown, r: Product) => {
        const state = getStockState(r);
        if (state === "out") return <Tag color="red">缺货</Tag>;
        if (state === "low") return <Tag color="orange">低库存</Tag>;
        return <Tag color="green">在库</Tag>;
      },
    },
    { title: "库存", dataIndex: "quantity", key: "quantity", width: 90, align: "right", render: (v: number | null) => v != null ? v : 0 },
    { title: "可用", dataIndex: "available", key: "available", width: 90, align: "right", render: (_: number | null, r: Product) => getAvailableQty(r) },
    { title: "锁定", dataIndex: "locked_quantity", key: "locked", width: 90, align: "right", render: (v: number | null) => v != null ? v : 0 },
    { title: "安全库存", dataIndex: "safety_stock", key: "safety_stock", width: 100, align: "right", render: (v: number | null) => v != null ? v : "-" },
    { title: "单价", dataIndex: "unit_price", key: "unit_price", width: 110, align: "right", render: (v: number | null) => v != null ? `¥${v.toFixed(2)}` : "-" },
    { title: "最近销售", dataIndex: "last_sale_at", key: "last_sale_at", width: 170, render: (v: string | null) => formatDateTime(v) },
    {
      title: "操作",
      key: "actions",
      width: 230,
      fixed: "right",
      render: (_: unknown, r: Product) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button size="small" icon={<EyeOutlined />} onClick={() => openDetail(r)} />
          </Tooltip>
          <Tooltip title="快捷改价">
            <Button size="small" onClick={() => openQuickAction(r, "price")}>改价</Button>
          </Tooltip>
          <Tooltip title="快捷改安全库存">
            <Button size="small" onClick={() => openQuickAction(r, "safety")}>安库</Button>
          </Tooltip>
          <Tooltip title="编辑产品">
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          </Tooltip>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <style>{`
        .product-command-layout {
          display: grid;
          grid-template-columns: 220px minmax(0, 1fr) 280px;
          gap: 12px;
          align-items: start;
        }
        .product-command-sidebar,
        .product-command-context {
          position: sticky;
          top: 8px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .product-command-main {
          min-width: 0;
        }
        .product-command-panel {
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          overflow: hidden;
        }
        .product-command-panel-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          padding: 10px 12px;
          border-bottom: 1px solid #f0f0f0;
        }
        .product-command-body {
          padding: 12px;
        }
        .product-task-button {
          display: block;
          width: 100%;
          padding: 9px 12px;
          text-align: left;
          background: transparent;
          border: 0;
          border-bottom: 1px solid #f5f5f5;
          cursor: pointer;
        }
        .product-task-button:hover,
        .product-task-button.is-active {
          background: #f0f5ff;
        }
        .product-task-main,
        .product-context-score {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .product-task-note,
        .product-context-note {
          margin-top: 4px;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 18px;
        }
        .product-context-score {
          margin: 10px 0;
          padding: 10px;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .product-context-score-value {
          color: #1677ff;
          font-size: 26px;
          font-weight: 650;
          line-height: 1;
        }
        .product-context-action {
          margin-top: 10px;
          padding: 10px;
          background: #fffbe6;
          border: 1px solid #ffe58f;
          border-radius: 8px;
        }
        .product-context-actions {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          margin-top: 10px;
        }
        .product-batch-bar {
          position: sticky;
          top: 8px;
          z-index: 5;
          margin-bottom: 12px;
          padding: 10px 12px;
          background: #f0f5ff;
          border: 1px solid #adc6ff;
          border-radius: 8px;
        }
        .product-row-selected td { background: #f0f5ff !important; }
        .product-row-low td { background: #fffbe6 !important; }
        .product-row-out td { background: #fff2f0 !important; }
        @media (max-width: 1180px) {
          .product-command-layout {
            grid-template-columns: 1fr;
          }
          .product-command-sidebar,
          .product-command-context {
            position: static;
          }
          .product-context-actions {
            grid-template-columns: repeat(4, minmax(0, 1fr));
          }
        }
        @media (max-width: 768px) {
          .product-context-actions {
            grid-template-columns: 1fr 1fr;
          }
        }
      `}</style>

      <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
        <Col xs={24} sm={12} xl={4}>
          <Card size="small" loading={statsLoading}>
            <Statistic title="SKU 总数" value={stats.total} prefix={<InboxOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={4}>
          <Card size="small" loading={statsLoading}>
            <Statistic title="在库" value={stats.in_stock_count} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={4}>
          <Card size="small" loading={statsLoading}>
            <Statistic title="低库存" value={stats.low_stock_count} prefix={<WarningOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={4}>
          <Card size="small" loading={statsLoading}>
            <Statistic title="缺货" value={stats.out_of_stock_count} prefix={<StopOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={4}>
          <Card size="small" loading={statsLoading}>
            <Statistic title="待完善" value={stats.pending_completion_count} />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={4}>
          <Card size="small" loading={statsLoading}>
            <Statistic title="30天无动销" value={stats.stale_30d_count} />
          </Card>
        </Col>
      </Row>

      <div className="product-command-layout">
        <aside className="product-command-sidebar">
          <div className="product-command-panel">
            <div className="product-command-panel-head">
              <Space size={6}>
                <ThunderboltOutlined />
                <span style={{ fontWeight: 600 }}>产品任务</span>
              </Space>
              <Button size="small" type="link" onClick={() => setAiSearchMode(true)}>AI搜索</Button>
            </div>
            {productTaskItems.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`product-task-button${productTask === item.key ? " is-active" : ""}`}
                onClick={() => {
                  setProductTask(item.key);
                  setContextProductId(null);
                  setPage(1);
                  if (item.key === "ai_search") setAiSearchMode(true);
                  if (item.key !== "ai_search" && aiSearchMode) {
                    setAiSearchMode(false);
                    setAiSearchResults(null);
                  }
                }}
              >
                <span className="product-task-main">
                  <span style={{ fontWeight: productTask === item.key ? 600 : 400 }}>{item.label}</span>
                  <Tag color={item.color}>{item.count}</Tag>
                </span>
                <span className="product-task-note">{item.note}</span>
              </button>
            ))}
          </div>

          <div className="product-command-panel">
            <div className="product-command-panel-head">
              <span style={{ fontWeight: 600 }}>库存快照</span>
            </div>
            <div className="product-command-body">
              <Space size={[4, 6]} wrap>
                <Tag color="green">在库 {stats.in_stock_count}</Tag>
                <Tag color="orange">低库存 {stats.low_stock_count}</Tag>
                <Tag color="red">缺货 {stats.out_of_stock_count}</Tag>
                <Tag>待完善 {stats.pending_completion_count}</Tag>
              </Space>
            </div>
          </div>
        </aside>

        <main className="product-command-main">
      <Card size="small" style={{ marginBottom: 12 }}>
        <Row gutter={[10, 10]} align="middle">
          <Col flex="420px">
            <Input
              placeholder={aiSearchMode ? "AI 语义搜索（如：高频放大器 贴片）" : "自然语言搜索（如：0402 10uF MLCC）"}
              prefix={<SearchOutlined />}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              allowClear
              suffix={(
                <Tooltip title={aiSearchMode ? "切换普通搜索" : "切换 AI 语义搜索"}>
                  <Button
                    size="small"
                    type={aiSearchMode ? "primary" : "default"}
                    icon={<ThunderboltOutlined />}
                    onClick={() => {
                      setAiSearchMode((prev) => !prev);
                      setPage(1);
                      if (aiSearchMode) setAiSearchResults(null);
                    }}
                    style={{ marginLeft: 4 }}
                  />
                </Tooltip>
              )}
            />
          </Col>
          <Col>
            <Segmented
              options={SCENE_OPTIONS}
              value={scene}
              onChange={(v) => {
                setScene(v as SceneValue);
                setPage(1);
              }}
            />
          </Col>
          <Col>
            <Select
              allowClear
              placeholder="分类"
              style={{ width: 120 }}
              value={category}
              onChange={(v) => {
                setCategory(v);
                setPage(1);
              }}
              options={CATEGORIES.map((v) => ({ value: v, label: v }))}
            />
          </Col>
          <Col>
            <Select
              allowClear
              placeholder="品牌"
              style={{ width: 160 }}
              value={brandId}
              onChange={(v) => {
                setBrandId(v);
                setPage(1);
              }}
              options={brands.map((b) => ({ value: b.id, label: b.name_cn || b.name }))}
            />
          </Col>
          <Col>
            <Select
              placeholder="库存状态"
              style={{ width: 110 }}
              value={stockStatus}
              onChange={(v) => {
                setStockStatus(v);
                setPage(1);
              }}
              options={STOCK_OPTIONS}
            />
          </Col>
          <Col>
            <Select
              value={sort}
              onChange={(v) => {
                setSort(v);
                setPage(1);
              }}
              options={SORT_OPTIONS}
              style={{ width: 110 }}
            />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={resetAllFilters}>重置</Button>
          </Col>
        </Row>

        <Row gutter={[10, 10]} style={{ marginTop: 8 }}>
          <Col>
            <Space>
              <Select
                value={activeSavedView || undefined}
                allowClear
                placeholder="保存视图"
                style={{ width: 180 }}
                onChange={(name) => {
                  const nextName = name || "";
                  setActiveSavedView(nextName);
                  if (!nextName) {
                    resetAllFilters();
                    return;
                  }
                  const view = savedViews.find((v) => v.name === nextName);
                  if (view) applySavedView(view);
                }}
                options={savedViews.map((v) => ({ label: v.name, value: v.name }))}
              />
              <Button icon={<SaveOutlined />} onClick={openSaveCurrentView}>保存当前视图</Button>
              {activeSavedView && (
                <Popconfirm title={`删除视图「${activeSavedView}」？`} onConfirm={deleteCurrentView}>
                  <Button danger>删除视图</Button>
                </Popconfirm>
              )}
            </Space>
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              <Button icon={<UploadOutlined />} onClick={() => setImportModalOpen(true)}>导入</Button>
              <Button icon={<DownloadOutlined />} onClick={handleExportAll}>导出</Button>
              <Popover
                content={(
                  <Checkbox.Group
                    options={allColKeys.map((k) => ({ label: COL_LABEL_MAP[k] || k, value: k }))}
                    value={visibleCols}
                    onChange={(vals) => setVisibleCols(vals as string[])}
                  />
                )}
                title="显示列"
                trigger="click"
              >
                <Button icon={<SettingOutlined />}>列</Button>
              </Popover>
              <Button icon={<ThunderboltOutlined />} onClick={() => setAiModalOpen(true)}>AI 解析</Button>
              <Button icon={<FileTextOutlined />} onClick={() => setBomModalOpen(true)}>BOM 导入</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建产品</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {selectedRowKeys.length > 0 && !aiSearchMode && (
        <div className="product-batch-bar">
          <Space wrap>
            <Tag color="blue">已选 {selectedRowKeys.length} 个产品</Tag>
            <Tag>在库 {selectedMetrics.inStock}</Tag>
            <Tag color="orange">低库存 {selectedMetrics.lowStock}</Tag>
            <Tag color="red">缺货 {selectedMetrics.outOfStock}</Tag>
            <Button icon={<SettingOutlined />} onClick={() => { setBatchTaskType("update"); setBatchTaskConfirm(false); batchEditForm.resetFields(); setBatchTaskModalOpen(true); }}>批量任务面板</Button>
            <Button onClick={() => setSelectedRowKeys([])}>清空选择</Button>
          </Space>
        </div>
      )}

      <Card bodyStyle={{ padding: 0 }}>
        <Table
          rowKey="id"
          columns={columns.filter((c) => visibleCols.includes(String(c.key)))}
          dataSource={tableProducts}
          loading={aiSearchMode ? aiSearching : loading}
          size="middle"
          tableLayout="auto"
          onChange={handleTableChange}
          rowSelection={
            aiSearchMode
              ? undefined
              : {
                  selectedRowKeys,
                  onChange: (keys) => setSelectedRowKeys(keys as number[]),
                }
          }
          rowClassName={(record) => {
            if (contextProduct?.id === record.id) return "product-row-selected";
            const state = getStockState(record);
            if (state === "low") return "product-row-low";
            if (state === "out") return "product-row-out";
            return "";
          }}
          onRow={(record) => ({
            onClick: () => setContextProductId(record.id),
          })}
          locale={{
            emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={aiSearchMode ? "未命中语义搜索结果" : "暂无产品数据"} />,
          }}
          scroll={{ x: 1850 }}
          pagination={
            aiSearchMode
              ? false
              : {
                  current: page,
                  pageSize: PAGE_SIZE,
                  total: productTask !== "all" ? filteredProducts.length : total,
                  showTotal: (count) => `共 ${count} 条`,
                  showSizeChanger: false,
                }
          }
        />
      </Card>

      {selectedRowKeys.length >= 2 && !aiSearchMode && (
        <Card
          title={`产品对比（${selectedRowKeys.length} 个）`}
          extra={<Button size="small" onClick={() => setSelectedRowKeys([])}>清除选择</Button>}
          style={{ marginTop: 16 }}
          size="small"
        >
          <Table
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={selectedProducts}
            columns={[
              { title: "SKU", dataIndex: "sku", width: 100 },
              { title: "产品名称", dataIndex: "name", width: 160 },
              { title: "分类", dataIndex: "category", width: 80 },
              { title: "封装", dataIndex: "package_type", width: 80 },
              { title: "规格", dataIndex: "specs", ellipsis: true, width: 150 },
              { title: "品牌", dataIndex: "brand_name", width: 100 },
              { title: "完整度", dataIndex: "completion_score", width: 80, render: (v: number | null) => `${v ?? 0}%` },
              { title: "供应商", dataIndex: "supplier_count", width: 70 },
              { title: "分仓", dataIndex: "inventory_location_count", width: 60 },
              { title: "库存", dataIndex: "quantity", width: 60 },
              { title: "可用", dataIndex: "available", width: 60, render: (_: number, r: Product) => getAvailableQty(r) },
              { title: "安全库存", dataIndex: "safety_stock", width: 80 },
              { title: "单价", dataIndex: "unit_price", width: 80, render: (v: number | null) => (v != null ? `¥${v.toFixed(2)}` : "-") },
            ]}
            scroll={{ x: true }}
            style={{ overflowX: "auto" }}
          />
        </Card>
      )}
        </main>

        <aside className="product-command-context">
          <div className="product-command-panel">
            <div className="product-command-panel-head">
              <Space size={6}>
                <InboxOutlined />
                <span style={{ fontWeight: 600 }}>产品上下文</span>
              </Space>
              {contextProduct && (
                <Tag color={contextStockState === "out" ? "red" : contextStockState === "low" ? "orange" : "green"}>
                  {contextStockState === "out" ? "缺货" : contextStockState === "low" ? "低库存" : "在库"}
                </Tag>
              )}
            </div>
            {!contextProduct ? (
              <div className="product-command-body">
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择产品查看上下文" />
              </div>
            ) : (
              <div className="product-command-body">
                <a style={{ fontWeight: 600 }} onClick={() => openDetail(contextProduct)}>{contextProduct.name}</a>
                <div className="product-context-note">
                  {[contextProduct.sku, contextProduct.brand_name, contextProduct.category, contextProduct.package_type].filter(Boolean).join(" / ") || "暂无基础信息"}
                </div>
                <div className="product-context-score">
                  <div>
                    <span style={{ color: "#8c8c8c" }}>AI优先级</span>
                    <div className="product-context-note">按库存、资料、供应商、动销计算</div>
                  </div>
                  <div className="product-context-score-value">{contextPriorityScore}</div>
                </div>
                <Space size={[4, 6]} wrap>
                  <Tag color={contextStockState === "out" ? "red" : contextStockState === "low" ? "orange" : "green"}>
                    可用 {getAvailableQty(contextProduct)}
                  </Tag>
                  <Tag>安全库存 {contextProduct.safety_stock ?? "-"}</Tag>
                  <Tag>供应商 {contextProduct.supplier_count ?? 0}</Tag>
                  <Tag>完整度 {contextProduct.completion_score ?? 0}%</Tag>
                </Space>
                <div className="product-context-action">
                  <span style={{ fontWeight: 600 }}>推荐动作</span>
                  <div className="product-context-note">{contextSuggestedAction}</div>
                </div>
                <Descriptions column={1} size="small" style={{ marginTop: 10 }}>
                  <Descriptions.Item label="规格">{contextProduct.specs || "-"}</Descriptions.Item>
                  <Descriptions.Item label="最近销售">{formatDateTime(contextProduct.last_sale_at)}</Descriptions.Item>
                  <Descriptions.Item label="分仓">{contextProduct.inventory_location_count ?? 0}</Descriptions.Item>
                  <Descriptions.Item label="单价">{contextProduct.unit_price != null ? `¥${contextProduct.unit_price.toFixed(2)}` : "-"}</Descriptions.Item>
                </Descriptions>
                {contextProduct.missing_fields?.length ? (
                  <div className="product-context-note">缺少：{contextProduct.missing_fields.join("、")}</div>
                ) : null}
                <div className="product-context-actions">
                  <Button size="small" type="primary" icon={<EyeOutlined />} onClick={() => openDetail(contextProduct)}>详情</Button>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(contextProduct)}>编辑</Button>
                  <Button size="small" onClick={() => openQuickAction(contextProduct, "price")}>改价</Button>
                  <Button size="small" onClick={() => openQuickAction(contextProduct, "safety")}>安库</Button>
                </div>
              </div>
            )}
          </div>

          <div className="product-command-panel">
            <div className="product-command-panel-head">
              <span style={{ fontWeight: 600 }}>智能工具</span>
            </div>
            <div className="product-command-body">
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Button block size="small" icon={<ThunderboltOutlined />} onClick={() => setAiModalOpen(true)}>AI解析产品</Button>
                <Button block size="small" icon={<FileTextOutlined />} onClick={() => setBomModalOpen(true)}>BOM导入</Button>
                <Button block size="small" icon={<UploadOutlined />} onClick={() => setImportModalOpen(true)}>批量导入</Button>
                <Button block size="small" icon={<DownloadOutlined />} onClick={handleExportAll}>导出当前页</Button>
              </Space>
            </div>
          </div>
        </aside>
      </div>

      <Modal
        title={editing ? "编辑产品" : "新建产品"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        width={640}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Row gutter={12}>
            <Col span={12}><Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="sku" label="SKU"><Input /></Form.Item></Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}><Form.Item name="category" label="分类"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="package_type" label="封装"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit" label="单位"><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="specs" label="规格"><Input.TextArea rows={2} /></Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="brand_id" label="品牌">
                <Select allowClear placeholder="选择品牌" options={brands.map((b) => ({ value: b.id, label: b.name_cn || b.name }))} />
              </Form.Item>
            </Col>
            <Col span={12}><Form.Item name="image_url" label="图片URL"><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal
        title="批量任务面板"
        open={batchTaskModalOpen}
        onCancel={() => setBatchTaskModalOpen(false)}
        onOk={executeBatchTask}
        confirmLoading={batchEditing}
        okText="执行任务"
        width={560}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Descriptions size="small" bordered column={3}>
            <Descriptions.Item label="选中数量">{selectedRowKeys.length}</Descriptions.Item>
            <Descriptions.Item label="低库存">{selectedMetrics.lowStock}</Descriptions.Item>
            <Descriptions.Item label="缺货">{selectedMetrics.outOfStock}</Descriptions.Item>
          </Descriptions>
          <Select
            value={batchTaskType}
            onChange={(v) => setBatchTaskType(v as BatchTaskType)}
            options={[
              { value: "update", label: "批量更新字段" },
              { value: "delete", label: "批量删除产品" },
              { value: "export", label: "导出选中产品" },
            ]}
          />

          {batchTaskType === "update" && (
            <Form form={batchEditForm} layout="vertical">
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item name="brand_id" label="品牌">
                    <Select allowClear placeholder="保持不变" options={brands.map((b) => ({ value: b.id, label: b.name_cn || b.name }))} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="category" label="分类">
                    <Input placeholder="保持不变" />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item name="package_type" label="封装">
                    <Input placeholder="保持不变" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="unit" label="单位">
                    <Input placeholder="保持不变" />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item name="specs" label="规格">
                <Input.TextArea rows={2} placeholder="保持不变" />
              </Form.Item>
              <Form.Item name="notes" label="备注">
                <Input.TextArea rows={2} placeholder="保持不变" />
              </Form.Item>
            </Form>
          )}

          {batchTaskType === "delete" && (
            <Tag color="red">该任务将删除 {selectedRowKeys.length} 条产品记录（软删除）</Tag>
          )}
          {batchTaskType === "export" && (
            <Tag color="blue">将导出 {selectedRowKeys.length} 条已选产品记录</Tag>
          )}

          <Checkbox checked={batchTaskConfirm} onChange={(e) => setBatchTaskConfirm(e.target.checked)}>
            我已确认本次任务影响范围
          </Checkbox>
        </Space>
      </Modal>

      <Modal
        title="保存视图"
        open={saveViewModalOpen}
        onCancel={() => setSaveViewModalOpen(false)}
        onOk={saveCurrentView}
      >
        <Input
          placeholder="请输入视图名称"
          value={saveViewName}
          onChange={(e) => setSaveViewName(e.target.value)}
          maxLength={30}
        />
      </Modal>

      <Modal
        title={quickActionType === "price" ? "快捷改价" : "快捷改安全库存"}
        open={quickActionOpen}
        onCancel={() => setQuickActionOpen(false)}
        onOk={saveQuickAction}
        confirmLoading={quickActionSaving}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <div>产品：{quickActionProduct?.name || "-"}</div>
          <Select
            loading={quickActionLoading}
            placeholder="选择仓库库存记录"
            value={quickInventoryId}
            onChange={onQuickInventoryChange}
            options={quickInventoryOptions.map((item) => ({
              value: item.id,
              label: `${item.warehouse_name} | 库存:${item.quantity} | 可用:${item.available_quantity}`,
            }))}
          />
          <InputNumber
            style={{ width: "100%" }}
            min={0}
            precision={quickActionType === "price" ? 2 : 0}
            value={quickValue as number}
            onChange={(v) => setQuickValue(v)}
            placeholder={quickActionType === "price" ? "输入单价" : "输入安全库存"}
          />
        </Space>
      </Modal>

      <Drawer
        title={`产品详情${detailProduct ? ` - ${detailProduct.name}` : ""}`}
        placement="right"
        width={680}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      >
        {detailLoading ? (
          <Card loading />
        ) : !detailProduct ? (
          <Empty description="暂无详情" />
        ) : (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="SKU">{detailProduct.sku || "-"}</Descriptions.Item>
              <Descriptions.Item label="品牌">{detailProduct.brand_name || "-"}</Descriptions.Item>
              <Descriptions.Item label="分类">{detailProduct.category || "-"}</Descriptions.Item>
              <Descriptions.Item label="封装">{detailProduct.package_type || "-"}</Descriptions.Item>
              <Descriptions.Item label="单位">{detailProduct.unit || "-"}</Descriptions.Item>
              <Descriptions.Item label="最近销售">{formatDateTime(detailProduct.last_sale_at)}</Descriptions.Item>
              <Descriptions.Item label="资料完整度">{detailProduct.completion_score ?? 0}%</Descriptions.Item>
              <Descriptions.Item label="供应商数">{detailProduct.supplier_count ?? 0}</Descriptions.Item>
              <Descriptions.Item label="分仓数">{detailProduct.inventory_location_count ?? 0}</Descriptions.Item>
              <Descriptions.Item label="总库存">{detailProduct.quantity ?? 0}</Descriptions.Item>
              <Descriptions.Item label="可用库存">{getAvailableQty(detailProduct)}</Descriptions.Item>
              <Descriptions.Item label="锁定库存">{detailProduct.locked_quantity ?? 0}</Descriptions.Item>
              <Descriptions.Item label="规格" span={2}>{detailProduct.specs || "-"}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{detailProduct.notes || "-"}</Descriptions.Item>
            </Descriptions>

            <Divider style={{ margin: "4px 0" }}>库存分仓</Divider>
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={detailInventories}
              columns={[
                { title: "仓库", dataIndex: "warehouse_name", width: 120 },
                { title: "库存", dataIndex: "quantity", width: 90, align: "right" },
                { title: "可用", dataIndex: "available_quantity", width: 90, align: "right" },
                { title: "锁定", dataIndex: "locked_quantity", width: 90, align: "right" },
                { title: "安全库存", dataIndex: "safety_stock", width: 100, align: "right" },
                { title: "单价", dataIndex: "unit_price", width: 100, align: "right", render: (v: number | null) => (v != null ? `¥${Number(v).toFixed(2)}` : "-") },
              ]}
            />

            <Divider style={{ margin: "4px 0" }}>最近销售动作</Divider>
            <List
              size="small"
              bordered
              dataSource={detailSales?.orders || []}
              locale={{ emptyText: "暂无销售订单记录" }}
              renderItem={(item) => {
                const row = item as { order_no?: string; status?: string; quantity?: number; unit_price?: number; created_at?: string };
                return (
                  <List.Item>
                    <Space split={<span>|</span>} size={4}>
                      <span>{row.order_no || "-"}</span>
                      <Tag>{row.status || "-"}</Tag>
                      <span>数量 {row.quantity || 0}</span>
                      <span>单价 {row.unit_price != null ? `¥${Number(row.unit_price).toFixed(2)}` : "-"}</span>
                      <span>{formatDateTime(row.created_at || null)}</span>
                    </Space>
                  </List.Item>
                );
              }}
            />
          </Space>
        )}
      </Drawer>

      <Modal
        title="AI 智能解析"
        open={aiModalOpen}
        onCancel={() => setAiModalOpen(false)}
        onOk={handleAiParse}
        confirmLoading={aiParsing}
        okText="解析并填充表单"
      >
        <p style={{ color: "#888", marginBottom: 8 }}>粘贴料号、型号、数据手册描述或供应商报价文本，AI 自动提取产品信息</p>
        <Input.TextArea
          rows={6}
          placeholder={"例如：\nSamsung CL05A105KP5NNNC\n0402 1uF ±10% 10V X5R MLCC\n原装正品，整盘4000PCS"}
          value={aiText}
          onChange={(e) => setAiText(e.target.value)}
        />
      </Modal>

      <Modal
        title="BOM 批量导入"
        open={bomModalOpen}
        onCancel={() => setBomModalOpen(false)}
        onOk={handleBomParse}
        confirmLoading={bomParsing}
        okText="解析并创建产品"
      >
        <p style={{ color: "#888", marginBottom: 8 }}>粘贴 BOM 清单，AI 逐行解析并自动创建产品。支持多行粘贴。</p>
        <Input.TextArea
          rows={10}
          placeholder={"例如：\n1 GRM155R61A105KE15 1uF 16V 0402 X5R 10% 100pcs\n2 CL05A105KP5NNNC 1uF 10V 0402 X5R 10% 200pcs"}
          value={bomText}
          onChange={(e) => setBomText(e.target.value)}
        />
      </Modal>

      <Modal
        title="批量导入产品"
        open={importModalOpen}
        onCancel={() => {
          setImportModalOpen(false);
          setImportFile(null);
        }}
        onOk={handleImport}
        confirmLoading={importing}
        okText="导入"
        width={480}
      >
        <p style={{ color: "#888", marginBottom: 16 }}>
          支持 CSV / XLSX 文件，列：<code>name, sku, category, brand, package_type, specs, unit, notes</code>
        </p>
        <input
          type="file"
          accept=".csv,.xlsx"
          onChange={(e) => setImportFile(e.target.files?.[0] || null)}
          style={{ marginBottom: 8 }}
        />
        {importFile && <p style={{ color: "#555" }}>已选：{importFile.name}</p>}
        <a
          href="/products_template.csv"
          download
          style={{ fontSize: 12, color: "#1677ff" }}
          onClick={(e) => {
            e.preventDefault();
            const headers = ["name", "sku", "category", "brand", "package_type", "specs", "unit", "notes"];
            const sample = ["8658B传感器", "8658B", "传感器", "QST", "BGA", "原装正品", "pcs", "导入备注"];
            const csv = [headers, sample].map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
            const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "products_template.csv";
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          下载模板文件
        </a>
      </Modal>
    </div>
  );
}
