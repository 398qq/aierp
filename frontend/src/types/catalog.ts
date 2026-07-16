// Product & Inventory
export interface Product {
  id: number; sku: string | null; name: string;
  status?: "draft" | "active" | "frozen" | "inactive" | string;
  product_type?: string;
  owner?: string | null;
  // 基础标识
  mpn: string | null; datecode?: string | null; barcode: string | null;
  hs_code: string | null; origin_country: string | null;
  // 归属
  brand_id: number | null; brand_name: string | null;
  category: string | null; package_type: string | null;
  // 电子属性
  package_case: string | null; pin_count: number | null;
  voltage_rating: string | null; tolerance_pct: string | null;
  temperature_range: string | null; power_rating: string | null;
  // 规格
  specs: string | null; unit: string | null;
  default_warehouse_id?: number | null;
  default_warehouse_name?: string | null;
  batch_control?: boolean;
  serial_control?: boolean;
  shelf_life_control?: boolean;
  // 物理属性
  length_mm: number | null; width_mm: number | null;
  height_mm: number | null; gross_weight_g: number | null;
  net_weight_g: number | null;
  // 商务属性
  tax_rate: number | null; currency: string;
  standard_cost: number | null; list_price: number | null;
  wholesale_price: number | null;
  minimum_sale_price?: number | null;
  price_valid_from?: string | null; price_valid_to?: string | null;
  latest_purchase_cost?: number | null; weighted_avg_cost?: number | null;
  cost_updated_at?: string | null;
  // 生命周期与合规
  lifecycle_status: string | null; eol_date: string | null;
  alternative_mpn: string | null;
  rohs_compliant: boolean; reach_compliant: boolean;
  esd_sensitive: boolean; msl_level: string | null;
  // 文档
  datasheet_url: string | null;
  rohs_cert_url: string | null; reach_cert_url: string | null;
  // 备注
  notes: string | null; image_url: string | null;
  created_at: string;
  // Inventory (joined from API)
  quantity?: number | null;
  available?: number | null;
  locked_quantity?: number | null;
  safety_stock?: number | null;
  unit_price?: number | null;
  stock_status?: "in_stock" | "low_stock" | "out_of_stock";
  inventory_location_count?: number;
  supplier_count?: number;
  completion_score?: number;
  missing_fields?: string[];
  last_sale_at?: string | null;
  inventory_updated_at?: string | null;
}

export interface Brand {
  id: number;
  // 基础
  code: string | null; name: string; name_cn: string | null; short_name: string | null;
  logo: string | null; brand_type: string | null; status: string;
  category: string | null; description: string | null; notes: string | null;
  // 商业
  level: string | null; positioning: string | null; owner: string | null;
  product_lines: string | null; target_markets: string | null; website: string | null;
  // 供应链
  supplier_id: number | null; manufacturer_name: string | null;
  authorization_status: string | null; lifecycle_stage: string | null;
  is_automotive: boolean; moq: number | null; lead_time_days: number | null;
  risk_level: string | null; rohs_status: string | null;
  // AI
  ai_keywords: string | null; risk_score: number | null; alternative_brands: string | null;
  // meta
  product_count?: number;
  has_products?: boolean;
  completion_score?: number;
  missing_fields?: string[];
  created_at?: string;
  updated_at?: string | null;
}

export interface Supplier {
  id: number; name: string; contact_person: string | null; phone: string | null;
  email: string | null; address: string | null; product_lines: string | null;
  notes: string | null;
  supplier_type: string | null; status: string;
  certifications: string | null;
  payment_terms: string | null; payment_method: string | null;
  currency: string; incoterms: string | null;
  region: string | null; website: string | null;
  financial_rating: string | null; rating_score: number | null;
  lead_time_days: number | null; min_order_value: number | null;
  last_audit_date: string | null;
  created_at: string; updated_at?: string | null;
}

export interface Warehouse {
  id: number; name: string; location: string | null; description: string | null;
  warehouse_type: string | null; is_active: boolean;
}

export interface InventoryItem {
  id: number; product_id: number; warehouse_id: number;
  quantity: number; safety_stock: number; locked_quantity: number; created_at: string;
  sku?: string; product_name?: string; mpn?: string | null; category?: string;
  brand_name?: string; warehouse_name?: string; warehouse_type?: string | null;
  available_quantity?: number;
  unit_price?: number | null;
  location_code?: string | null;
  reorder_point?: number; max_stock?: number | null;
  abc_class?: string | null; costing_method?: string;
  last_counted_at?: string | null; count_cycle_days?: number | null;
}

// BOM — Bill of Materials
export interface BOM {
  id: number; product_id: number; name: string;
  version: string; status: string; revision_notes: string | null;
  product_name?: string; product_sku?: string;
  line_count?: number;
  created_at: string; updated_at?: string | null;
}

export interface BOMLine {
  id: number; bom_id: number; child_product_id: number;
  quantity: number; unit: string | null;
  reference_designator: string | null;
  position: number; is_critical: boolean; notes: string | null;
  child_product_name?: string; child_product_sku?: string; child_product_mpn?: string | null;
}

// Inventory batch tracking
export interface InventoryBatch {
  id: number; product_id: number; warehouse_id: number;
  batch_no: string; quantity: number; unit_cost: number; total_value: number;
  received_date: string | null; expiry_date: string | null;
  status: string;
  product_name: string | null; supplier_name: string | null;
}

export interface CogsReport {
  items: {
    product_id: number; product_name: string;
    quantity: number; revenue: number; cost: number;
    margin: number; margin_pct: number;
  }[];
  summary: {
    total_revenue: number; total_cost: number;
    total_margin: number; margin_pct: number;
  };
}
