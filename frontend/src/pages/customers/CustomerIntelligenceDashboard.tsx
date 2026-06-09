import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Row, Col, Statistic, Table, Tag, Spin, Button, Space, Typography, Alert, Progress, ProgressProps } from "antd";
import { StatusTag } from "../../ui";
import {
  TeamOutlined, AlertOutlined, RiseOutlined, WarningOutlined,
  ReloadOutlined, StopOutlined, CheckCircleOutlined,
} from "@ant-design/icons";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { getCustomerAIStats, batchScoreAI } from "../../api";
import type { CustomerAIStats } from "../../types";
import CustomerModuleShell from "./CustomerModuleShell";

const { Text } = Typography;

const CHURN_COLORS: Record<string, string> = { 低: "#52c41a", 中: "#faad14", 高: "#f5222d", 未知: "#d9d9d9" };
const TIER_COLORS: Record<string, string> = {
  重要价值: "#52c41a", 重要发展: "#1890ff", 重要保持: "#faad14", 一般价值: "#d9d9d9", "流失风险": "#f5222d",
};
const LIFECYCLE_COLORS: Record<string, string> = {
  "新潜客": "#1890ff", "活跃": "#52c41a", "已成交": "#722ed1", "VIP": "#eb2f96", "不活跃": "#faad14", "流失": "#f5222d",
};


export default function CustomerIntelligenceDashboard() {
  const [stats, setStats] = useState<CustomerAIStats | null>(null);
  const [scoring, setScoring] = useState(false);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchStats = async () => {
    setLoading(true);
    try {
      const resp = await getCustomerAIStats();
      setStats(resp.data.data as CustomerAIStats);
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStats(); }, []);

  const handleBatchScore = async () => {
    setScoring(true);
    try {
      await batchScoreAI();
      await fetchStats();
    } catch {
      // ignore
    } finally {
      setScoring(false);
    }
  };

  if (loading) {
    return (
      <CustomerModuleShell title="客户智能分析" subtitle="围绕健康度、流失风险与生命周期的智能决策视图">
        <Spin size="large" style={{ display: "block", marginTop: 100 }} />
      </CustomerModuleShell>
    );
  }
  if (!stats) {
    return (
      <CustomerModuleShell title="客户智能分析" subtitle="围绕健康度、流失风险与生命周期的智能决策视图">
        <Text type="secondary">无法加载客户AI统计数据</Text>
      </CustomerModuleShell>
    );
  }

  const s = stats;
  const rfmData = Object.entries(s.rfm_tiers).map(([tier, count]) => ({ tier, count }));
  const churnData = Object.entries(s.churn_dist).map(([level, count]) => ({ level, count }));

  const topChurnCustomers: Array<{ id: number; name: string; risk_score: number; risk_level: string }> = [];

  const scoreColumns = [
    { title: "排名", key: "rank", width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    {
      title: "客户", key: "name", render: (_: unknown, r: { id: number; name: string }) => (
        <a onClick={() => navigate(`/customers/${r.id}`)}>{r.name}</a>
      ),
    },
    {
      title: "风险评分", key: "risk_score", width: 120,
      render: (v: number) => {
        const pctProps: ProgressProps = {
          percent: v,
          size: "small",
          status: v >= 70 ? "exception" : v >= 40 ? "normal" : "success",
          strokeColor: v >= 70 ? "#f5222d" : v >= 40 ? "#faad14" : "#52c41a",
        };
        return <Progress {...pctProps} />;
      },
    },
    {
      title: "风险等级", key: "risk_level", width: 80,
      render: (v: string) => <StatusTag tone={CHURN_COLORS[v] || "neutral"}>{v}</StatusTag>,
    },
    {
      title: "操作", key: "action", width: 70,
      render: (_: unknown, r: { id: number }) => (
        <Button size="small" onClick={() => navigate(`/customers/${r.id}/insight`)}>洞察</Button>
      ),
    },
  ];

  return (
    <CustomerModuleShell
      title="客户智能分析"
      subtitle="围绕健康度、流失风险与生命周期的智能决策视图"
      extra={(
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchStats}>刷新</Button>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            loading={scoring}
            onClick={handleBatchScore}
          >
            批量AI评分
          </Button>
        </Space>
      )}
    >
      {/* Alerts */}
      {s.high_churn_count > 0 && (
        <Alert
          type="error"
          icon={<AlertOutlined />}
          message={`发现 ${s.high_churn_count} 个高流失风险客户`}
          description="以下客户AI评估显示流失风险较高，请及时采取挽留措施"
          style={{ marginBottom: 16 }}
          action={<Button size="small" onClick={() => navigate("/customers")}>查看全部</Button>}
        />
      )}

      {s.stale_high_value > 0 && (
        <Alert
          type="warning"
          icon={<WarningOutlined />}
          message={`${s.stale_high_value} 个A类客户超过60天未联系`}
          description="重要客户长期未跟进，存在流失风险"
          style={{ marginBottom: 16 }}
        />
      )}

      {/* KPI Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card><Statistic title="客户总数" value={s.total} prefix={<TeamOutlined />} /></Card>
        </Col>
        <Col span={4}>
          <Card><Statistic title="已AI分析" value={s.ai_computed} suffix={`/ ${s.total}`} prefix={<CheckCircleOutlined />} /></Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="AI覆盖率"
              value={s.ai_coverage_pct}
              suffix="%"
              prefix={<RiseOutlined />}
              valueStyle={{ color: s.ai_coverage_pct < 50 ? "#f5222d" : undefined }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="高流失风险 (>=70)"
              value={s.high_churn_count}
              prefix={<StopOutlined />}
              valueStyle={{ color: s.high_churn_count > 0 ? "#f5222d" : undefined }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card><Statistic title="活跃客户(30天)" value={s.active_30d} prefix={<RiseOutlined />} /></Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="从未联系"
              value={s.never_contacted}
              prefix={<WarningOutlined />}
              valueStyle={{ color: s.never_contacted > 0 ? "#faad14" : undefined }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card title="RFM客户分层" size="small">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={rfmData} dataKey="count" nameKey="tier" cx="50%" cy="50%" outerRadius={70}
                  label={(entry) => { const e = entry as unknown as { tier: string; count: number }; return `${e.tier}: ${e.count}`; }}
                >
                  {rfmData.map((entry) => (
                    <Cell key={entry.tier} fill={TIER_COLORS[entry.tier] || "#999"} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={6}>
          <Card title="流失风险分布" size="small">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={churnData} dataKey="count" nameKey="level" cx="50%" cy="50%" outerRadius={70}
                  label={(entry) => { const e = entry as unknown as { level: string; count: number }; return `${e.level}: ${e.count}`; }}
                >
                  {churnData.map((entry) => (
                    <Cell key={entry.level} fill={CHURN_COLORS[entry.level] || "#999"} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={6}>
          <Card title="客户生命周期分布" size="small">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={s.by_lifecycle}>
                <XAxis dataKey="stage" fontSize={11} />
                <YAxis fontSize={11} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {s.by_lifecycle.map((entry) => (
                    <Cell key={entry.stage} fill={LIFECYCLE_COLORS[entry.stage] || "#1890ff"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={6}>
          <Card title="平均健康评分" size="small">
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 200 }}>
              <Progress
                type="dashboard"
                percent={s.avg_health_score}
                size={140}
                strokeColor={s.avg_health_score >= 70 ? "#52c41a" : s.avg_health_score >= 40 ? "#faad14" : "#f5222d"}
                format={(p) => <span style={{ fontSize: 24, fontWeight: 600 }}>{p}</span>}
              />
              <Text type="secondary" style={{ marginTop: 8 }}>健康分 (0-100)</Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* High Churn Risk Customers */}
      <Row gutter={16}>
        <Col span={24}>
          <Card title="高流失风险客户" size="small">
            {topChurnCustomers.length > 0 ? (
              <Table
                rowKey="id"
                columns={scoreColumns}
                dataSource={topChurnCustomers}
                size="small"
                pagination={false}
              />
            ) : (
              <Text type="secondary">
                {s.high_churn_count > 0
                  ? `共 ${s.high_churn_count} 个高风险客户，请在客户详情页查看`
                  : "暂无高流失风险客户"}
              </Text>
            )}
          </Card>
        </Col>
      </Row>
    </CustomerModuleShell>
  );
}
