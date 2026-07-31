import { Alert, Button, Typography } from "antd";
import { useApiQuery } from "@/lib/queries";
import { getApiErrorMessage } from "@/api/client";
import { EmptyState } from "@/ui";
import FullPageLoader from "@/ui/FullPageLoader";
import { ScanHeader } from "./components/ScanHeader";
import { KpiCards } from "./components/KpiCards";
import { AiSummary } from "./components/AiSummary";
import { TopActions } from "./components/TopActions";
import type { WatchtowerScanResponse } from "@/types/watchtower";
import styles from "./WatchtowerDashboard.module.css";

const { Text } = Typography;
const SCAN_LOOKBACK_DAYS = 90;

const domainLabels: Record<string, string> = {
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
  const anomalyEntries = Object.entries(data.anomalies || {}).filter(([, v]) => v.length > 0);

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

      <div className={styles.section}>
        <Text strong>异常详情</Text>
        {anomalyEntries.length > 0 ? (
          <pre className={styles.anomalyPre}>
            {JSON.stringify(
              anomalyEntries.flatMap(([domain, items]) =>
                items.map((it) => ({ ...it, domain, domainLabel: domainLabels[domain] || domain })),
              ),
              null,
              2,
            )}
          </pre>
        ) : (
          <EmptyState description="未检测到异常，系统运行正常" />
        )}
      </div>
    </div>
  );
}
