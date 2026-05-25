export interface APIResponse<T = unknown> {
  code: number;
  msg: string;
  data: T;
}

export interface PageData<T> {
  list: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Customer {
  id: number;
  code: string | null;
  name: string;
  short_name: string | null;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  industry: string | null;
  level: string | null;
  source: string | null;
  notes: string | null;
  customer_type: string | null;
  region: string | null;
  credit_limit: number | null;
  credit_level: string | null;
  lifecycle: string | null;
  last_contacted_at: string | null;
  created_at: string;
  owner: string | null;
  parent_id: number | null;
  health_score: number | null;
  health_label: string | null;
  contacts?: Contact[];
  follow_ups?: FollowUp[];
  tags?: Tag[];
}

export interface Tag {
  id: number;
  name: string;
  color: string | null;
}

export interface Attachment {
  id: number;
  original_name: string;
  file_size: number;
  content_type: string | null;
  category: string | null;
  created_at: string;
}

export interface Document {
  id: number;
  entity_type: string;
  entity_id: number;
  filename: string;
  file_size: number;
  mime_type: string | null;
  uploaded_by: number | null;
  uploader_name: string;
  created_at: string;
}

export interface DashboardWidget {
  id: number;
  widget_type: string;
  title: string | null;
  config: Record<string, unknown>;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
  enabled: boolean;
}

export interface KpiData {
  month_revenue: number;
  new_customers: number;
  open_opportunities: number;
  pending_purchase_orders: number;
  outstanding_ar: number;
  low_stock_items: number;
  total_products: number;
  total_customers: number;
}

export interface OverdueFollowUp {
  id: number;
  customer_id: number;
  customer_name: string;
  owner: string | null;
  method: string | null;
  priority: string | null;
  planned_at: string;
  status: string | null;
  content: string | null;
  overdue_days: number;
}

export interface FollowUpReminder extends OverdueFollowUp {
  due_bucket: "overdue" | "today" | "upcoming";
  days_until: number | null;
}

export interface DashboardStats {
  total: number;
  by_industry: { name: string; value: number }[];
  by_level: { name: string; value: number }[];
  by_region: { name: string; value: number }[];
  by_source: { name: string; value: number }[];
  by_type: { name: string; value: number }[];
  monthly: { month: string; count: number }[];
}

export interface CustomerStats {
  lifecycle: string;
  created_days: number;
  order_count: number;
  total_revenue: number;
  last_order_date: string | null;
  credit_limit: number;
  outstanding: number;
  paid_total: number;
  credit_usage_pct: number;
  aging: Record<string, number>;
  health_score: number;
  health_label: string;
}

export interface CustomerAIStats {
  total: number;
  ai_computed: number;
  ai_coverage_pct: number;
  rfm_tiers: Record<string, number>;
  churn_dist: Record<string, number>;
  never_contacted: number;
  stale_high_value: number;
  active_30d: number;
  avg_health_score: number;
  by_lifecycle: { stage: string; count: number }[];
  high_churn_count: number;
}

export interface CustomerRecognition {
  name: string | null;
  short_name: string | null;
  customer_type: string | null;
  industry: string | null;
  level: string | null;
  region: string | null;
  source: string | null;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  owner: string | null;
  credit_limit: number | null;
  credit_level: string | null;
  address: string | null;
  notes: string | null;
  confidence: number;
  summary: string | null;
  raw_text?: string | null;
  ocr_engine?: string | null;
  ocr_confidence?: number | null;
  ocr_score?: number | null;
  ocr_candidates?: Array<{
    engine: string;
    confidence: number;
    score: number;
    text_length: number;
  }> | null;
  recognition_warnings?: string[] | null;
  image_quality?: {
    width: number;
    height: number;
    megapixels: number;
    brightness: number;
    contrast: number;
    sharpness: number;
    warnings?: string[];
  } | null;
}

export interface CustomerAIWorkQueueSnapshot {
  health_score: number | null;
  churn_risk_score: number | null;
  value_score: number | null;
  urgency_score: number | null;
  recency_days: number | null;
  frequency_90d: number | null;
  monetary_180d: number | null;
  overdue_followups: number | null;
  open_opportunities: number | null;
  outstanding_amount: number | null;
}

export interface CustomerAIWorkQueueItem {
  id: number;
  customer_id: number;
  customer_name: string;
  customer_level: string | null;
  customer_industry: string | null;
  customer_owner: string | null;
  action_type: string;
  title: string;
  reason: string;
  confidence: number;
  priority_score: number;
  expected_impact: number | null;
  due_at: string | null;
  status: "open" | "in_progress" | "done" | "dismissed" | "superseded";
  owner: string | null;
  model_version: string;
  snapshot: CustomerAIWorkQueueSnapshot;
  feedback_count: number;
  created_at: string | null;
}

export interface CustomerAIWorkQueuePage {
  list: CustomerAIWorkQueueItem[];
  total: number;
  page: number;
  page_size: number;
  status_stats: Record<string, number>;
}

export interface CustomerAIRecommendationSummary {
  customer: {
    id: number;
    name: string;
    level: string | null;
    industry: string | null;
    owner: string | null;
    health_score: number | null;
    health_label: string | null;
    last_contacted_at: string | null;
  };
  snapshot: {
    snapshot_date: string | null;
    health_score: number | null;
    churn_risk_score: number | null;
    value_score: number | null;
    urgency_score: number | null;
    overdue_followups: number | null;
    open_opportunities: number | null;
    outstanding_amount: number | null;
  };
  next_actions: Array<{
    id: number;
    action_type: string;
    title: string;
    reason: string;
    priority_score: number;
    status: string;
    due_at: string | null;
  }>;
}

export interface TimelineEvent {
  type: "contact" | "followup" | "order";
  title: string;
  detail: string;
  time: string;
  id: number;
}

export interface Contact {
  id: number;
  name: string;
  title: string | null;
  role: string | null;
  phone: string | null;
  email: string | null;
  wechat: string | null;
  is_primary: boolean;
  notes: string | null;
}

export interface FollowUp {
  id: number;
  method: string | null;
  status: string | null;
  content: string | null;
  result: string | null;
  planned_at: string | null;
  completed_at: string | null;
  priority: string | null;
  assigned_to: string | null;
  created_at: string;
}

export interface FollowUpRecognition {
  method: string | null;
  status: string | null;
  content: string | null;
  result: string | null;
  planned_at: string | null;
  completed_at: string | null;
  priority: string | null;
  assigned_to: string | null;
  confidence: number;
  summary: string | null;
}

export interface RFMAnalysis {
  r_score: number;
  f_score: number;
  m_score: number;
  tier: string;
  suggestion: string;
}

export interface ChurnRisk {
  risk_score: number;
  risk_level: string;
  factors: string[];
  recommendation: string;
}

export type LoginData = { token: string; username: string; role: string };

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

// Transactions
export interface PurchaseOrder {
  id: number; order_no: string | null; supplier_id: number;
  supplier_name?: string;
  status: string; total_amount: number; expected_date: string | null;
  notes: string | null; created_at: string;
}

export interface PaymentRecord {
  id: number; sales_order_id: number; customer_id: number;
  amount: number; payment_date: string | null;
  payment_method: string; status: string;
  notes: string | null; created_at: string; updated_at: string | null;
}

export interface Invoice {
  id: number; invoice_no: string | null; sales_order_id: number;
  customer_id: number; amount: number; tax_amount: number;
  invoice_date: string | null; invoice_type: string; status: string;
  notes: string | null; created_at: string; updated_at: string | null;
}

export interface SalesTarget {
  id: number; user_id: number; target_amount: number;
  period: string | null; target_orders: number | null;
  target_type: string; period_start: string | null; period_end: string | null;
  actual_amount: number; status: string;
  created_at: string; updated_at: string | null;
}

export interface Ticket {
  id: number; ticket_no: string | null; customer_id: number | null;
  title: string; description: string | null; status: string; priority: string;
  category: string | null; assigned_to: string | null;
  resolved_at: string | null; notes: string | null; created_at: string | null;
}

export interface Visit {
  id: number; visit_no: string | null; customer_id: number; contact_id: number | null;
  title: string | null; visit_date: string | null; type: string | null;
  status: string | null; content: string | null; result: string | null;
  next_plan: string | null; stage: string | null; purpose: string | null;
  main_product: string | null; key_points: string | null;
  followup_date: string | null; created_at: string;
}

export interface Sample {
  id: number; customer_id: number; product_id: number | null;
  quantity: number; unit: string | null;
  apply_date: string | null; ship_date: string | null; receive_date: string | null;
  status: string; tracking_number: string | null; notes: string | null;
  created_at: string;
}

export interface CustomerLog {
  id: number;
  customer_id?: number;
  customer_name?: string;
  action: string;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  operator: string | null;
  summary: string | null;
  created_at: string;
}

export interface DuplicatePair {
  similarity: number;
  customer_a: { id: number; name: string; phone: string | null; owner: string | null };
  customer_b: { id: number; name: string; phone: string | null; owner: string | null };
}

export interface MergeResult {
  merged: boolean;
  transferred: Record<string, number>;
}

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
  signed_date: string | null; expire_date: string | null;
  status: string; file_url: string | null; notes: string | null;
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


// ============================================================
// Embedded AI Insights (include_ai=true on entity endpoints)
// ============================================================





// Sales Intelligence




// Watchtower

// Smart Matching
export interface CustomerProductMatch {
  recommendations: { product_name: string; brand: string; reason: string; priority: string; estimated_potential: string }[];
  summary: string; approach_strategy: string;
  candidates?: { product_id: number; product_name: string; category: string; brand: string; times_bought: number }[];
}

export interface ProductCustomerMatch {
  recommendations: { customer_name: string; reason: string; priority: string; estimated_potential: string }[];
  summary: string; outreach_strategy: string;
  candidates?: { customer_id: number; name: string; industry: string; level: string; total_orders: number; total_revenue: number }[];
}

// Brand Product Performance
export interface BrandProductPerformance {
  star_products: { product_name: string; revenue: number; margin_pct: number; growth: string; recommendation: string }[];
  problem_products: { product_name: string; issue: string; suggestion: string }[];
  portfolio_assessment: string;
  focus_recommendations: string[];
  phase_out_candidates: string[];
  context?: Record<string, unknown>;
}

// Brand Customer Penetration
export interface BrandCustomerPenetration {
  penetration_score: number;
  penetration_assessment: string;
  key_industries: { industry: string; customer_count: number; contribution_pct: number; assessment: string }[];
  untapped_industries: { industry: string; potential_customers: number; strategy: string }[];
  retention_strategy: string[];
  expansion_strategy: string[];
  context?: Record<string, unknown>;
}

// Brand Lifecycle Prediction
export interface BrandLifecycle {
  lifecycle_stage: string;
  stage_confidence: number;
  stage_evidence: string[];
  strategic_advice: string;
  next_12m_outlook: string;
  key_actions: string[];
  risk_signals: string[];
  context?: Record<string, unknown>;
}

// Brand Price Trends
export interface BrandPriceTrends {
  price_trend: string;
  trend_score: number;
  margin_assessment: string;
  competitiveness: string;
  pricing_issues: string[];
  optimization_suggestions: string[];
  opportunity_alert: string | null;
  context?: Record<string, unknown>;
}

export interface LifecycleAnalysis {
  lifecycle_stage: string;
  stage_confidence: number;
  warning_signals: string[];
  eol_risk_score: number;
  eol_estimated_months: number | null;
  stock_strategy: string;
  suggested_quantity: number;
  migration_path: string | null;
  urgency: string;
  context?: Record<string, unknown>;
}

// Supplier-Product Linkage
export interface SupplierProductLink {
  id: number;
  supplier_id?: number;
  supplier_name?: string;
  product_id: number;
  cost_price: number | null;
  lead_time_days: number | null;
  moq: number | null;
  spq: number | null;
  is_preferred: boolean;
  notes: string | null;
  sku?: string;
  product_name?: string;
  category?: string;
  package_type?: string;
  brand_name?: string;
}

// Pricing
export interface PriceBenchmark {
  product_id: number;
  sales_history: { count: number; stats: Record<string, number | null>; recent: Record<string, unknown>[] };
  active_quotations: { count: number; stats: Record<string, number | null> };
  supplier_costs: { count: number; stats: Record<string, number | null>; suppliers: Record<string, unknown>[] };
}

export interface PriceRecommendation {
  recommended_price: number;
  price_range: [number, number];
  margin_pct: number;
  confidence: string;
  rationale: string;
  negotiation_floor: number;
  upsell_suggestion: string | null;
  context?: Record<string, unknown>;
}

// ============================================================
// Supplier Intelligence
// ============================================================
export interface SupplierScorecard {
  overall_score: number;
  delivery_score: number;
  quality_score: number;
  price_score: number;
  stability_score: number;
  assessment: string;
  strengths: string[];
  weaknesses: string[];
  tier: string;
  recommendations: string[];
  context?: Record<string, unknown>;
}

export interface SupplierDelayPrediction {
  delay_risk: string;
  risk_score: number;
  predicted_delay_days: number;
  probability: number;
  risk_factors: string[];
  mitigation: string[];
  alternative_suggestion: string;
  context?: Record<string, unknown>;
}

export interface SupplierAlternatives {
  urgency: string;
  recommended_alternatives: { supplier_name: string; product_lines: string; score: number; advantage: string; switch_cost: string }[];
  diversification_strategy: string[];
  risk_assessment: string;
  context?: Record<string, unknown>;
}

export interface SupplierPriceVariance {
  price_status: string;
  variance_score: number;
  anomaly_products: { product_name: string; current_price: number; expected_price: number; variance_pct: number; reason: string }[];
  trend_analysis: string;
  cost_saving_opportunities: string[];
  negotiation_points: string[];
  context?: Record<string, unknown>;
}

export interface Supplier360 {
  overall_score: number;
  tier: string;
  summary: string;
  assessment: string;
  key_strengths: string[];
  key_weaknesses: string[];
  recommendations: string[];
  po_history_summary: { total_pos: number; total_amount: number; avg_delivery_days: number; on_time_rate: number };
  context?: Record<string, unknown>;
}

export interface SupplierNegotiation {
  negotiation_strategy: string;
  price_target: string;
  talking_points: string[];
  leverage_points: string[];
  fallback_plan: string;
  suggested_approach: string;
  context?: Record<string, unknown>;
}

export interface SupplierComparison {
  comparison_matrix: { dimension: string; weight: number; scores: Record<string, number> }[];
  overall_ranking: { rank: number; supplier_name: string; total_score: number; tier: string }[];
  best_in_category: { category: string; winner: string; reason: string }[];
  recommendation: string;
  summary: string;
  context?: Record<string, unknown>;
}

// ============================================================
// Purchase Order Intelligence
// ============================================================
export interface POOptimization {
  optimization_score: number;
  quantity_advice: { product_name: string; ordered: number; suggested: number; reason: string }[];
  supplier_split: { supplier_name: string; product_name: string; quantity: number; price: number; saving: number }[];
  timing_advice: string;
  risk_flags: string[];
  total_saving_estimate: number;
  context?: Record<string, unknown>;
}

export interface POAutoSuggest {
  urgency_level: string;
  suggested_pos: { supplier_name: string; product_name: string; quantity: number; estimated_price: number; estimated_amount: number; urgency: string; reason: string }[];
  total_estimated_amount: number;
  prioritization: string;
  inventory_health_score: number;
  context?: Record<string, unknown>;
}

export interface PORiskAssessment {
  overall_risk: string;
  risk_score: number;
  risk_factors: { factor: string; severity: string; impact: string }[];
  delivery_risk: string;
  price_risk: string;
  quality_risk: string;
  mitigation_plan: string[];
  go_no_go: string;
  context?: Record<string, unknown>;
}

// ============================================================
// Payment & AR Intelligence
// ============================================================




// ============================================================
// Sales Target Intelligence
// ============================================================



// ============================================================
// Visit Intelligence
// ============================================================
export interface VisitReport {
  visit_summary: string;
  key_achievements: string[];
  customer_sentiment: string;
  engagement_level: string;
  product_interest: string;
  opportunity_signals: string[];
  risk_signals: string[];
  action_items: { action: string; priority: string; deadline: string }[];
  followup_recommendation: string;
  effectiveness_score: number;
  context?: Record<string, unknown>;
}

export interface VisitSentiment {
  overall_sentiment: string;
  sentiment_score: number;
  key_concerns: string[];
  satisfaction_indicators: string[];
  dissatisfaction_signals: string[];
  relationship_trend: string;
  loyalty_risk: string;
  improvement_suggestions: string[];
  context?: Record<string, unknown>;
}

export interface VisitEffectiveness {
  effectiveness_score: number;
  coverage_assessment: string;
  productivity_assessment: string;
  high_performers: string[];
  gaps: string[];
  optimization_suggestions: string[];
  visit_frequency_recommendation: string;
  context?: Record<string, unknown>;
}

// ============================================================
// Ticket Intelligence
// ============================================================
export interface TicketClassification {
  category: string;
  subcategory: string[];
  priority: string;
  priority_reason: string;
  assigned_to: string;
  estimated_resolution_hours: number;
  severity: number;
  escalation_needed: boolean;
  auto_response_suggestion: string;
  context?: Record<string, unknown>;
}

export interface TicketResponse {
  diagnosis: string;
  root_cause: string;
  solution_steps: string[];
  reply_template: string;
  followup_questions: string[];
  internal_notes: string;
  faq_candidate: boolean;
  context?: Record<string, unknown>;
}

export interface TicketResolutionPrediction {
  predicted_resolution_hours: number;
  confidence: number;
  resolution_barriers: string[];
  stall_risk: string;
  escalation_probability: number;
  customer_satisfaction_prediction: string;
  acceleration_suggestions: string[];
  context?: Record<string, unknown>;
}

export interface TicketCluster {
  clusters: { cluster_name: string; ticket_count: number; root_cause: string; severity: string; trend: string }[];
  systemic_issues: string[];
  product_quality_alerts: string[];
  process_gaps: string[];
  improvement_plan: string[];
  prevention_suggestions: string[];
  context?: Record<string, unknown>;
}

// ============================================================
// Contract Intelligence
// ============================================================




// ============================================================
// Multi-Agent Orchestration
// ============================================================
export interface Customer360 {
  customer_360_score: number;
  health_summary: string;
  revenue_health: string;
  relationship_health: string;
  risk_health: string;
  cross_domain_insights: { domain: string; finding: string; impact: string; action: string }[];
  prioritized_actions: { action: string; domain: string; priority: string; expected_impact: string }[];
  opportunity_score: number;
  risk_score: number;
  next_best_action: string;
  context?: Record<string, unknown>;
}

export interface Product360 {
  product_360_score: number;
  health_summary: string;
  commercial_health: string;
  supply_health: string;
  quality_health: string;
  cross_domain_insights: { domain: string; finding: string; impact: string; action: string }[];
  prioritized_actions: { action: string; domain: string; priority: string; expected_impact: string }[];
  growth_potential: string;
  risk_flags: string[];
  next_best_action: string;
  context?: Record<string, unknown>;
}

export interface DailyReport {
  report_date: string; generated_at: string;
  metrics: {
    orders_today: number; revenue_today: number; new_customers: number;
    payments_today: number; payments_amount_today: number;
    low_stock_items: number; out_of_stock_items: number;
  };
  ai_summary: string; mood: string; top_action: string;
}

export interface Global360 {
  scanned_at?: string;
  enterprise_health_score: number;
  executive_summary: string;
  top_opportunities: { area: string; description: string; potential_value: number; effort?: string; timeframe?: string }[];
  top_risks: { area: string; description: string; severity: string; probability?: string; mitigation?: string }[];
  cross_domain_correlations: { domains: string; finding: string; significance?: string }[];
  strategic_recommendations: { recommendation: string; domain: string; priority: string; rationale?: string }[];
  kpi_health: { kpi: string; current: string; target: string; status: string }[];
  focus_areas: string[];
  context?: Record<string, unknown>;
}

// ============================================================
// NLP Query
// ============================================================
export interface NLPQueryResult {
  answer: string;
  data_summary: string;
  related_entities: { type: string; id: number; name: string; relevance: string }[];
  suggested_followups: string[];
  actions: { action: string; type: string; entity: string; urgency: string }[];
  confidence: number;
  context?: Record<string, unknown>;
}

// ============================================================
// Sales Entities
// ============================================================

export interface Opportunity {
  id: number;
  customer_id: number;
  product_id: number | null;
  title: string;
  description: string | null;
  status: string;
  stage: string | null;
  amount: number | null;
  win_probability: number | null;
  expected_close_date: string | null;
  assigned_to: string | null;
  source: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  ai?: OpportunityAI | null;
}

export interface QuotationItem {
  id: number;
  quotation_id: number;
  product_id: number | null;
  product_name: string | null;
  quantity: number;
  unit_price: number | null;
  total_price: number | null;
  notes: string | null;
}

export interface Quotation {
  id: number;
  quotation_no: string | null;
  customer_id: number;
  opportunity_id: number | null;
  title: string | null;
  total_amount: number;
  status: string;
  valid_until: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  items: QuotationItem[];
  ai?: QuotationAI | null;
}

export interface SalesOrderItem {
  id: number;
  order_id: number;
  product_id: number | null;
  product_name: string | null;
  quantity: number;
  unit_price: number | null;
  total_price: number | null;
  notes: string | null;
}

export interface SalesOrder {
  id: number;
  order_no: string | null;
  customer_id: number;
  quotation_id: number | null;
  total_amount: number;
  status: string;
  order_date: string | null;
  delivery_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  items: SalesOrderItem[];
  ai?: SalesOrderAI | null;
}

export interface DeliveryNoteItem {
  id: number;
  delivery_note_id: number;
  product_id: number | null;
  product_name: string | null;
  quantity: number;
  notes: string | null;
}

export interface DeliveryNote {
  id: number;
  delivery_no: string | null;
  sales_order_id: number;
  customer_id: number;
  status: string;
  delivery_date: string | null;
  received_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  items: DeliveryNoteItem[];
  ai?: DeliveryNoteAI | null;
}

// ============================================================
// AI Insight Types (embedded in entity responses via ?include_ai=true)
// ============================================================

export interface OpportunityAI {
  risk_level: string;
  win_probability: number;
  next_best_action: string | null;
  key_concerns: string[];
}

export interface QuotationAI {
  pricing_health: string;
  win_probability: number;
  margin_assessment: string | null;
  improvement_suggestions: string[];
}

export interface SalesOrderAI {
  delivery_risk: string;
  payment_risk: string;
  health_score: number;
  flags: string[];
}

export interface DeliveryNoteAI {
  completion_risk: string;
  signing_delay_probability: number;
  issues: string[];
}

// ============================================================
// Sales Dashboard
// ============================================================

export interface FunnelStage {
  stage: string;
  count: number;
  amount: number;
}

export interface SalesDashboardOverview {
  funnel: FunnelStage[];
  open_opportunities: number;
  won_opportunities: number;
  total_pipeline: number;
  quote_to_order_rate: number;
  opp_to_quote_rate: number;
}

export interface TrendPoint {
  month: string;
  opportunities: number;
  orders: number;
  revenue: number;
}

export interface SalesDashboardTrends {
  trends: TrendPoint[];
}

export interface AIAlert {
  id: number;
  type: string;
  title: string;
  content: string | null;
  created_at: string | null;
}

export interface SalesDashboardAlerts {
  alerts: AIAlert[];
}

export interface ConversionValidation {
  risk_level: string;
  warnings: string[];
  recommendations: string[];
}

export interface SegmentCluster {
  id: number;
  label: string;
  size: number;
  avg_similarity: number;
  sample_names: string[];
  common_industry: string;
  common_level: string;
}

export interface SimilarCustomer {
  id: number;
  name: string;
  industry: string;
  region: string;
  similarity: number;
}

export interface CustomerQuotationHistory {
  quotations: Array<{
    id: number;
    quotation_no: string;
    status: string;
    total_amount: number;
    valid_until: string | null;
    notes: string | null;
    created_at: string | null;
    items: Array<{ id: number; product_id: number; quantity: number; unit_price: number; total_price: number }>;
  }>;
  total: number;
  stats: {
    won: number;
    lost: number;
    pending: number;
    conversion_rate: number;
    total_won_amount: number;
  };
}
