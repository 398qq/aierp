import type { AnomalyDomain } from "@/types/watchtower";

/** Single source of truth for AnomalyDomain → Chinese display label.
 * Used by KpiCards (domain distribution badges) and WatchtowerDashboard
 * (allAnomalies mapping). Add a new domain here and both stay in sync. */
export const DOMAIN_LABELS: Record<AnomalyDomain, string> = {
  churn_risk: "客户流失风险",
  order_drop: "订单量下降",
  low_stock: "低库存",
  out_of_stock: "缺货",
};
