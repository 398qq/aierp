// Customer Insight
export interface CustomerInsight {
  customer: Record<string, unknown>;
  order_summary: { total_orders: number; total_amount: number; avg_order_amount: number; last_order_date: string | null };
  product_distribution: { product_id: number; product_name: string; quantity: number; amount: number }[];
  followup_summary: { total_followups: number; last_followup: string | null; pending_count: number; overdue_count: number };
  opportunity_summary: { total: number; active: number; won: number; win_probability: number };
  suggestions: string[];
}

// Notification
export interface NotificationItem {
  id: number; user_id: number; type: string; title: string;
  content: string | null; related_id: number | null;
  is_read: boolean; created_at: string;
}

// Group & Alerts
export interface GroupStats {
  members: number;
  all_ids: number[];
  agg_revenue: number;
  agg_orders: number;
  agg_credit: number;
}

export interface AlertRule {
  id: number;
  name: string;
  rule_type: string;
  threshold_days: number | null;
  threshold_pct: number | null;
  threshold_amount: number | null;
  enabled: boolean;
  severity: string;
}

export interface AlertEvent {
  id: number;
  customer_id: number;
  rule_type: string;
  rule_name: string;
  severity: string;
  message: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}


export interface LevelRule {
  id: number;
  name: string;
  target_level: string;
  condition_type: string;
  operator: string;
  threshold_value: number;
  period_days: number | null;
  enabled: boolean;
  priority: number;
}

// Payment Records


// Invoice

// Sales Target


// Contract
export interface Contract {
  id: number; contract_no: string | null; customer_id: number;
  sales_order_id: number | null; title: string; amount: number;
  currency: string;
  signed_date: string | null; expire_date: string | null;
  status: string; file_url: string | null; notes: string | null;
  delivery_address?: string | null; delivery_terms?: string | null;
  payment_terms?: string | null; acceptance_terms?: string | null;
  warranty_terms?: string | null; dispute_terms?: string | null;
  invoice_type?: string | null;
  created_at: string; updated_at?: string | null;
}

// Notification

// Dashboard


// Product Intelligence
export interface ProductProfile {
  market_positioning: string;
  typical_applications: string[];
  competitor_products: string[];
  target_customers: string[];
  lifecycle_stage: string;
  lifecycle_score: number;
  margin_potential: string;
  demand_stability: string;
  key_selling_points: string[];
  risk_factors: string[];
  context?: Record<string, unknown>;
}

export interface NormalizedSpec {
  key: string;
  value: string;
  unit: string | null;
  display: string;
}

export interface ProductAssociation {
  product_id: number;
  sku: string;
  name: string;
  category: string;
  package_type: string | null;
  brand_name: string | null;
  co_purchase_count: number;
  co_quantity: number;
}

export interface ProcurementPlan {
  recommended_plan: string;
  allocations: { supplier_name: string; quantity: number; unit_cost: number; subtotal: number; delivery_days: number; reason: string }[];
  total_cost: number;
  avg_unit_cost: number;
  delivery_risk: string;
  alternative_plan: string;
  negotiation_tips: string[];
  context?: Record<string, unknown>;
}

// Brand Intelligence
export interface BrandProfile {
  market_position: string;
  brand_strength_score: number;
  technology_advantages: string[];
  target_markets: string[];
  competitive_advantages: string[];
  typical_applications: string[];
  key_competitors: string[];
  procurement_difficulty: string;
  price_positioning: string;
  recommendation: string;
  context?: Record<string, unknown>;
}

export interface BrandPortfolio {
  portfolio_strength: string;
  category_analysis: { category: string; count: number; pct: number; assessment: string }[];
  growth_areas: string[];
  gap_analysis: string[];
  cross_sell_opportunities: string[];
  inventory_health: string;
  context?: Record<string, unknown>;
}

export interface BrandComparison {
  comparison_summary: string;
  dimension_scores: { dimension: string; a_score: number; b_score: number; note: string }[];
  switching_feasibility: string;
  switching_notes: string[];
  recommended_strategy: string;
  brand_a?: Record<string, unknown>;
  brand_b?: Record<string, unknown>;
  overlap?: Record<string, unknown>;
}

export interface SimilarBrand {
  id: number;
  name: string;
  name_cn: string | null;
  category: string | null;
  product_count: number;
  shared_categories: number;
}

export interface BrandImport {
  name: string;
  name_cn: string | null;
  category: string;
  website: string | null;
  description: string;
  product_lines: string;
  created_id?: number;
}

// Brand Health Dashboard
export interface BrandHealth {
  overall_health_score: number;
  health_label: string;
  revenue_assessment: string;
  margin_assessment: string;
  customer_assessment: string;
  inventory_assessment: string;
  trend_direction: string;
  risk_signals: string[];
  improvement_suggestions: string[];
  context?: Record<string, unknown>;
}

// Brand Risk Assessment
export interface BrandRisk {
  risk_score: number;
  risk_level: string;
  supplier_risk: string;
  lifecycle_risk: string;
  concentration_risk: string;
  market_risk: string;
  top_risks: string[];
  mitigation_suggestions: string[];
  context?: Record<string, unknown>;
}

// Brand-Supplier Matrix
export interface BrandSupplierMatrix {
  overall_assessment: string;
  coverage_score: number;
  single_source_products: { product_name: string; supplier: string; cost_price: number; risk_reason: string }[];
  backup_recommendations: { current: string; recommended: string; reason: string }[];
  price_optimization: string[];
  negotiation_leverage: string;
  context?: Record<string, unknown>;
  supplier_details?: { supplier_id: number; supplier_name: string; product_count: number; avg_cost: number | null; min_cost: number | null; max_cost: number | null; avg_lead_time: number | null }[];
}

// Brand Recommendation
export interface BrandRecommendation {
  recommendation_summary: string;
  recommended_brands: { brand_name: string; overlap_score: number; reason: string; priority: string }[];
  cross_sell_strategies: string[];
  target_industries: string[];
  expected_conversion: string;
  context?: Record<string, unknown>;
  co_purchase_raw?: { id: number; name: string; name_cn: string | null; category: string | null; shared_customers: number; shared_products: number }[];
}

// Quote Assistant
