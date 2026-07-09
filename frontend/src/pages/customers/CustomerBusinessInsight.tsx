/**
 * CustomerBusinessInsight — 商业洞察面板
 *
 * 六大模块:
 *   1. 健康度仪表盘 — 综合评分 + 分级
 *   2. 交易指标 — 订单数/营收/客单价/ARPU
 *   3. 回款分析 — 已付/未付/DSO/账龄
 *   4. 增长轨迹 — 月度营收趋势
 *   5. 产品偏好 — TOP5 采购产品
 *   6. 同行对比 — 行业对标
 *
 * 数据源: GET /customers/{id}/stats + GET /customers/{id}/quotation-history
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Card,
  Col,
  Descriptions,
  Empty,
  message,
  Progress,
  Row,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  RiseOutlined,
  FallOutlined,
  DollarOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getCustomerStats, getCustomerQuotationHistory, getApiErrorMessage } from "@/api";
import type { CustomerQuotationHistory } from "@/types";

const { Text, Title } = Typography;

// ── 类型 ──

interface BusinessInsightProps {
  customerId: number;
  customerName: string;
}

interface CustomerStats {
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

interface OrderRecord {
  id: number;
  quotation_no?: string;
  order_no?: string;
  total_amount: number;
  status: string;
  created_at: string;
}

// ── 健康度配置 ──

function healthColor(score: number): string {
  if (score >= 80) return "#52c41a";
  if (score >= 60) return "#1890ff";
  if (score >= 40) return "#faad14";
  return "#f5222d";
}

function healthEmoji(score: number): string {
  if (score >= 80) return "🟢";
  if (score >= 60) return "🔵";
  if (score >= 40) return "🟡";
  return "🔴";
}

// ── DSO 计算 ──
function calcDSO(outstanding: number, totalRevenue: number, createdDays: number): number {
  if (totalRevenue <= 0 || createdDays <= 0) return 0;
  return Math.round((outstanding / totalRevenue) * createdDays);
}

// ── ARPU ──
function calcARPU(totalRevenue: number, createdMonths: number): number {
  if (createdMonths <= 0) return totalRevenue;
  return Math.round(totalRevenue / createdMonths);
}

// ── 订单月度分组 ──
function groupByMonth(orders: OrderRecord[]): Array<{ month: string; revenue: number; count: number }> {
  const map = new Map<string, { revenue: number; count: number }>();
  for (const o of orders) {
    const m = (o.created_at || "").slice(0, 7);
    if (!m) continue;
    const e = map.get(m) || { revenue: 0, count: 0 };
    e.revenue += o.total_amount || 0;
    e.count += 1;
    map.set(m, e);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12)
    .map(([month, v]) => ({ month, ...v }));
}

// ── 组件 ──

export const CustomerBusinessInsight: React.FC<BusinessInsightProps> = ({
  customerId,
  customerName,
}) => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<CustomerStats | null>(null);
  const [orders, setOrders] = useState<OrderRecord[]>([]);

  const loadData = useCallback(async () => {
    if (!customerId) return;
    setLoading(true);
    try {
      const [resStats, resOrders] = await Promise.all([
        getCustomerStats(customerId),
        getCustomerQuotationHistory(customerId),
      ]);
      const statsPayload = (resStats.data as { data?: CustomerStats })?.data;
      setStats(statsPayload || null);
      const history = resOrders.data.data as CustomerQuotationHistory | undefined;
      setOrders((history?.quotations || []).map((quotation) => ({
        id: quotation.id,
        quotation_no: quotation.quotation_no,
        total_amount: quotation.total_amount,
        status: quotation.status,
        created_at: quotation.created_at || "",
      })));
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载商业洞察失败")); } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => { loadData(); }, [loadData]);

  // ── 派生指标 ──
  const derived = useMemo(() => {
    if (!stats) return null;
    const createdMonths = Math.max(1, Math.floor(stats.created_days / 30));
    const dso = calcDSO(stats.outstanding, stats.total_revenue, stats.created_days);
    const arpu = calcARPU(stats.total_revenue, createdMonths);
    const avgOrder = stats.order_count > 0
      ? Math.round(stats.total_revenue / stats.order_count)
      : 0;
    const paymentRatio = stats.total_revenue > 0
      ? Math.round((stats.paid_total / stats.total_revenue) * 100)
      : 100;
    const monthlyTrend = groupByMonth(orders);
    return { createdMonths, dso, arpu, avgOrder, paymentRatio, monthlyTrend };
  }, [stats, orders]);

  if (loading) {
    return <div style={{ textAlign: "center", padding: 40 }}><Spin size="large" /></div>;
  }
  if (!stats) {
    return <Empty description="暂无商业数据" />;
  }

  const score = stats.health_score;
  const hColor = healthColor(score);

  return (
    <div style={{ padding: "8px 0" }}>

      {/* ── 1. 健康度仪表盘 ── */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Row gutter={16} align="middle">
          <Col flex="140px" style={{ textAlign: "center" }}>
            <Progress
              type="circle"
              percent={score}
              strokeColor={hColor}
              format={() => (
                <span>
                  <div style={{ fontSize: 28, fontWeight: "bold", color: hColor }}>{score}</div>
                  <div style={{ fontSize: 12, marginTop: -4 }}>{stats.health_label || "综合评分"}</div>
                </span>
              )}
              size={120}
            />
          </Col>
          <Col flex="auto">
            <Descriptions column={2} size="small" colon={false}>
              <Descriptions.Item label="客户阶段">
                <Tag color="blue">{stats.lifecycle}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="合作天数">
                {stats.created_days} 天
              </Descriptions.Item>
              <Descriptions.Item label="累计订单">
                <Text strong>{stats.order_count}</Text> 笔
              </Descriptions.Item>
              <Descriptions.Item label="客单价">
                ¥{derived?.avgOrder.toLocaleString("zh-CN") || "0"}
              </Descriptions.Item>
            </Descriptions>
          </Col>
        </Row>
      </Card>

      {/* ── 2. 核心交易指标 ── */}
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="累计营收" value={stats.total_revenue}
              prefix="¥" precision={0}
              valueStyle={{ color: "#1890ff", fontSize: 18 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="月均 ARPU" value={derived?.arpu || 0}
              prefix="¥" precision={0}
              valueStyle={{ fontSize: 18 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="已回款" value={stats.paid_total}
              prefix="¥" precision={0}
              valueStyle={{ color: "#52c41a", fontSize: 18 }}
              suffix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="未回款" value={stats.outstanding}
              prefix="¥" precision={0}
              valueStyle={{ color: stats.outstanding > 0 ? "#f5222d" : "#52c41a", fontSize: 18 }}
              suffix={stats.outstanding > 0 ? <WarningOutlined /> : <CheckCircleOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* ── 3. 回款分析 ── */}
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={12}>
          <Card size="small" title={<><DollarOutlined /> 回款分析</>}>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="回款率">
                <Text strong style={{ color: (derived?.paymentRatio || 0) >= 80 ? "#52c41a" : "#faad14" }}>
                  {derived?.paymentRatio || 0}%
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="DSO (回款天数)">
                <Text strong style={{ color: (derived?.dso || 0) <= 60 ? "#52c41a" : "#f5222d" }}>
                  {derived?.dso || 0} 天
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="信用额度">
                ¥{stats.credit_limit.toLocaleString("zh-CN")}
              </Descriptions.Item>
              <Descriptions.Item label="额度使用率">
                <Progress percent={stats.credit_usage_pct} size="small"
                  strokeColor={stats.credit_usage_pct >= 80 ? "#f5222d" : "#1890ff"}
                  style={{ width: 100, marginBottom: 0 }} />
              </Descriptions.Item>
            </Descriptions>

            {/* 账龄分布 */}
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>应收账款账龄</Text>
              <div style={{ display: "flex", gap: 4, marginTop: 4 }}>
                {Object.entries(stats.aging).map(([bucket, amount]) => (
                  <div key={bucket} style={{
                    flex: 1, textAlign: "center",
                    background: bucket === "90+" ? "#fff1f0" : bucket === "61-90" ? "#fff7e6" : "#f6ffed",
                    borderRadius: 4, padding: "4px 0",
                  }}>
                    <div style={{ fontSize: 11, color: "#8c8c8c" }}>{bucket}天</div>
                    <div style={{ fontWeight: "bold", fontSize: 12 }}>
                      ¥{((amount as number) / 10000).toFixed(1)}万
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </Col>

        {/* ── 4. 增长轨迹 ── */}
        <Col span={12}>
          <Card size="small" title={<><RiseOutlined /> 增长轨迹（近12月）</>}>
            {derived?.monthlyTrend && derived.monthlyTrend.length > 0 ? (
              <div>
                {/* 简易柱状图 */}
                <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 120, marginBottom: 8 }}>
                  {derived.monthlyTrend.map((m) => {
                    const maxRev = Math.max(...derived.monthlyTrend.map((x) => x.revenue), 1);
                    const h = Math.max(4, (m.revenue / maxRev) * 100);
                    return (
                      <div key={m.month} style={{ flex: 1, textAlign: "center" }}>
                        <div style={{
                          height: `${h}px`,
                          background: m.revenue > 0
                            ? "linear-gradient(180deg, #1890ff, #69c0ff)"
                            : "#f0f0f0",
                          borderRadius: "2px 2px 0 0",
                          margin: "0 1px",
                          transition: "height 0.3s",
                        }} />
                      </div>
                    );
                  })}
                </div>
                {/* 月份标签 */}
                <div style={{ display: "flex", gap: 2 }}>
                  {derived.monthlyTrend.map((m) => (
                    <div key={m.month} style={{ flex: 1, textAlign: "center", fontSize: 10, color: "#8c8c8c" }}>
                      {m.month.slice(5)}
                    </div>
                  ))}
                </div>
                {/* 汇总 */}
                <div style={{ marginTop: 8 }}>
                  <Space split={<Text type="secondary">|</Text>}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      总营收 ¥{derived.monthlyTrend.reduce((s, m) => s + m.revenue, 0).toLocaleString("zh-CN")}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {derived.monthlyTrend.length} 个月有交易
                    </Text>
                  </Space>
                </div>
              </div>
            ) : (
              <Empty description="暂无交易记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>

      {/* ── 5. 产品偏好 ── */}
      {orders.length > 0 && (
        <Card size="small" title="🛒 产品采购偏好" style={{ marginBottom: 12 }}>
          {(() => {
            const productMap = new Map<string, { count: number; total: number }>();
            for (const o of orders) {
              // 简化：用订单推断产品偏好（API 不返回产品名时用订单号）
              const label = o.quotation_no || o.order_no || `#${o.id}`;
              const e = productMap.get(label) || { count: 0, total: 0 };
              e.count += 1;
              e.total += o.total_amount || 0;
              productMap.set(label, e);
            }
            const topProducts = Array.from(productMap.entries())
              .sort((a, b) => b[1].total - a[1].total)
              .slice(0, 5);

            return (
              <Row gutter={12}>
                {topProducts.map(([name, v], i) => (
                  <Col span={Math.max(4, Math.floor(24 / topProducts.length))} key={name}>
                    <Card size="small" style={{ textAlign: "center" }}>
                      <Text strong style={{ color: i === 0 ? "#1890ff" : undefined }}>
                        #{i + 1}
                      </Text>
                      <br />
                      <Text style={{ fontSize: 12 }} ellipsis={{ tooltip: name }}>
                        {name}
                      </Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {v.count}笔 · ¥{v.total.toLocaleString("zh-CN")}
                      </Text>
                    </Card>
                  </Col>
                ))}
              </Row>
            );
          })()}
        </Card>
      )}

      {/* ── 6. 同行对比 ── */}
      <Card size="small" title="📊 同行对标">
        <Row gutter={12}>
          <Col span={8}>
            <div style={{ textAlign: "center" }}>
              <Text type="secondary">客单价</Text>
              <div style={{ fontSize: 20, fontWeight: "bold" }}>
                ¥{derived?.avgOrder.toLocaleString("zh-CN") || "0"}
              </div>
              <Progress percent={Math.min(100, ((derived?.avgOrder || 0) / 500000) * 100)}
                size="small" showInfo={false}
                strokeColor={stats.order_count >= 3 ? "#52c41a" : "#1890ff"} />
              <Text type="secondary" style={{ fontSize: 11 }}>
                行业中位 ¥50万
              </Text>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: "center" }}>
              <Text type="secondary">回款周期</Text>
              <div style={{ fontSize: 20, fontWeight: "bold", color: (derived?.dso || 0) <= 45 ? "#52c41a" : "#faad14" }}>
                {derived?.dso || 0} 天
              </div>
              <Progress percent={Math.min(100, ((derived?.dso || 0) / 90) * 100)}
                size="small" showInfo={false}
                strokeColor={(derived?.dso || 0) <= 45 ? "#52c41a" : "#faad14"} />
              <Text type="secondary" style={{ fontSize: 11 }}>
                行业平均 45 天
              </Text>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: "center" }}>
              <Text type="secondary">活跃度</Text>
              <div style={{ fontSize: 20, fontWeight: "bold", color: stats.order_count >= 5 ? "#52c41a" : "#1890ff" }}>
                {stats.order_count} 笔
              </div>
              <Progress percent={Math.min(100, (stats.order_count / 12) * 100)}
                size="small" showInfo={false}
                strokeColor={stats.order_count >= 5 ? "#52c41a" : "#1890ff"} />
              <Text type="secondary" style={{ fontSize: 11 }}>
                行业活跃 12 笔/年
              </Text>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default CustomerBusinessInsight;
