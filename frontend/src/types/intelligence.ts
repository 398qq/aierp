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
  supplier_sku?: string | null;
  currency?: string;
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
  /** New in 2026-06: AI-generated insights (or heuristic fallback). */
  insights?: Omit<Global360, "data" | "insights" | "ai_available" | "last_error">;
  /** New in 2026-06: raw aggregated data (always returned, even if AI fails). */
  data?: {
    sales?: { mtd_revenue: number; qtd_revenue: number; ytd_revenue: number;
              top_products_30d: { id: number; name: string; sku: string; revenue: number }[];
              top_customers_30d: { id: number; name: string; revenue: number }[] };
    customer?: { total_customers: number; new_customers_30d: number;
                active_customers_30d: number; activity_rate_pct: number };
    supply_chain?: { pending_po_count: number; pending_po_amount: number;
                     low_stock_product_count: number; out_of_stock_product_count: number;
                     top_suppliers_30d: { id: number; name: string; total: number }[] };
    finance?: { total_ar: number; open_invoice_count: number; overdue_ar: number;
                total_ap: number; receipts_mtd: number; payments_mtd: number; net_cash_flow_mtd: number };
    ticket?: { open_tickets: number; avg_resolution_hours: number | null;
               hotspot_categories: { category: string; count: number }[] };
    anomalies?: { message?: string };
  };
  /** New in 2026-06: false when AI failed and insights are heuristic. */
  ai_available?: boolean;
  /** New in 2026-06: error message if AI failed. */
  last_error?: string | null;
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
