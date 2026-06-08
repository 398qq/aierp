// Transactions
export interface PurchaseOrder {
  id: number; order_no: string | null; supplier_id: number;
  supplier_name?: string;
  status: string; total_amount: number; expected_date: string | null;
  notes: string | null; created_at: string;
}

export interface PaymentRecord {
  id: number; sales_order_id: number; customer_id: number;
  delivery_note_id: number | null;
  amount: number; payment_date: string | null;
  payment_method: string; status: string;
  currency: string; transaction_ref: string | null;
  bank_account: string | null;
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
  reasons?: string[];
  customer_a: { id: number; name: string; phone: string | null; owner: string | null };
  customer_b: { id: number; name: string; phone: string | null; owner: string | null };
}

export interface MergeResult {
  merged: boolean;
  transferred: Record<string, number>;
}
