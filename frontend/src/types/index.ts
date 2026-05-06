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
  contacts?: Contact[];
  follow_ups?: FollowUp[];
  tags?: Tag[];
}

export interface Tag {
  id: number;
  name: string;
  color: string | null;
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
  id: number; name: string; name_cn: string | null; website: string | null; category: string | null;
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
}

// Sales
export interface Opportunity {
  id: number; customer_id: number; name: string; amount: number;
  stage: string; probability: number;
  expected_close_date: string | null; actual_close_date: string | null;
  notes: string | null; created_at: string;
}

export interface Quotation {
  id: number; quotation_no: string | null; customer_id: number;
  status: string; total_amount: number; valid_until: string | null;
  notes: string | null; created_at: string;
}

export interface SalesOrder {
  id: number; order_no: string | null; customer_id: number;
  status: string; total_amount: number; delivery_date: string | null;
  notes: string | null; created_at: string;
}

export interface DeliveryNote {
  id: number; note_no: string | null; sales_order_id: number;
  customer_id: number; status: string;
  delivery_date: string | null; signed_at: string | null;
  notes: string | null; created_at: string;
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
