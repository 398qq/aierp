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
  last_contacted_at: string | null;
  created_at: string;
  owner: string | null;
  parent_id: number | null;
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
  category: string | null; package_type: string | null; specs: string | null;
  unit: string | null; notes: string | null; image_url: string | null;
  created_at: string;
}

export interface Brand {
  id: number; name: string; name_cn: string | null; website: string | null; category: string | null; notes: string | null;
  product_count?: number;
  created_at?: string;
  updated_at?: string | null;
}

export interface Supplier {
  id: number; name: string; contact_person: string | null; phone: string | null;
  email: string | null; address: string | null; product_lines: string | null;
  notes: string | null; created_at: string;
}

export interface Warehouse {
  id: number; name: string; location: string | null; description: string | null;
}

export interface InventoryItem {
  id: number; product_id: number; warehouse_id: number;
  quantity: number; safety_stock: number; created_at: string;
  sku?: string; product_name?: string; category?: string;
  brand_name?: string; warehouse_name?: string;
}

// Sales
export interface Opportunity {
  id: number; customer_id: number; name: string; amount: number;
  stage: string; probability: number;
  expected_close_date: string | null; actual_close_date: string | null;
  notes: string | null; created_at: string;
}

export interface QuotationItem {
  id: number; quotation_id: number; product_id: number;
  quantity: number; unit_price: number; amount: number;
}

export interface Quotation {
  id: number; quotation_no: string | null; customer_id: number;
  status: string; total_amount: number; valid_until: string | null;
  notes: string | null; created_at: string;
  items?: QuotationItem[];
}

export interface SalesOrderItem {
  id: number; order_id: number; product_id: number;
  quantity: number; unit_price: number; amount: number;
}

export interface SalesOrder {
  id: number; order_no: string | null; customer_id: number;
  status: string; total_amount: number; delivery_date: string | null;
  notes: string | null; created_at: string;
  items?: SalesOrderItem[];
}

export interface DeliveryNoteItem {
  id: number; delivery_note_id: number; product_id: number; quantity: number;
}

export interface DeliveryNote {
  id: number; note_no: string | null; sales_order_id: number;
  customer_id: number; status: string;
  delivery_date: string | null; signed_at: string | null;
  notes: string | null; created_at: string;
  items?: DeliveryNoteItem[];
}

// Transactions
export interface PurchaseOrder {
  id: number; order_no: string | null; supplier_id: number;
  status: string; total_amount: number; expected_date: string | null;
  notes: string | null; created_at: string;
}

export interface Payment {
  id: number; payment_no: string | null; customer_id: number | null;
  supplier_id: number | null; type: string; amount: number;
  method: string | null; paid_at: string | null;
  notes: string | null; created_at: string;
}

export interface Ticket {
  id: number; ticket_no: string | null; customer_id: number | null;
  title: string; description: string | null; status: string; priority: string;
  category: string | null; assigned_to: string | null;
  resolved_at: string | null; notes: string | null; created_at: string;
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

// Sales Funnel
export interface FunnelStage {
  stage: string;
  count: number;
  amount: number;
}

// Sales Stats
export interface SalesSummary {
  total_orders: number;
  total_amount: number;
  avg_amount: number;
  active_opportunities: number;
}

export interface TrendPoint {
  period: string;
  order_count: number;
  total_amount: number;
}

export interface StageDistribution {
  stage: string;
  count: number;
  percentage: number;
}

// AI Sales
export interface SalesRecommendation {
  recommended_products: string[];
  opportunity_suggestion: string;
  cross_sell_opportunities: string;
  priority_action: string;
}

export interface WinPrediction {
  win_probability: number;
  confidence: string;
  key_factors: string[];
  recommendation: string;
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

export interface QuotationHistory {
  quotations: Quotation[];
  total: number;
  stats: {
    won: number;
    lost: number;
    pending: number;
    conversion_rate: number;
    total_won_amount: number;
  };
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
export interface PaymentRecord {
  id: number; sales_order_id: number; customer_id: number;
  amount: number; payment_date: string | null; payment_method: string;
  status: string; notes: string | null; created_at: string;
}

export interface PaymentSummary {
  received_total: number; pending_total: number; overdue_total: number;
}

// Invoice
export interface Invoice {
  id: number; invoice_no: string | null; sales_order_id: number;
  customer_id: number; amount: number; tax_amount: number;
  invoice_date: string | null; invoice_type: string; status: string;
  notes: string | null; created_at: string;
}

// Sales Target
export interface SalesTarget {
  id: number; user_id: number; target_amount: number;
  target_type: string; actual_amount: number;
  period_start: string | null; period_end: string | null;
  status: string; created_at: string;
}

export interface TargetSummary {
  items: SalesTarget[]; total_target: number; total_actual: number;
  overall_completion_rate: number;
}

// Contract
export interface Contract {
  id: number; contract_no: string | null; customer_id: number;
  sales_order_id: number | null; title: string; amount: number;
  signed_date: string | null; expire_date: string | null;
  status: string; file_url: string | null; notes: string | null;
  created_at: string;
  sales_order?: { id: number; order_no: string | null; status: string; total_amount: number };
  invoices?: { id: number; invoice_no: string | null; amount: number; status: string }[];
  payments?: { id: number; amount: number; payment_method: string; status: string }[];
}

// Notification
export interface NotificationItem {
  id: number; user_id: number; type: string; title: string;
  content: string | null; related_id: number | null;
  is_read: boolean; created_at: string;
}

// Dashboard
export interface DashboardOverview {
  today_orders: number; today_order_amount: number;
  today_opportunities: number; active_opportunities: number;
  won_amount: number; total_customers: number;
}

export interface DashboardRealtime {
  order_status: { status: string; count: number; amount: number }[];
  top_customers: { name: string; amount: number }[];
  top_products: { name: string; count: number }[];
}

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
export interface QuoteAssistEnrichedItem {
  product_id: number; product_name: string; brand: string; category: string;
  quantity: number; stock_qty: number; supplier_count: number; min_cost: number | null;
  historical_prices: number[]; risk_flags: string[];
}

export interface QuoteAssistResult {
  win_probability: number; win_probability_reason: string;
  pricing_recommendations: { product_name: string; recommended_price: number; price_range_low: number; price_range_high: number; margin_pct: number; rationale: string }[];
  cross_sell_suggestions: { brand_name: string; product_name: string; reason: string; estimated_value: number }[];
  risk_summary: string; negotiation_tips: string[];
  customer_info?: Record<string, unknown>;
  enriched_items?: QuoteAssistEnrichedItem[];
}

// Watchtower
export interface WatchtowerResult {
  scanned_at: string; total_alerts: number; severity: string; summary: string;
  top_actions: string[]; risk_areas: string[];
  anomalies: {
    churn_risk: { customer_id: number; name: string; level: string; industry: string; signal: string }[];
    order_drop: { customer_id: number; name: string; prev_orders: number; recent_orders: number; drop_pct: number }[];
    low_stock: { product_id: number; product_name: string; brand: string; qty: number; safety: number }[];
    out_of_stock: { product_id: number; product_name: string; brand: string }[];
  };
}

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

// Customer Insight
export interface CustomerInsight {
  customer: Record<string, unknown>;
  order_summary: { total_orders: number; total_amount: number; avg_order_amount: number; last_order_date: string | null };
  product_distribution: { product_id: number; product_name: string; quantity: number; amount: number }[];
  followup_summary: { total_followups: number; last_followup: string | null; pending_count: number; overdue_count: number };
  opportunity_summary: { total: number; active: number; won: number; win_probability: number };
  suggestions: string[];
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
export interface PaymentDelayPrediction {
  overall_risk: string;
  risk_score: number;
  late_invoice_predictions: { invoice_no: string; amount: number; due_date: string; predicted_delay_days: number; probability: number; reason: string }[];
  dso_forecast: number;
  cash_flow_impact: string;
  recommendations: string[];
  context?: Record<string, unknown>;
}

export interface CashFlowForecast {
  cash_flow_health: string;
  health_score: number;
  forecast_7d: number;
  forecast_30d: number;
  forecast_90d: number;
  shortage_risk: string;
  shortage_timing: string;
  recommendations: string[];
  alerts: string[];
  context?: Record<string, unknown>;
}

export interface DunningStrategy {
  dunning_level: string;
  suggested_contact: string;
  suggested_timing: string;
  message_template: string;
  escalation_timeline: string;
  negotiation_strategy: string;
  risk_of_default: string;
  context?: Record<string, unknown>;
}

export interface CreditRiskAssessment {
  credit_rating: string;
  credit_score: number;
  recommended_credit_limit: number;
  payment_terms_recommendation: string;
  risk_factors: string[];
  positive_signals: string[];
  watch_list: boolean;
  action_recommendation: string;
  context?: Record<string, unknown>;
}

// ============================================================
// Sales Target Intelligence
// ============================================================
export interface TargetRecommendation {
  recommended_target: number;
  conservative_target: number;
  ambitious_target: number;
  confidence: number;
  growth_rate: number;
  key_drivers: string[];
  risk_factors: string[];
  strategy: string[];
  context?: Record<string, unknown>;
}

export interface AttainmentPrediction {
  predicted_attainment: number;
  predicted_amount: number;
  gap: number;
  confidence: number;
  trend: string;
  key_opportunities: string[];
  catch_up_plan: string[];
  early_warning: boolean;
  context?: Record<string, unknown>;
}

export interface TargetEarlyWarning {
  overall_status: string;
  risk_targets: { user_name: string; target: number; actual: number; attainment_pct: number; risk_level: string; reason: string }[];
  top_performers: { user_name: string; attainment_pct: number; highlight: string }[];
  systemic_issues: string[];
  recommendations: string[];
  forecast_attainment: number;
  context?: Record<string, unknown>;
}

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
export interface ContractExtraction {
  contract_type: string;
  key_terms: { clause: string; content: string; importance: string; risk_flag: string }[];
  payment_terms: string;
  delivery_terms: string;
  warranty_terms: string;
  liability_clauses: string;
  termination_clauses: string;
  special_conditions: string;
  missing_clauses: string[];
  overall_risk: string;
  context?: Record<string, unknown>;
}

export interface ContractRisk {
  risk_score: number;
  risk_level: string;
  financial_risk: string;
  legal_risk: string;
  operational_risk: string;
  risk_items: { item: string; risk: string; impact: string; mitigation: string }[];
  recommendation: string;
  negotiation_priority: string[];
  context?: Record<string, unknown>;
}

export interface ContractExpiry {
  expiring_soon: { contract_no: string; customer_name: string; amount: number; expire_date: string; days_left: number; renewal_probability: number; action: string }[];
  high_risk_expiries: string[];
  renewal_opportunities: string[];
  total_at_risk_amount: number;
  priority_actions: string[];
  auto_renewal_candidates: string[];
  context?: Record<string, unknown>;
}

export interface ContractRebate {
  rebate_achieved: number;
  rebate_projected: number;
  rebate_tier_progress: string;
  gap_to_next_tier: number;
  optimization_suggestions: string[];
  upsell_opportunities: string[];
  margin_impact: string;
  context?: Record<string, unknown>;
}

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

export interface Global360 {
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
