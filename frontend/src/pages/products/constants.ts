// Product list constants, enums, and small pure helpers.
//
// Extracted from the 1888-line `index.tsx` so the page module only
// holds orchestrating state + JSX. Anything that doesn't need React
// state lives here.

import type { Brand, Product } from "../../types";

export type SceneValue =
  | "all"
  | "in_stock"
  | "low_stock"
  | "out_of_stock"
  | "pending_completion"
  | "stale_30d"
  | "no_supplier";

export type BatchTaskType = "update" | "delete" | "export";

export type ProductTaskKey =
  | "replenish"
  | "out"
  | "complete"
  | "stale"
  | "no_supplier"
  | "ai_search"
  | "all";

export interface ProductStats {
  total: number;
  in_stock_count: number;
  out_of_stock_count: number;
  low_stock_count: number;
  pending_completion_count: number;
  stale_30d_count: number;
  no_supplier_count: number;
}

export interface SavedView {
  name: string;
  scene: SceneValue;
  q: string;
  category?: string;
  brandId?: number;
  stockStatus?: string;
  sort: string;
  visibleCols: string[];
}

export interface ProductSalesData {
  quotations: Record<string, unknown>[];
  orders: Record<string, unknown>[];
  deliveries: Record<string, unknown>[];
}

export const CATEGORIES = [
  "MLCC",
  "IC",
  "电阻",
  "电容",
  "连接器",
  "晶体管",
  "传感器",
  "电源管理",
  "存储",
  "其他",
];

export const STOCK_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "全部" },
  { value: "in_stock", label: "在库" },
  { value: "out_of_stock", label: "缺货" },
  { value: "low_stock", label: "低库存" },
];

export const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "created_at_desc", label: "最新优先" },
  { value: "created_at_asc", label: "最旧优先" },
  { value: "name_asc", label: "名称升序" },
  { value: "name_desc", label: "名称降序" },
];

export const SCENE_OPTIONS: { label: string; value: SceneValue }[] = [
  { label: "全部", value: "all" },
  { label: "待补货", value: "low_stock" },
  { label: "缺货", value: "out_of_stock" },
  { label: "待完善", value: "pending_completion" },
  { label: "30天无动销", value: "stale_30d" },
];

export const TASK_SCENE_MAP: Partial<Record<ProductTaskKey, SceneValue>> = {
  replenish: "low_stock",
  out: "out_of_stock",
  complete: "pending_completion",
  stale: "stale_30d",
  no_supplier: "no_supplier",
  all: "all",
};

export const PRODUCT_TASK_LABELS: Record<ProductTaskKey, string> = {
  replenish: "补货预警",
  out: "缺货处理",
  complete: "资料完善",
  stale: "无动销复盘",
  no_supplier: "供应商缺口",
  ai_search: "AI选型搜索",
  all: "全部产品",
};

export const COL_LABEL_MAP: Record<string, string> = {
  sku: "SKU",
  name: "产品名称",
  mpn: "MPN",
  status: "产品状态",
  product_type: "产品类型",
  brand_name: "品牌",
  owner: "负责人",
  category: "分类",
  package: "封装",
  compliance: "合规",
  unit: "单位",
  specs: "规格",
  completion_score: "完整度",
  supplier_count: "供应商",
  stock_state: "库存状态",
  quantity: "库存",
  available: "可用",
  list_price: "列表价",
  minimum_sale_price: "最低销售价",
  weighted_avg_cost: "加权平均成本",
  currency: "币种",
  last_sale_at: "最近销售",
  actions: "操作",
};

export const PAGE_SIZE = 20;
export const SAVED_VIEW_STORAGE_KEY = "aierp.products.saved_views.v1";

// === Pure helpers (no React, no JSX) =====================================

export const getBrandSelectLabel = (brand: Brand): string =>
  brand.name || brand.short_name || brand.name_cn || "";

export const getAvailableQty = (p: Product): number => {
  if (typeof p.available === "number") return p.available;
  return (p.quantity ?? 0) - (p.locked_quantity ?? 0);
};

export const getStockState = (p: Product): "in" | "low" | "out" => {
  const available = getAvailableQty(p);
  const safety = p.safety_stock ?? 0;
  if (available <= 0) return "out";
  if (available <= safety) return "low";
  return "in";
};

export const getDaysSince = (value?: string | null): number | null => {
  if (!value) return null;
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return null;
  return Math.floor((Date.now() - time) / (24 * 60 * 60 * 1000));
};

export const getProductPriorityScore = (product: Product): number => {
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

export const getProductSuggestedAction = (product: Product): string => {
  const stockState = getStockState(product);
  if (stockState === "out") return "优先确认可替代库存或发起采购补货";
  if (stockState === "low") return "检查安全库存并补充采购计划";
  if ((product.completion_score ?? 100) < 60) return "补齐品牌、封装、规格和资料字段";
  if ((product.supplier_count ?? 0) <= 0) return "补充可供货供应商并维护采购关系";
  const staleDays = getDaysSince(product.last_sale_at);
  if (staleDays == null || staleDays > 30) return "复盘动销，生成客户推荐或清理策略";
  return "维护价格与库存，保持可销售状态";
};

export const formatDateTime = (value?: string | null): string => {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
};

export const exportProductsCsv = (rows: Product[], filename: string): boolean => {
  if (!rows.length) return false;
  const headers = [
    "SKU",
    "产品名称",
    "分类",
    "封装",
    "规格",
    "单位",
    "品牌",
    "完整度",
    "供应商数",
    "分仓数",
    "库存",
    "可用",
    "锁定",
    "安全库存",
    "单价",
    "最近销售",
  ];
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
  const csv = [headers, ...body]
    .map((row) => row.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","))
    .join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  return true;
};
