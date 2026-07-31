export type AnomalyDomain = "churn_risk" | "order_drop" | "low_stock" | "out_of_stock";

export interface AnomalyRow {
  domain: AnomalyDomain;
  domainLabel: string;
  customer_id?: number;
  product_id?: number;
  name?: string;
  signal?: string;
  prev_orders?: number;
  recent_orders?: number;
  drop_pct?: number;
  qty?: number;
  safety?: number;
  brand?: string;
}

export interface WatchtowerScanResponse {
  scanned_at: string;
  total_alerts: number;
  severity: "紧急" | "需关注" | "正常";
  summary: string;
  top_actions: string[];
  risk_areas: string[];
  alerts_persisted: number;
  anomalies: Record<AnomalyDomain, AnomalyRow[]>;
}
