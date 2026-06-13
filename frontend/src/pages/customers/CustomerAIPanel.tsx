/**
 * CustomerAIPanel — 客户 AI 功能面板
 *
 * 功能:
 *   1. RFM 分析 — 评分 + 分层 + 策略建议
 *   2. 流失预警 — 风险分 + 风险因素 + 挽留建议
 *   3. 产品推荐 — AI 智能匹配
 *   4. 语义搜索 — 自然语言查找相似客户
 *
 * 数据源:
 *   getCustomer360 → RFM + churn
 *   getCustomerAIRecommendationSummary → 产品推荐
 *   getSimilarCustomers → 相似客户
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Input,
  List,
  message,
  Progress,
  Row,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
} from "antd";
import {
  SearchOutlined,
  WarningOutlined,
  RiseOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import {
  getCustomer360,
  getCustomerAIRecommendationSummary,
  getSimilarCustomers,
  searchSimilarCustomers,
} from "@/api";

const { Text, Title, Paragraph } = Typography;

// ── 类型 ──

interface AIPanelProps {
  customerId: number;
  customerName: string;
}

interface RFMData {
  r_score: number;
  f_score: number;
  m_score: number;
  tier?: string;
  segment?: string;
  suggestion?: string;
}

interface ChurnData {
  risk_score: number;
  risk_level: string;
  factors: string[];
  recommendation: string;
}

interface ProductRecommendation {
  product_id: number;
  product_name: string;
  brand?: string;
  match_score: number;
  reason: string;
}

interface SimilarCustomer {
  id: number;
  name: string;
  similarity: number;
  industry?: string;
}

interface AIRecommendationSummary {
  summary?: string;
  churn_risk_score?: number;
  value_score?: number;
  urgency_score?: number;
  recommendations?: ProductRecommendation[];
}

// ── 常量 ──

const RFM_TIER_COLORS: Record<string, string> = {
  "重要价值": "#52c41a",
  "重要发展": "#1890ff",
  "重要保持": "#faad14",
  "一般价值": "#d9d9d9",
  "流失风险": "#f5222d",
};

const CHURN_RISK_COLORS: Record<string, string> = {
  low: "#52c41a",
  medium: "#faad14",
  high: "#f5222d",
};

// ── 组件 ──

export const CustomerAIPanel: React.FC<AIPanelProps> = ({
  customerId,
  customerName,
}) => {
  const [loading, setLoading] = useState(false);
  const [rfm, setRfm] = useState<RFMData | null>(null);
  const [churn, setChurn] = useState<ChurnData | null>(null);
  const [recommendations, setRecommendations] = useState<
    ProductRecommendation[]
  >([]);
  const [similarCustomers, setSimilarCustomers] = useState<SimilarCustomer[]>(
    []
  );
  const [semanticQuery, setSemanticQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SimilarCustomer[]>([]);

  // ── 加载所有 AI 数据 ──
  const loadAll = useCallback(async () => {
    if (!customerId) return;
    setLoading(true);
    try {
      const [res360, resRec, resSim] = await Promise.allSettled([
        getCustomer360(customerId),
        getCustomerAIRecommendationSummary(customerId),
        getSimilarCustomers(customerId, 5),
      ]);

      if (res360.status === "fulfilled") {
        const d = res360.value.data.data;
        const context = d?.context;
        if (context) {
          const rfmData = context.rfm as RFMData | undefined;
          if (rfmData) setRfm(rfmData);
          const churnData = (context.churn_risk || context.churn) as ChurnData | undefined;
          if (churnData) setChurn(churnData);
        }
      }
      if (resRec.status === "fulfilled") {
        const d = (resRec.value.data as { data?: AIRecommendationSummary })?.data;
        setRecommendations(d?.recommendations || []);
      }
      if (resSim.status === "fulfilled") {
        const d = (resSim.value.data as { data?: SimilarCustomer[] })?.data;
        setSimilarCustomers(d || []);
      }
    } catch {
      message.error("加载 AI 数据失败");
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // ── 语义搜索 ──
  const handleSemanticSearch = useCallback(async () => {
    if (!semanticQuery.trim()) return;
    setSearching(true);
    try {
      const res = await searchSimilarCustomers(semanticQuery, 10);
      const payload = (res.data as { data?: SimilarCustomer[] })?.data;
      setSearchResults(payload || []);
    } catch {
      message.error("语义搜索失败");
    } finally {
      setSearching(false);
    }
  }, [semanticQuery]);

  // ── RFM 可视化 ──
  const rfmSection = useMemo(() => {
    if (!rfm) {
      return <Empty description="暂无 RFM 数据，完成首笔交易后自动生成" />;
    }
    const tier = rfm.tier || rfm.segment || "未分类";
    const tierColor = RFM_TIER_COLORS[tier] || "#d9d9d9";

    return (
      <Card title="📊 RFM 分析" size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="最近消费 (R)"
              value={rfm.r_score}
              suffix="/ 5"
              valueStyle={{ color: rfm.r_score >= 4 ? "#52c41a" : "#faad14" }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="消费频率 (F)"
              value={rfm.f_score}
              suffix="/ 5"
              valueStyle={{ color: rfm.f_score >= 4 ? "#52c41a" : "#faad14" }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="消费金额 (M)"
              value={rfm.m_score}
              suffix="/ 5"
              valueStyle={{ color: rfm.m_score >= 4 ? "#52c41a" : "#faad14" }}
            />
          </Col>
        </Row>
        <div style={{ marginTop: 12 }}>
          <Text strong>客户分层：</Text>
          <Tag color={tierColor} style={{ marginLeft: 8 }}>
            {tier}
          </Tag>
        </div>
        {rfm.suggestion && (
          <Alert
            type="info"
            message="策略建议"
            description={rfm.suggestion}
            style={{ marginTop: 12 }}
            showIcon
          />
        )}
      </Card>
    );
  }, [rfm]);

  // ── 流失预警 ──
  const churnSection = useMemo(() => {
    if (!churn) {
      return (
        <Card title="⚠️ 流失预警" size="small" style={{ marginBottom: 16 }}>
          <Empty description="暂无流失风险评估数据" />
        </Card>
      );
    }

    const riskColor =
      CHURN_RISK_COLORS[churn.risk_level] || "#faad14";
    const riskPercent = Math.round((churn.risk_score || 0) * 100);

    return (
      <Card title="⚠️ 流失预警" size="small" style={{ marginBottom: 16 }}>
        <div style={{ textAlign: "center", marginBottom: 16 }}>
          <Progress
            type="circle"
            percent={riskPercent}
            strokeColor={
              riskPercent >= 70
                ? "#f5222d"
                : riskPercent >= 40
                  ? "#faad14"
                  : "#52c41a"
            }
            format={() => (
              <span>
                <div style={{ fontSize: 24, fontWeight: "bold" }}>
                  {riskPercent}%
                </div>
                <div style={{ fontSize: 12, color: riskColor }}>
                  {churn.risk_level === "high"
                    ? "高风险"
                    : churn.risk_level === "medium"
                      ? "中风险"
                      : "低风险"}
                </div>
              </span>
            )}
          />
        </div>

        {churn.factors && churn.factors.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <Text strong>风险因素：</Text>
            <ul style={{ marginTop: 4, paddingLeft: 20 }}>
              {churn.factors.map((f, i) => (
                <li key={i}>
                  <Text>{f}</Text>
                </li>
              ))}
            </ul>
          </div>
        )}

        {churn.recommendation && (
          <Alert
            type={riskPercent >= 70 ? "error" : "warning"}
            message="挽留建议"
            description={churn.recommendation}
            showIcon
            icon={<RiseOutlined />}
          />
        )}
      </Card>
    );
  }, [churn]);

  // ── 产品推荐 ──
  const productSection = useMemo(() => {
    if (recommendations.length === 0) {
      return (
        <Card title="🛒 产品推荐" size="small" style={{ marginBottom: 16 }}>
          <Empty description="暂无产品推荐，完成更多交易后 AI 自动生成" />
        </Card>
      );
    }

    return (
      <Card title="🛒 产品推荐" size="small" style={{ marginBottom: 16 }}>
        <List
          size="small"
          dataSource={recommendations.slice(0, 5)}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <Space>
                    <ShoppingCartOutlined />
                    <Text strong>{item.product_name}</Text>
                    {item.brand && (
                      <Tag color="blue">{item.brand}</Tag>
                    )}
                    <Progress
                      percent={Math.round(item.match_score * 100)}
                      size="small"
                      style={{ width: 80 }}
                      strokeColor="#1890ff"
                    />
                  </Space>
                }
                description={item.reason}
              />
            </List.Item>
          )}
        />
      </Card>
    );
  }, [recommendations]);

  // ── 相似客户（语义搜索） ──
  const similaritySection = useMemo(() => {
    const data = searchResults.length > 0 ? searchResults : similarCustomers;

    return (
      <Card title="🔍 相似客户" size="small" style={{ marginBottom: 16 }}>
        {/* 语义搜索框 */}
        <Input.Search
          placeholder="输入自然语言描述搜索相似客户..."
          value={semanticQuery}
          onChange={(e) => setSemanticQuery(e.target.value)}
          onSearch={handleSemanticSearch}
          loading={searching}
          enterButton={<SearchOutlined />}
          style={{ marginBottom: 12 }}
        />

        {data.length === 0 ? (
          <Empty
            description={
              searchResults.length === 0 && semanticQuery
                ? "未找到匹配客户"
                : "加载相似客户中..."
            }
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <List
            size="small"
            dataSource={data}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  avatar={<TeamOutlined style={{ fontSize: 20 }} />}
                  title={
                    <Space>
                      <Text strong>{item.name}</Text>
                      <Tag color="blue">
                        匹配度 {(item.similarity * 100).toFixed(0)}%
                      </Tag>
                    </Space>
                  }
                  description={
                    item.industry && (
                      <Text type="secondary">{item.industry as string}</Text>
                    )
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    );
  }, [similarCustomers, searchResults, semanticQuery, searching, handleSemanticSearch]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 40 }}>
        <Spin size="large" tip="加载 AI 分析数据..." />
      </div>
    );
  }

  return (
    <div style={{ padding: "8px 0" }}>
      {rfmSection}
      {churnSection}
      {productSection}
      {similaritySection}
    </div>
  );
};

export default CustomerAIPanel;
