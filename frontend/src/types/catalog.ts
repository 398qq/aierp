// Product & Inventory
export interface Product {
  id: number; sku: string | null; name: string; brand_id: number | null;
  brand_name: string | null;
  category: string | null; package_type: string | null; specs: string | null;
  unit: string | null; notes: string | null; image_url: string | null;
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
  notes: string | null; supplier_type: string | null; certifications: string | null;
  payment_terms: string | null; region: string | null; website: string | null;
  financial_rating: string | null; created_at: string; updated_at?: string | null;
}

export interface Warehouse {
  id: number; name: string; location: string | null; description: string | null;
}

export interface InventoryItem {
  id: number; product_id: number; warehouse_id: number;
  quantity: number; safety_stock: number; locked_quantity: number; created_at: string;
  sku?: string; product_name?: string; category?: string;
  brand_name?: string; warehouse_name?: string;
  available_quantity?: number;
  unit_price?: number | null;
}
