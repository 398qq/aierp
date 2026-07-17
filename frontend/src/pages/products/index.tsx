import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  Alert,
  Modal,
  Popconfirm,
  Popover,
  Progress,
  Row,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  message,
} from "antd";
import { StatusTag } from "../../ui";
import {
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
  ThunderboltOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import type { SorterResult } from "antd/es/table/interface";
import { aiParseBom, aiParseProduct, aiSearchProducts, batchDeleteProducts, batchUpdateProducts, createProduct, deleteProduct, getBrands, getProduct, getProductInventories, getProducts, getProductSales, getProductStats, getWarehouses, importProducts, updateProduct, updateProductInventory, getApiErrorMessage } from "../../api";
import type { Brand, InventoryItem, Product, Warehouse } from "../../types";
import {
  BatchTaskType,
  CATEGORIES,
  COL_LABEL_MAP,
  exportProductsCsv,
  formatDateTime,
  getAvailableQty,
  getBrandSelectLabel,
  getDaysSince,
  getProductPriorityScore,
  getProductSuggestedAction,
  getStockState,
  PAGE_SIZE,
  ProductSalesData,
  ProductStats,
  ProductTaskKey,
  SavedView,
  SAVED_VIEW_STORAGE_KEY,
  SCENE_OPTIONS,
  SceneValue,
  SORT_OPTIONS,
  STOCK_OPTIONS,
  TASK_SCENE_MAP,
  PRODUCT_TASK_LABELS,
} from "./constants";
import { useProductTableColumns } from "./useProductTableColumns";
import ProductHealthStrip from "./ProductHealthStrip";
import ProductDetailDrawer from "./ProductDetailDrawer";
import "./products.css";

export default function ProductList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
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
  const [productStatus, setProductStatus] = useState<string | undefined>();
  const [sort, setSort] = useState<string>("created_at_desc");
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
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
    no_supplier_count: 0,
  });

  const [form] = Form.useForm();
  const watchedEditorStatus = Form.useWatch("status", form) as string | undefined;
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const allColKeys = [
    "sku",
    "name",
    "mpn",
    "status",
    "product_type",
    "brand_name",
    "owner",
    "category",
    "package",
    "compliance",
    "unit",
    "specs",
    "completion_score",
    "supplier_count",
    "stock_state",
    "quantity",
    "available",
    "safety_stock",
    "default_warehouse_name",
    "list_price",
    "minimum_sale_price",
    "weighted_avg_cost",
    "currency",
    "last_sale_at",
    "actions",
  ];
  const defaultColKeys = [
    "sku", "name", "status", "brand_name", "category", "specs", "unit",
    "stock_state", "available", "safety_stock", "default_warehouse_name",
    "supplier_count", "list_price", "owner", "completion_score", "actions",
  ];
  const [visibleCols, setVisibleCols] = useState<string[]>(defaultColKeys);
  const searchText = q.trim();
  const activeProductTask: ProductTaskKey = searchText ? "all" : productTask;

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
    if (task === "complete")
      return (product.completion_score ?? 100) < 80 || Boolean(product.missing_fields?.length);
    if (task === "stale") return staleDays == null || staleDays > 30;
    if (task === "no_supplier") return (product.supplier_count ?? 0) <= 0;
    if (task === "ai_search") return getProductPriorityScore(product) >= 65;
    return true;
  };

  const filteredProducts = useMemo(() => {
    if (activeProductTask !== "ai_search") return data;
    return data
      .filter((item) => productMatchesTask(item, activeProductTask))
      .sort((a, b) => getProductPriorityScore(b) - getProductPriorityScore(a));
  }, [activeProductTask, data]);

  const productTaskItems = useMemo(
    () => [
      {
        key: "replenish" as ProductTaskKey,
        label: PRODUCT_TASK_LABELS.replenish,
        count: stats.low_stock_count,
        color: "orange",
        note: "可用库存低于安全线",
      },
      {
        key: "out" as ProductTaskKey,
        label: PRODUCT_TASK_LABELS.out,
        count: stats.out_of_stock_count,
        color: "red",
        note: "当前无可用库存",
      },
      {
        key: "complete" as ProductTaskKey,
        label: PRODUCT_TASK_LABELS.complete,
        count: stats.pending_completion_count,
        color: "gold",
        note: "资料字段不完整",
      },
      {
        key: "stale" as ProductTaskKey,
        label: PRODUCT_TASK_LABELS.stale,
        count: stats.stale_30d_count,
        color: "blue",
        note: "超过30天无销售",
      },
      {
        key: "no_supplier" as ProductTaskKey,
        label: PRODUCT_TASK_LABELS.no_supplier,
        count: stats.no_supplier_count ?? 0,
        color: "purple",
        note: "未维护供应商",
      },
      {
        key: "ai_search" as ProductTaskKey,
        label: PRODUCT_TASK_LABELS.ai_search,
        count: data.filter((item) => productMatchesTask(item, "ai_search")).length,
        color: "cyan",
        note: "综合优先级较高",
      },
      {
        key: "all" as ProductTaskKey,
        label: PRODUCT_TASK_LABELS.all,
        count: stats.total,
        color: "default",
        note: "回到普通清单",
      },
    ],
    [data, stats],
  );

  const tableProducts = useMemo(
    () => (aiSearchMode ? ((aiSearchResults ?? []) as unknown as Product[]) : filteredProducts),
    [aiSearchMode, aiSearchResults, filteredProducts],
  );
  const currentListTotal = aiSearchMode
    ? tableProducts.length
    : activeProductTask === "ai_search"
      ? filteredProducts.length
      : total;
  const currentListTitle = searchText
    ? "搜索结果"
    : scene !== "all" && productTask === "all"
      ? SCENE_OPTIONS.find((option) => option.value === scene)?.label || "产品清单"
      : PRODUCT_TASK_LABELS[activeProductTask];
  const activeBrand = brands.find((brand) => brand.id === brandId);
  const activeBrandLabel = activeBrand ? getBrandSelectLabel(activeBrand) : String(brandId || "");
  const contextProduct = useMemo(
    () =>
      contextProductId == null
        ? null
        : data.find((item) => item.id === contextProductId) ||
          tableProducts.find((item) => item.id === contextProductId) ||
          null,
    [contextProductId, data, tableProducts],
  );
  const contextPriorityScore = contextProduct ? getProductPriorityScore(contextProduct) : 0;
  const contextSuggestedAction = contextProduct ? getProductSuggestedAction(contextProduct) : "";
  const healthMetrics = useMemo(() => {
    const totalCount = stats.total || 0;
    const pct = (value: number) => (totalCount > 0 ? Math.round((value / totalCount) * 100) : 0);
    return {
      inStockRate: pct(stats.in_stock_count),
      lowStockRate: pct(stats.low_stock_count),
      outOfStockRate: pct(stats.out_of_stock_count),
      completionGapRate: pct(stats.pending_completion_count),
    };
  }, [stats]);

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
      if (productStatus) params.status = productStatus;
      const resp = await getProducts(params);
      const list = (resp.data.data.list || []) as Product[];
      setData(list);
      setTotal(resp.data.data.total || 0);
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      // eslint-disable-next-line no-console
      console.error("getProducts failed:", err);
      message.error(`加载产品列表失败: ${detail}`);
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "AI 搜索失败")); } finally {
      setAiSearching(false);
    }
  };

  const loadBrands = async () => {
    try {
      const r = await getBrands({ page: 1, page_size: 200 });
      const payload = r.data.data as Brand[] | { list?: Brand[] };
      setBrands(Array.isArray(payload) ? payload : payload.list || []);
    } catch {
      // no-op
    }
  };

  const loadWarehouses = async () => {
    try {
      const r = await getWarehouses({ page: 1, page_size: 200 });
      if (r.data.code === 0) setWarehouses((r.data.data.list || []) as Warehouse[]);
    } catch {
      // Warehouse selection is optional; keep the form usable if the directory is unavailable.
    }
  };

  const resetAllFilters = () => {
    setQ("");
    setScene("all");
    setProductTask("all");
    setCategory(undefined);
    setBrandId(undefined);
    setStockStatus(undefined);
    setProductStatus(undefined);
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
    setVisibleCols(view.visibleCols?.length ? view.visibleCols : defaultColKeys);
    setAiSearchMode(false);
    setAiSearchResults(null);
    setPage(1);
  };

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    loadBrands();
    loadWarehouses();
    setModalOpen(true);
  };

  const openEdit = (p: Product) => {
    setEditing(p);
    form.setFieldsValue(p);
    loadBrands();
    loadWarehouses();
    setModalOpen(true);
  };

  const closeEditor = () => {
    setModalOpen(false);
    if (searchParams.has("edit")) {
      const next = new URLSearchParams(searchParams);
      next.delete("edit");
      setSearchParams(next, { replace: true });
    }
  };

  useEffect(() => {
    const editId = Number(searchParams.get("edit"));
    if (!editId || (modalOpen && editing?.id === editId)) return;
    getProduct(editId)
      .then((response) => openEdit(response.data.data))
      .catch((error: unknown) => {
        message.error(getApiErrorMessage(error, "加载产品失败"));
        closeEditor();
      });
  }, [searchParams]);

  const handleSave = async (values: Record<string, unknown>) => {
    try {
      if (editing) {
        await updateProduct(editing.id, values);
        message.success("已更新");
      } else {
        await createProduct(values);
        message.success("已创建");
      }
      closeEditor();
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
  };

  const handleBatchDelete = async () => {
    try {
      await batchDeleteProducts(selectedRowKeys);
      message.success(`已删除 ${selectedRowKeys.length} 个产品`);
      setSelectedRowKeys([]);
      await Promise.all([fetch(), loadStats()]);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "批量删除失败")); }
  };

  const handleBatchUpdate = async (values: Record<string, unknown>) => {
    if (!selectedRowKeys.length) {
      message.warning("未选中产品");
      return;
    }
    setBatchEditing(true);
    try {
      const fields = Object.fromEntries(
        Object.entries(values).filter(([, v]) => v !== undefined && v !== null && v !== ""),
      );
      await batchUpdateProducts(selectedRowKeys, fields);
      message.success(`批量更新成功：${selectedRowKeys.length} 个产品`);
      setBatchTaskModalOpen(false);
      setSelectedRowKeys([]);
      setBatchTaskConfirm(false);
      await Promise.all([fetch(), loadStats()]);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "批量更新失败")); } finally {
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载产品详情失败")); } finally {
      setDetailLoading(false);
    }
  };

  const openQuickAction = async (product: Product, type: "price" | "safety") => {
    setQuickActionType(type);
    setQuickActionProduct(product);
    setQuickActionOpen(true);
    setQuickActionLoading(true);
    try {
      const invResp = await getProductInventories({
        product_id: product.id,
        page: 1,
        page_size: 200,
      });
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载库存记录失败")); } finally {
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "保存失败")); } finally {
      setQuickActionSaving(false);
    }
  };

  const handleAiParse = async () => {
    if (!aiText.trim()) return;
    setAiParsing(true);
    try {
      const resp = await aiParseProduct(aiText.trim());
      const parsed = resp.data.data as Record<string, unknown>;
      const specsStr =
        parsed.specs && typeof parsed.specs === "object"
          ? JSON.stringify(parsed.specs)
          : String(parsed.specs || "");
      let brandIdVal: number | undefined;
      const brandName = String(parsed.brand_name || "").toLowerCase();
      if (brandName) {
        const match = brands.find(
          (b) =>
            b.name.toLowerCase().includes(brandName) ||
            (b.name_cn || "").toLowerCase().includes(brandName),
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "AI 解析失败")); } finally {
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "BOM 解析失败")); } finally {
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "导入失败，请检查文件格式")); } finally {
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
    else if (s.order === "descend")
      setSort(fieldMap[field]?.replace("_asc", "_desc") || "created_at_desc");
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
  }, [category, brandId, stockStatus, productStatus]);

  const columns: ColumnsType<Product> = useProductTableColumns({
    onOpenDetail: openDetail,
    onOpenFullDetail: (product) => navigate(`/products/${product.id}`),
    onOpenEdit: openEdit,
    onOpenQuickPrice: (r) => openQuickAction(r, "price"),
    onOpenQuickSafety: (r) => openQuickAction(r, "safety"),
    onDelete: handleDelete,
  });

  return (
    <div className="product-workbench-page">
      <ProductHealthStrip
        stats={stats}
        statsLoading={statsLoading}
        metrics={healthMetrics}
        onCreate={openCreate}
        onImport={() => setImportModalOpen(true)}
        onOpenAiParse={() => setAiModalOpen(true)}
        onOpenBomImport={() => setBomModalOpen(true)}
        onResetFilters={resetAllFilters}
        onTaskClick={(task, scene) => {
          setProductTask(task);
          setScene(scene);
          setPage(1);
        }}
      />

      <div className="product-command-layout">
        <aside className="product-command-sidebar">
          <div className="product-command-panel">
            <div className="product-command-panel-head">
              <Space size={6}>
                <ThunderboltOutlined />
                <span className="product-command-panel-title">产品任务</span>
              </Space>
              <Button size="small" type="link" onClick={() => setAiSearchMode(true)}>
                AI搜索
              </Button>
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
                  const nextScene = TASK_SCENE_MAP[item.key];
                  if (nextScene) setScene(nextScene);
                  if (item.key === "ai_search") {
                    setScene("all");
                    setAiSearchMode(true);
                  }
                  if (item.key !== "ai_search" && aiSearchMode) {
                    setAiSearchMode(false);
                    setAiSearchResults(null);
                  }
                }}
              >
                <span className="product-task-main">
                  <span style={{ fontWeight: productTask === item.key ? 600 : 400 }}>
                    {item.label}
                  </span>
                  <StatusTag tone={item.color}>{item.count}</StatusTag>
                </span>
                <span className="product-task-note">{item.note}</span>
              </button>
            ))}
          </div>

        </aside>

        <main className="product-command-main">
          <div className="product-filter-panel">
            <div className="product-filter-primary">
              <div className="product-filter-search">
                <Input
                  placeholder={
                    aiSearchMode
                      ? "AI 语义搜索（如：高频放大器 贴片）"
                      : "自然语言搜索（如：0402 10uF MLCC）"
                  }
                  prefix={<SearchOutlined />}
                  value={q}
                  onChange={(e) => {
                    setQ(e.target.value);
                    setProductTask("all");
                    setScene("all");
                    setPage(1);
                  }}
                  allowClear
                  suffix={
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
                  }
                />
              </div>
              <div className="product-filter-fields">
                <Segmented
                  options={SCENE_OPTIONS}
                  value={scene}
                  onChange={(v) => {
                    setScene(v as SceneValue);
                    setProductTask("all");
                    setPage(1);
                  }}
                />
                <Select
                  allowClear
                  placeholder="分类"
                  style={{ width: 116 }}
                  value={category}
                  onChange={(v) => {
                    setCategory(v);
                    setPage(1);
                  }}
                  options={CATEGORIES.map((v) => ({ value: v, label: v }))}
                />
                <Select
                  allowClear
                  placeholder="品牌"
                  style={{ width: 148 }}
                  value={brandId}
                  onChange={(v) => {
                    setBrandId(v);
                    setPage(1);
                  }}
                  options={brands.map((b) => ({ value: b.id, label: getBrandSelectLabel(b) }))}
                />
                <Select
                  placeholder="库存状态"
                  style={{ width: 108 }}
                  value={stockStatus}
                  onChange={(v) => {
                    setStockStatus(v);
                    setPage(1);
                  }}
                  options={STOCK_OPTIONS}
                />
                <Select
                  allowClear
                  placeholder="产品状态"
                  style={{ width: 108 }}
                  value={productStatus}
                  onChange={(v) => { setProductStatus(v); setPage(1); }}
                  options={[{ value: "active", label: "已启用" }, { value: "draft", label: "草稿" }, { value: "frozen", label: "已冻结" }, { value: "inactive", label: "已停用" }]}
                />
                <Select
                  value={sort}
                  onChange={(v) => {
                    setSort(v);
                    setPage(1);
                  }}
                  options={SORT_OPTIONS}
                  style={{ width: 108 }}
                />
              </div>
            </div>

            <div className="product-filter-secondary">
              <div className="product-filter-views">
                <Select
                  value={activeSavedView || undefined}
                  allowClear
                  placeholder="选择保存视图"
                  style={{ width: 168 }}
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
                <Button icon={<SaveOutlined />} onClick={openSaveCurrentView}>
                  保存视图
                </Button>
                {activeSavedView && (
                  <Popconfirm
                    title={`删除视图「${activeSavedView}」？`}
                    onConfirm={deleteCurrentView}
                  >
                    <Button danger type="text">
                      删除
                    </Button>
                  </Popconfirm>
                )}
              </div>
              <div className="product-filter-actions">
                <Button icon={<ReloadOutlined />} onClick={resetAllFilters}>
                  重置筛选
                </Button>
                <Button icon={<UploadOutlined />} onClick={() => setImportModalOpen(true)}>
                  导入
                </Button>
                <Button icon={<DownloadOutlined />} onClick={handleExportAll}>
                  导出
                </Button>
                <Popover
                  content={
                    <Checkbox.Group
                      options={allColKeys.map((k) => ({ label: COL_LABEL_MAP[k] || k, value: k }))}
                      value={visibleCols}
                      onChange={(vals) => setVisibleCols(vals as string[])}
                    />
                  }
                  title="显示列"
                  trigger="click"
                >
                  <Button icon={<SettingOutlined />}>显示列</Button>
                </Popover>
              </div>
            </div>
            {(searchText ||
              scene !== "all" ||
              category ||
              brandId ||
              stockStatus ||
              aiSearchMode) && (
              <div className="product-active-filters">
                <span>已生效：</span>
                {searchText && (
                  <Tag closable onClose={() => setQ("")}>
                    关键词：{searchText}
                  </Tag>
                )}
                {scene !== "all" && (
                  <Tag
                    closable
                    onClose={() => {
                      setScene("all");
                      setProductTask("all");
                      setPage(1);
                    }}
                  >
                    场景：
                    {SCENE_OPTIONS.find((option) => option.value === scene)?.label ||
                      PRODUCT_TASK_LABELS[productTask]}
                  </Tag>
                )}
                {category && (
                  <Tag closable onClose={() => setCategory(undefined)}>
                    分类：{category}
                  </Tag>
                )}
                {brandId && (
                  <Tag closable onClose={() => setBrandId(undefined)}>
                    品牌：{activeBrandLabel}
                  </Tag>
                )}
                {stockStatus && (
                  <Tag closable onClose={() => setStockStatus(undefined)}>
                    库存：
                    {STOCK_OPTIONS.find((option) => option.value === stockStatus)?.label ||
                      stockStatus}
                  </Tag>
                )}
                {productStatus && (
                  <Tag closable onClose={() => setProductStatus(undefined)}>
                    产品状态：{productStatus}
                  </Tag>
                )}
                {aiSearchMode && (
                  <Tag
                    color="purple"
                    closable
                    onClose={() => {
                      setAiSearchMode(false);
                      setAiSearchResults(null);
                    }}
                  >
                    AI 语义搜索
                  </Tag>
                )}
                <Button type="link" size="small" onClick={resetAllFilters}>
                  清除全部
                </Button>
              </div>
            )}
          </div>

          {selectedRowKeys.length > 0 && !aiSearchMode && (
            <div className="product-batch-bar">
              <Space wrap>
                <StatusTag tone="info">已选 {selectedRowKeys.length} 个产品</StatusTag>
                <StatusTag>在库 {selectedMetrics.inStock}</StatusTag>
                <StatusTag tone="warning">低库存 {selectedMetrics.lowStock}</StatusTag>
                <StatusTag tone="danger">缺货 {selectedMetrics.outOfStock}</StatusTag>
              </Space>
              <Space wrap>
                <Button
                  icon={<SettingOutlined />}
                  onClick={() => {
                    setBatchTaskType("update");
                    setBatchTaskConfirm(false);
                    batchEditForm.resetFields();
                    setBatchTaskModalOpen(true);
                  }}
                >
                  批量任务面板
                </Button>
                <Button onClick={() => setSelectedRowKeys([])}>清空选择</Button>
              </Space>
            </div>
          )}

          {contextProduct && (
            <div className="product-context-strip">
              <div className="product-context-identity">
                <a className="product-context-name" onClick={() => openDetail(contextProduct)}>
                  {contextProduct.name}
                </a>
                <span className="product-context-meta">
                  {[
                    contextProduct.sku,
                    contextProduct.brand_name,
                    contextProduct.category,
                    contextProduct.package_type,
                  ]
                    .filter(Boolean)
                    .join(" / ") || "暂无基础信息"}
                </span>
              </div>
              <div className="product-context-stat">
                <strong>{getAvailableQty(contextProduct)}</strong>
                <span>可用库存</span>
              </div>
              <div className="product-context-stat">
                <strong>{contextProduct.safety_stock ?? "-"}</strong>
                <span>安全库存</span>
              </div>
              <div className="product-context-stat">
                <strong>{contextProduct.supplier_count ?? 0}</strong>
                <span>供应商</span>
              </div>
              <div className="product-context-stat">
                <strong>{contextPriorityScore}</strong>
                <span>处理优先级</span>
              </div>
              <div className="product-context-recommendation">
                <span>建议动作</span>
                <strong>{contextSuggestedAction}</strong>
              </div>
              <div className="product-context-buttons">
                <Tooltip title="查看详情">
                  <Button
                    type="text"
                    icon={<EyeOutlined />}
                    onClick={() => openDetail(contextProduct)}
                  />
                </Tooltip>
                <Tooltip title="编辑产品">
                  <Button
                    type="text"
                    icon={<EditOutlined />}
                    onClick={() => openEdit(contextProduct)}
                  />
                </Tooltip>
                <Tooltip title="快捷改价">
                  <Button type="text" onClick={() => openQuickAction(contextProduct, "price")}>
                    改价
                  </Button>
                </Tooltip>
                <Tooltip title="修改安全库存">
                  <Button type="text" onClick={() => openQuickAction(contextProduct, "safety")}>
                    安库
                  </Button>
                </Tooltip>
              </div>
            </div>
          )}

          <div className="product-table-panel erp-table">
            <div className="product-table-header">
              <div className="product-table-title">
                <strong>{aiSearchMode ? "AI 搜索结果" : `产品台账 · ${currentListTitle}`}</strong>
                <span>共 {currentListTotal} 条 · 固定 SKU/产品名称</span>
              </div>
              <Space size={6}>
                {aiSearchMode && <StatusTag tone="processing">语义搜索</StatusTag>}
                <Button
                  size="small"
                  icon={<ReloadOutlined />}
                  onClick={() => {
                    fetch();
                    loadStats();
                  }}
                >
                  刷新
                </Button>
              </Space>
            </div>
            <Table
              rowKey="id"
              columns={columns.filter((c) => visibleCols.includes(String(c.key)))}
              dataSource={tableProducts}
              loading={aiSearchMode ? aiSearching : loading}
              size="small"
              tableLayout="fixed"
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
                if (record.status === "frozen") return "product-row-frozen";
                if (record.status === "inactive") return "product-row-inactive";
                const state = getStockState(record);
                if (state === "low") return "product-row-low";
                if (state === "out") return "product-row-out";
                return "";
              }}
              onRow={(record) => ({
                onClick: () => setContextProductId(record.id),
              })}
              locale={{
                emptyText: (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description={aiSearchMode ? "未命中语义搜索结果" : "暂无产品数据"}
                  />
                ),
              }}
              scroll={{ x: "max-content" }}
              pagination={
                aiSearchMode
                  ? false
                  : {
                      current: page,
                      pageSize: PAGE_SIZE,
                      total: currentListTotal,
                      showTotal: (count) => `共 ${count} 条`,
                      showSizeChanger: false,
                    }
              }
            />
          </div>

          {selectedRowKeys.length >= 2 && !aiSearchMode && (
            <Card
              className="product-compare-panel"
              title={`产品对比（${selectedRowKeys.length} 个）`}
              extra={
                <Button size="small" onClick={() => setSelectedRowKeys([])}>
                  清除选择
                </Button>
              }
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
                  {
                    title: "完整度",
                    dataIndex: "completion_score",
                    width: 80,
                    render: (v: number | null) => `${v ?? 0}%`,
                  },
                  { title: "供应商", dataIndex: "supplier_count", width: 70 },
                  { title: "分仓", dataIndex: "inventory_location_count", width: 60 },
                  { title: "库存", dataIndex: "quantity", width: 60 },
                  {
                    title: "可用",
                    dataIndex: "available",
                    width: 60,
                    render: (_: number, r: Product) => getAvailableQty(r),
                  },
                  { title: "安全库存", dataIndex: "safety_stock", width: 80 },
                  {
                    title: "单价",
                    dataIndex: "unit_price",
                    width: 80,
                    render: (v: number | null) => (v != null ? `¥${v.toFixed(2)}` : "-"),
                  },
                ]}
                scroll={{ x: true }}
                style={{ overflowX: "auto" }}
              />
            </Card>
          )}
        </main>
      </div>

      <Modal
        title={editing ? "编辑产品" : "新建产品"}
        open={modalOpen}
        onCancel={closeEditor}
        onOk={() => form.submit()}
        width={760}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          {editing && watchedEditorStatus && watchedEditorStatus !== "active" ? (
            <Alert
              showIcon
              type={watchedEditorStatus === "frozen" ? "warning" : "info"}
              message={watchedEditorStatus === "frozen" ? "产品已冻结" : watchedEditorStatus === "inactive" ? "产品已停用" : "产品尚未启用"}
              description="该状态会影响报价、销售订单及后续业务单据，请确认状态变更符合审批及业务规则。"
              style={{ marginBottom: 12 }}
            />
          ) : null}
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="name" label="产品名称" rules={[{ required: true, message: "请输入产品名称" }, { max: 200, message: "名称不能超过 200 个字符" }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="sku" label="SKU / 料号" rules={[{ max: 100, message: "SKU 不能超过 100 个字符" }]}>
                <Input placeholder="企业内部唯一料号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}><Form.Item name="status" label="产品状态" initialValue="active"><Select options={[{ value: "draft", label: "草稿" }, { value: "active", label: "已启用" }, { value: "frozen", label: "已冻结" }, { value: "inactive", label: "已停用" }]} /></Form.Item></Col>
            <Col span={8}><Form.Item name="product_type" label="产品类型" initialValue="finished_good"><Select options={[{ value: "finished_good", label: "成品" }, { value: "raw_material", label: "原材料" }, { value: "semi_finished", label: "半成品" }, { value: "service", label: "服务" }]} /></Form.Item></Col>
            <Col span={8}><Form.Item name="owner" label="产品负责人"><Input /></Form.Item></Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="datecode" label="生产日期">
                <Input maxLength={100} placeholder="如 2026-07-16 / 2026W18" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="category" label="分类">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="package_type" label="封装">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="unit" label="单位">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="specs" label="规格">
            <Input.TextArea rows={2} placeholder="填写关键技术参数，支持采购、报价和替代料识别" />
          </Form.Item>
          <Card size="small" title="库存控制" style={{ marginBottom: 12 }}>
            <Row gutter={12}>
              <Col span={8}><Form.Item name="default_warehouse_id" label="默认仓库"><Select allowClear showSearch optionFilterProp="label" placeholder="选择默认仓库" options={warehouses.map((w) => ({ value: w.id, label: `${w.name}${w.location ? ` · ${w.location}` : ""}` }))} /></Form.Item></Col>
              <Col span={5}><Form.Item name="batch_control" valuePropName="checked" label="批次管理"><Checkbox>启用</Checkbox></Form.Item></Col>
              <Col span={5}><Form.Item name="serial_control" valuePropName="checked" label="序列号管理"><Checkbox>启用</Checkbox></Form.Item></Col>
              <Col span={6}><Form.Item name="shelf_life_control" valuePropName="checked" label="保质期管理"><Checkbox>启用</Checkbox></Form.Item></Col>
            </Row>
            <div style={{ color: "#8c8c8c", fontSize: 12 }}>库存控制会影响收货、发货及库存台账的批次/序列号校验。</div>
          </Card>
          <Card size="small" title="价格与成本" style={{ marginBottom: 12 }}>
            <Row gutter={12}>
              <Col span={8}><Form.Item name="list_price" label="目录价"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
              <Col span={8}><Form.Item name="wholesale_price" label="批发价"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
              <Col span={8}><Form.Item name="minimum_sale_price" label="最低销售价"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
            </Row>
            <Row gutter={12}>
              <Col span={12}><Form.Item name="latest_purchase_cost" label="最新采购成本"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
              <Col span={12}><Form.Item name="weighted_avg_cost" label="加权平均成本"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
            </Row>
            <Row gutter={12}>
              <Col span={12}><Form.Item name="price_valid_from" label="价格生效日"><Input placeholder="YYYY-MM-DD" /></Form.Item></Col>
              <Col span={12}><Form.Item name="price_valid_to" label="价格失效日"><Input placeholder="YYYY-MM-DD（可留空）" /></Form.Item></Col>
            </Row>
            <div style={{ color: "#8c8c8c", fontSize: 12 }}>最低销售价用于报价与销售订单校验；成本字段用于毛利和采购分析。</div>
          </Card>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="brand_id" label="品牌">
                <Select
                  allowClear
                  placeholder="选择品牌"
                  options={brands.map((b) => ({ value: b.id, label: getBrandSelectLabel(b) }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="image_url" label="图片URL">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
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
                    <Select
                      allowClear
                      placeholder="保持不变"
                      options={brands.map((b) => ({ value: b.id, label: getBrandSelectLabel(b) }))}
                    />
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
            <StatusTag tone="danger">
              该任务将删除 {selectedRowKeys.length} 条产品记录（软删除）
            </StatusTag>
          )}
          {batchTaskType === "export" && (
            <StatusTag tone="info">将导出 {selectedRowKeys.length} 条已选产品记录</StatusTag>
          )}

          <Checkbox
            checked={batchTaskConfirm}
            onChange={(e) => setBatchTaskConfirm(e.target.checked)}
          >
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

      <ProductDetailDrawer
        open={detailOpen}
        loading={detailLoading}
        product={detailProduct}
        inventories={detailInventories}
        sales={detailSales}
        onClose={() => setDetailOpen(false)}
        onEdit={(product) => {
          setDetailOpen(false);
          navigate(`/products/${product.id}/edit`);
        }}
        onOpenFullDetail={(product) => {
          setDetailOpen(false);
          navigate(`/products/${product.id}`);
        }}
      />

      <Modal
        title="AI 智能解析"
        open={aiModalOpen}
        onCancel={() => setAiModalOpen(false)}
        onOk={handleAiParse}
        confirmLoading={aiParsing}
        okText="解析并填充表单"
      >
        <p style={{ color: "#888", marginBottom: 8 }}>
          粘贴料号、型号、数据手册描述或供应商报价文本，AI 自动提取产品信息
        </p>
        <Input.TextArea
          rows={6}
          placeholder={
            "例如：\nSamsung CL05A105KP5NNNC\n0402 1uF ±10% 10V X5R MLCC\n原装正品，整盘4000PCS"
          }
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
        <p style={{ color: "#888", marginBottom: 8 }}>
          粘贴 BOM 清单，AI 逐行解析并自动创建产品。支持多行粘贴。
        </p>
        <Input.TextArea
          rows={10}
          placeholder={
            "例如：\n1 GRM155R61A105KE15 1uF 16V 0402 X5R 10% 100pcs\n2 CL05A105KP5NNNC 1uF 10V 0402 X5R 10% 200pcs"
          }
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
          支持 CSV / XLSX 文件，列：
          <code>name, sku, category, brand, package_type, specs, unit, notes</code>
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
            const headers = [
              "name",
              "sku",
              "category",
              "brand",
              "package_type",
              "specs",
              "unit",
              "notes",
            ];
            const sample = [
              "8658B传感器",
              "8658B",
              "传感器",
              "QST",
              "BGA",
              "原装正品",
              "pcs",
              "导入备注",
            ];
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
