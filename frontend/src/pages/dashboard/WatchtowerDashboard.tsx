import { Col, Row, Alert, Button, Typography } from "antd";
import { useApiQuery } from "@/lib/queries";
import { getApiErrorMessage } from "@/api/client";
import { EmptyState, StatusTag } from "@/ui";
import FullPageLoader from "@/ui/FullPageLoader";
import { ScanHeader } from "./components/ScanHeader";
import type { WatchtowerScanResponse } from "@/types/watchtower";
import styles from "./WatchtowerDashboard.module.css";

const { Text } = Typography;
const SCAN_LOOKBACK_DAYS = 90;

const severityTone = (s: string): "success" | "warning" | "danger" =>
  s === "紧急" ? "danger" : s === "需关注" ? "warning" : "success";

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

      <Row gutter={[16, 16]} className={styles.kpiRow}>
        <Col xs={24} sm={6}>
          <div className={styles.kpiCard}>
            <Text>异常总数</Text>
            <div className={styles.kpiValue}>{data.total_alerts}</div>
          </div>
        </Col>
        <Col xs={24} sm={6}>
          <div className={styles.kpiCard}>
            <Text>严重程度</Text>
            <div className={styles.kpiValue}>
              <StatusTag tone={severityTone(data.severity)}>{data.severity}</StatusTag>
            </div>
          </div>
        </Col>
        <Col xs={24} sm={6}>
          <div className={styles.kpiCard}>
            <Text>异常领域</Text>
            {data.risk_areas?.length ? (
              data.risk_areas.map((a, i) => (
                <StatusTag tone="danger" key={i}>
                  {a}
                </StatusTag>
              ))
            ) : (
              <StatusTag tone="success">无</StatusTag>
            )}
          </div>
        </Col>
        <Col xs={24} sm={6}>
          <div className={styles.kpiCard}>
            <Text>领域分布</Text>
            {anomalyEntries.length ? (
              anomalyEntries.map(([domain, items]) => (
                <StatusTag key={domain} tone={items.length > 5 ? "danger" : "warning"}>
                  {domainLabels[domain] || domain}: {items.length}
                </StatusTag>
              ))
            ) : (
              <Text type="secondary">暂无异常</Text>
            )}
          </div>
        </Col>
      </Row>

      <div className={styles.section}>
        <Text strong>AI 分析摘要</Text>
        <div className={styles.aiSummary}>{data.summary}</div>
      </div>

      {data.top_actions?.length > 0 && (
        <div className={styles.section}>
          <Text strong>优先行动</Text>
          <ol className={styles.topActions}>
            {data.top_actions.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ol>
        </div>
      )}

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
