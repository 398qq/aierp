// Sales Entities
// ============================================================

export interface Opportunity {
  id: number;
  customer_id: number;
  product_id: number | null;
  product_name?: string | null;
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
  customer_part_no: string | null;
  customer_product_name: string | null;
  quantity: number;
  unit: string | null;
  unit_price: number | null;
  total_price: number | null;
  tax_rate: number | null;
  discount_rate: number | null;
  cost_price: number | null;
  untaxed_cost: number | null;
  taxed_cost: number | null;
  sales_profit: number | null;
  datecode: string | null;
  lead_time: string | null;
  notes: string | null;
}

export interface Quotation {
  id: number;
  quotation_no: string | null;
  customer_id: number;
  customer_name?: string | null;
  opportunity_id: number | null;
  opportunity_title?: string | null;
  title: string | null;
  total_amount: number;
  status: string;
  currency: string;
  incoterms: string | null;
  payment_terms: string | null;
  discount_rate: number | null;
  discount_amount: number | null;
  subtotal: number | null;
  valid_until: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  items: QuotationItem[];
  ai?: QuotationAI | null;
}

export interface SalesOrder {
  id: number;
  order_no: string | null;
  customer_id: number;
  customer_name?: string | null;
  quotation_id: number | null;
  quotation_no?: string | null;
  total_amount: number;
  status: string;
  currency: string;
  incoterms: string | null;
  payment_terms: string | null;
  due_date: string | null;
  customer_po_no: string | null;
  shipping_address: string | null;
  billing_address: string | null;
  discount_rate: number | null;
  discount_amount: number | null;
  subtotal: number | null;
  order_date: string | null;
  delivery_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  items: SalesOrderItem[];
  ai?: SalesOrderAI | null;
}

export interface BusinessDocumentRef {
  id: number;
  number: string;
  status: string;
  amount?: number;
  date?: string | null;
}

export interface SalesOrderBusinessChain {
  order: BusinessDocumentRef;
  opportunity: BusinessDocumentRef | null;
  quotation: BusinessDocumentRef | null;
  contracts: BusinessDocumentRef[];
  deliveries: BusinessDocumentRef[];
  invoices: BusinessDocumentRef[];
  payments: BusinessDocumentRef[];
  item_progress: Array<{
    order_item_id: number;
    product_id: number | null;
    product_code: string | null;
    ordered_quantity: number;
    delivered_quantity: number;
    pending_quantity: number;
  }>;
  progress: {
    ordered_quantity: number;
    delivered_quantity: number;
    pending_delivery_quantity: number;
    delivery_percent: number;
    order_amount: number;
    invoiced_amount: number;
    uninvoiced_amount: number;
    invoice_percent: number;
    paid_amount: number;
    outstanding_amount: number;
    payment_percent: number;
  };
}

export interface OpportunityBusinessChain {
  opportunity: BusinessDocumentRef & { title: string; stage: string | null };
  quotations: Array<BusinessDocumentRef & { created_at?: string | null }>;
  orders: SalesOrderBusinessChain[];
  summary: {
    quotation_count: number;
    order_count: number;
    quoted_amount: number;
    ordered_amount: number;
    conversion_rate: number;
  };
}

export interface OpportunityAuditItem {
  id: string;
  event_type: "transition" | "field_change";
  action: "create" | "status_change" | "stage_change" | "delete" | "field_change" | string;
  field_name: string;
  before: string | null;
  after: string | null;
  actor: string | null;
  reason: string | null;
  occurred_at: string;
}

export interface OpportunityAuditTrail {
  list: OpportunityAuditItem[];
  total: number;
  transition_count: number;
  field_change_count: number;
}

export interface DeliveryNote {
  id: number;
  delivery_no: string | null;
  sales_order_id: number;
  sales_order_no?: string | null;
  customer_id: number;
  customer_name?: string | null;
  status: string;
  shipping_method: string | null;
  tracking_number: string | null;
  incoterms: string | null;
  delivery_date: string | null;
  received_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  items: DeliveryNoteItem[];
  ai?: DeliveryNoteAI | null;
}

export interface InvoiceLine {
  id: number;
  invoice_id: number;
  product_id: number | null;
  product_name: string | null;
  quantity: number;
  unit: string | null;
  unit_price: number | null;
  total_price: number | null;
  tax_rate: number | null;
  tax_amount: number | null;
  notes: string | null;
}

export interface Invoice {
  id: number;
  invoice_no: string | null;
  sales_order_id: number;
  delivery_note_id: number | null;
  sales_order_no?: string | null;
  customer_id: number;
  customer_name?: string | null;
  amount: number;
  tax_amount: number;
  subtotal: number | null;
  currency: string;
  due_date: string | null;
  invoice_date: string | null;
  invoice_type: string;
  status: string;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  items?: InvoiceLine[];
}

export interface QuotationStats {
  total: number;
  total_amount: number;
  draft: number;
  sent: number;
  won: number;
  lost: number;
  won_amount: number;
  expiring_soon: number;
  expired: number;
  converted: number;
  quote_to_order_rate: number;
  by_status: Record<string, { count: number; amount: number }>;
}

export interface SalesOrderItem {
  id: number;
  order_id: number;
  product_id: number | null;
  product_name: string | null;
  customer_part_no: string | null;
  customer_product_name: string | null;
  quantity: number;
  unit: string | null;
  unit_price: number | null;
  total_price: number | null;
  tax_rate: number | null;
  discount_rate: number | null;
  notes: string | null;
}

export interface DeliveryNoteItem {
  id: number;
  delivery_note_id: number;
  product_id: number | null;
  product_name: string | null;
  customer_part_no: string | null;
  customer_product_name: string | null;
  quantity: number;
  unit: string | null;
  notes: string | null;
}

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
  fallback?: boolean;
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
    items: Array<{ id: number; product_id: number | null; product_name?: string | null; quantity: number; unit_price: number; total_price: number }>;
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

// --- Commission ---

export type CommissionStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "paid"
  | "rejected"
  | "cancelled";

export interface Commission {
  id: number;
  commission_no: string | null;
  sales_order_id: number;
  sales_user_id: number;
  customer_id: number | null;
  base_amount: number;
  rate: number;
  commission_amount: number;
  paid_amount: number;
  status: CommissionStatus;
  approved_by: number | null;
  approved_at: string | null;
  paid_at: string | null;
  period: string | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CommissionCreate {
  sales_order_id: number;
  sales_user_id: number;
  base_amount?: number;
  rate?: number;
  period?: string | null;
  notes?: string | null;
}

export interface CommissionUpdate {
  base_amount?: number;
  rate?: number;
  period?: string | null;
  notes?: string | null;
  status?: CommissionStatus;
}
