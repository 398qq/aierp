import { Alert, Button } from "antd";
import { useApiQuery } from "@/lib/queries";
import { getApiErrorMessage } from "@/api/client";
import FullPageLoader from "@/ui/FullPageLoader";
import { ScanHeader } from "./components/ScanHeader";
import { KpiCards } from "./components/KpiCards";
import { AiSummary } from "./components/AiSummary";
import { TopActions } from "./components/TopActions";
import { AnomalyTable } from "./components/AnomalyTable";
import type { WatchtowerScanResponse, AnomalyRow, AnomalyDomain } from "@/types/watchtower";
import styles from "./WatchtowerDashboard.module.css";

const SCAN_LOOKBACK_DAYS = 90;

const DOMAIN_LABELS: Record<AnomalyDomain, string> = {
  churn_risk: "客户流失风险",
  order_drop: "订单量下降",
  low_stock: "低库存",
  out_of_stock: "缺货",
};

export default function WatchtowerDashboard() {
  const query = useApiQuery<WatchtowerScanResponse>(
    ["watchtower", "scan", SCAN_LOOKBACK_DAYS],
    `/ai/watchtower/scan?days_back=${SCAN_LOOKBACK_DAYS}`,
    undefined,
    { staleTime: 60 * 1000, refetchInterval: false },
  );

  if (query.isLoading) return <FullPageLoader />;
  if (query.error) {
    return (
      <Alert
        type="error"
        message={getApiErrorMessage(query.error)}
        className={styles.errorAlert}
        action={<Button onClick={() => query.refetch()}>重试</Button>}
      />
    );
  }
  if (!query.data) return null;

  const data = query.data;
  const anomalyEntries: Array<[AnomalyDomain, AnomalyRow[]]> = (
    Object.entries(data.anomalies) as Array<[AnomalyDomain, AnomalyRow[]]>
  ).filter(([, v]) => v.length > 0);

  const allAnomalies: AnomalyRow[] = anomalyEntries.flatMap(([domain, items]) =>
    items.map((item) => ({ ...item, domain, domainLabel: DOMAIN_LABELS[domain] || domain })),
  );

  return (
    <div className={styles.page}>
      <ScanHeader
        scanned_at={data.scanned_at}
        loading={query.isFetching}
        onRefresh={() => query.refetch()}
      />

      <KpiCards
        totalAlerts={data.total_alerts}
        severity={data.severity}
        riskAreas={data.risk_areas}
        domainDistribution={anomalyEntries.map(
          ([d, items]) => [d, items.length] as [string, number],
        )}
      />

      <AiSummary text={data.summary} />

      {data.top_actions?.length > 0 && <TopActions items={data.top_actions} />}

      <AnomalyTable rows={allAnomalies} />
    </div>
  );
}
