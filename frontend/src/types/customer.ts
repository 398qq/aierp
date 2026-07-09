export interface Customer {
  id: number;
  code: string | null;
  name: string;
  short_name: string | null;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  address: string | null;
  tax_id: string | null;
  unified_social_credit_code: string | null;
  registration_number: string | null;
  invoice_title: string | null;
  invoice_address: string | null;
  invoice_phone: string | null;
  bank_name: string | null;
  bank_account: string | null;
  industry: string | null;
  level: string | null;
  source: string | null;
  customer_type: string | null;
  region: string | null;
  price_tier: string | null;
  annual_revenue: number | null;
  employee_count: number | null;
  credit_limit: number | null;
  credit_level: string | null;
  tax_rate: number | null;
  payment_terms: string | null;
  payment_method: string | null;
  currency: string;
  delivery_address: string | null;
  default_incoterm: string | null;
  status: string | null;
  total_amount: number | null;
  lifecycle: string | null;
  last_contacted_at: string | null;
  created_at: string;
  owner: string | null;
  notes: string | null;
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

export interface GlobalFollowUp extends Omit<FollowUpReminder, "due_bucket" | "planned_at"> {
  due_bucket: "overdue" | "today" | "upcoming" | "unscheduled" | "closed";
  planned_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  result: string | null;
  assigned_to: string | null;
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
