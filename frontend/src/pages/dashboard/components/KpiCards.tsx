import { Col, Row, Typography } from "antd";
import { StatusTag } from "@/ui";
import styles from "./KpiCards.module.css";

const { Text } = Typography;

const severityTone = (s: string): "success" | "warning" | "danger" =>
  s === "紧急" ? "danger" : s === "需关注" ? "warning" : "success";

const domainLabels: Record<string, string> = {
  churn_risk: "客户流失风险",
  order_drop: "订单量下降",
  low_stock: "低库存",
  out_of_stock: "缺货",
};

export interface KpiCardsProps {
  totalAlerts: number;
  severity: string;
  riskAreas: string[];
  domainDistribution: Array<[string, number]>;
}

export function KpiCards({ totalAlerts, severity, riskAreas, domainDistribution }: KpiCardsProps) {
  return (
    <Row gutter={[16, 16]} className={styles.row}>
      <Col xs={24} sm={6}>
        <div className={styles.card}>
          <Text>异常总数</Text>
          <div className={styles.value}>{totalAlerts}</div>
        </div>
      </Col>
      <Col xs={24} sm={6}>
        <div className={styles.card}>
          <Text>严重程度</Text>
          <div className={styles.severity}>
            <StatusTag tone={severityTone(severity)}>{severity}</StatusTag>
          </div>
        </div>
      </Col>
      <Col xs={24} sm={6}>
        <div className={styles.card}>
          <Text>异常领域</Text>
          <div className={styles.areaList}>
            {riskAreas.length ? (
              riskAreas.map((a, i) => (
                <StatusTag tone="danger" key={i}>
                  {a}
                </StatusTag>
              ))
            ) : (
              <StatusTag tone="success">无</StatusTag>
            )}
          </div>
        </div>
      </Col>
      <Col xs={24} sm={6}>
        <div className={styles.card}>
          <Text>领域分布</Text>
          <div className={styles.areaList}>
            {domainDistribution.length ? (
              domainDistribution.map(([domain, count]) => (
                <StatusTag key={domain} tone={count > 5 ? "danger" : "warning"}>
                  {domainLabels[domain] || domain}: {count}
                </StatusTag>
              ))
            ) : (
              <Text type="secondary">暂无异常</Text>
            )}
          </div>
        </div>
      </Col>
    </Row>
  );
}
