import { useEffect, useState } from "react";
import {
  Card, Row, Col, Statistic, Progress, Table, Spin, Result, Button,
  Modal, Tag, Typography, Descriptions, List, InputNumber, Space, message,
} from "antd";
import { AlertOutlined, BulbOutlined } from "@ant-design/icons";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { getTargetSummary, scanTargetEarlyWarning, recommendTargets } from "../../api";
import type { TargetSummary, TargetEarlyWarning, TargetRecommendation } from "../../types";

export default function TargetStats() {
  const [data, setData] = useState<TargetSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Early Warning modal
  const [warningOpen, setWarningOpen] = useState(false);
  const [warningData, setWarningData] = useState<TargetEarlyWarning | null>(null);
  const [warningLoading, setWarningLoading] = useState(false);

  // Recommendation modal
  const [recoOpen, setRecoOpen] = useState(false);
  const [recoData, setRecoData] = useState<TargetRecommendation | null>(null);
  const [recoLoading, setRecoLoading] = useState(false);
  const [recoUserId, setRecoUserId] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const resp = await getTargetSummary();
        setData(resp.data.data);
      } catch { setError(true); }
      finally { setLoading(false); }
    })();
  }, []);

  const handleEarlyWarning = async () => {
    setWarningOpen(true);
    setWarningLoading(true);
    setWarningData(null);
    try {
      const resp = await scanTargetEarlyWarning();
      setWarningData(resp.data.data);
    } catch {
      message.error("目标预警分析失败");
    } finally {
      setWarningLoading(false);
    }
  };

  const handleRecommend = async () => {
    if (recoUserId == null) {
      message.warning("请先输入用户ID");
      return;
    }
    setRecoOpen(true);
    setRecoLoading(true);
    setRecoData(null);
    try {
      const resp = await recommendTargets(recoUserId);
      setRecoData(resp.data.data);
    } catch {
      message.error("目标推荐失败");
    } finally {
      setRecoLoading(false);
    }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;
  if (error) return <Result status="warning" title="加载失败" extra={<Button onClick={() => window.location.reload()}>重试</Button>} />;
  if (!data) return <Result status="warning" title="暂无数据" />;

  const chartData = data.items.map(t => ({
    name: `${t.target_type} #${t.id}`,
    目标: t.target_amount,
    实际: t.actual_amount,
  }));

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "用户", dataIndex: "user_id", width: 80 },
    { title: "类型", dataIndex: "target_type", width: 80 },
    { title: "目标", dataIndex: "target_amount", width: 120, render: (v: number) => `¥${v.toFixed(2)}` },
    { title: "实际", dataIndex: "actual_amount", width: 120, render: (v: number) => `¥${v.toFixed(2)}` },
    {
      title: "完成率", dataIndex: "completion_rate", width: 120,
      render: (v: number) => <Progress percent={v} size="small" status={v >= 100 ? "success" : "active"} />,
    },
  ];

  const riskColumns = [
    { title: "用户", dataIndex: "user_name", width: 100 },
    { title: "目标", dataIndex: "target", width: 100, render: (v: number) => `¥${v.toFixed(2)}` },
    { title: "实际", dataIndex: "actual", width: 100, render: (v: number) => `¥${v.toFixed(2)}` },
    {
      title: "完成率", dataIndex: "attainment_pct", width: 100,
      render: (v: number) => (
        <Typography.Text type={v < 50 ? "danger" : "warning"}>{v.toFixed(1)}%</Typography.Text>
      ),
    },
    {
      title: "风险等级", dataIndex: "risk_level", width: 100,
      render: (v: string) => {
        const color = v === "high" ? "red" : v === "medium" ? "orange" : "blue";
        return <Tag color={color}>{v}</Tag>;
      },
    },
    { title: "原因", dataIndex: "reason", ellipsis: true },
  ];

  const topPerformerColumns = [
    { title: "用户", dataIndex: "user_name", width: 100 },
    {
      title: "完成率", dataIndex: "attainment_pct", width: 100,
      render: (v: number) => <Typography.Text type="success">{v.toFixed(1)}%</Typography.Text>,
    },
    { title: "亮点", dataIndex: "highlight", ellipsis: true },
  ];

  const overallStatusColor =
    warningData?.overall_status === "healthy" ? "green"
    : warningData?.overall_status === "warning" ? "orange"
    : warningData?.overall_status === "critical" ? "red"
    : "default";

  const recoStatusColor = (recoData?.confidence ?? 0) >= 70 ? "green"
    : (recoData?.confidence ?? 0) >= 40 ? "orange"
    : "red";

  return (
    <div>
      {/* AI Action Buttons */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col>
          <Button
            type="primary"
            danger
            icon={<AlertOutlined />}
            onClick={handleEarlyWarning}
          >
            目标预警
          </Button>
        </Col>
        <Col>
          <Space>
            <InputNumber
              placeholder="用户ID"
              min={1}
              value={recoUserId}
              onChange={(v) => setRecoUserId(v)}
              style={{ width: 120 }}
            />
            <Button
              type="primary"
              icon={<BulbOutlined />}
              onClick={handleRecommend}
            >
              目标推荐
            </Button>
          </Space>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card><Statistic title="总目标" value={data.total_target} precision={2} prefix="¥" loading={loading} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="已完成" value={data.total_actual} precision={2} prefix="¥" valueStyle={{ color: "#52c41a" }} loading={loading} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="整体完成率" value={data.overall_completion_rate} suffix="%" valueStyle={{ color: data.overall_completion_rate >= 100 ? "#52c41a" : "#faad14" }} loading={loading} /></Card>
        </Col>
      </Row>
      <Card title="目标 vs 实际" style={{ marginBottom: 24 }}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="目标" fill="#1890ff" />
            <Bar dataKey="实际" fill="#52c41a" />
          </BarChart>
        </ResponsiveContainer>
      </Card>
      <Card title="目标详情">
        <Table rowKey="id" columns={columns} dataSource={data.items} pagination={false} />
      </Card>

      {/* Early Warning Modal */}
      <Modal
        title={<><AlertOutlined /> 目标预警分析</>}
        open={warningOpen}
        onCancel={() => setWarningOpen(false)}
        width={900}
        footer={null}
        destroyOnClose
      >
        {warningLoading ? (
          <Spin size="large" style={{ display: "block", margin: "60px auto" }} />
        ) : warningData ? (
          <div>
            <Card style={{ marginBottom: 16 }}>
              <Row gutter={24}>
                <Col span={12}>
                  <Statistic
                    title="整体状态"
                    valueRender={() => (
                      <Tag color={overallStatusColor} style={{ fontSize: 16, padding: "4px 12px" }}>
                        {warningData.overall_status}
                      </Tag>
                    )}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="预测完成率"
                    value={warningData.forecast_attainment}
                    suffix="%"
                    valueStyle={{ color: warningData.forecast_attainment >= 100 ? "#52c41a" : "#ff4d4f" }}
                  />
                </Col>
              </Row>
            </Card>

            <Card title="风险目标" size="small" style={{ marginBottom: 16 }}>
              <Table
                rowKey="user_name"
                columns={riskColumns}
                dataSource={warningData.risk_targets}
                pagination={false}
                size="small"
              />
            </Card>

            <Card title="表现优秀" size="small" style={{ marginBottom: 16 }}>
              <Table
                rowKey="user_name"
                columns={topPerformerColumns}
                dataSource={warningData.top_performers}
                pagination={false}
                size="small"
              />
            </Card>

            <Row gutter={16}>
              <Col span={12}>
                <Card title="系统性问题" size="small">
                  <List
                    size="small"
                    dataSource={warningData.systemic_issues}
                    renderItem={(item: string) => (
                      <List.Item>
                        <Typography.Text type="danger">{item}</Typography.Text>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card title="改进建议" size="small">
                  <List
                    size="small"
                    dataSource={warningData.recommendations}
                    renderItem={(item: string) => (
                      <List.Item>
                        <Typography.Text type="success">{item}</Typography.Text>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
            </Row>
          </div>
        ) : (
          <Result status="warning" title="暂无预警数据" />
        )}
      </Modal>

      {/* Target Recommendation Modal */}
      <Modal
        title={<><BulbOutlined /> 目标推荐</>}
        open={recoOpen}
        onCancel={() => setRecoOpen(false)}
        width={800}
        footer={null}
        destroyOnClose
      >
        {recoLoading ? (
          <Spin size="large" style={{ display: "block", margin: "60px auto" }} />
        ) : recoData ? (
          <div>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="保守目标"
                    value={recoData.conservative_target}
                    precision={2}
                    prefix="¥"
                    valueStyle={{ color: "#1890ff" }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="推荐目标"
                    value={recoData.recommended_target}
                    precision={2}
                    prefix="¥"
                    valueStyle={{ color: "#52c41a" }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="挑战目标"
                    value={recoData.ambitious_target}
                    precision={2}
                    prefix="¥"
                    valueStyle={{ color: "#faad14" }}
                  />
                </Card>
              </Col>
            </Row>

            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="置信度"
                    value={recoData.confidence}
                    suffix="%"
                    valueStyle={{ color: recoStatusColor }}
                  />
                  <Progress
                    percent={recoData.confidence}
                    strokeColor={recoStatusColor}
                    size="small"
                    style={{ marginTop: 8 }}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="增长率"
                    value={recoData.growth_rate}
                    suffix="%"
                    valueStyle={{ color: recoData.growth_rate >= 0 ? "#52c41a" : "#ff4d4f" }}
                  />
                </Card>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Card title="关键驱动因素" size="small" style={{ marginBottom: 16 }}>
                  <List
                    size="small"
                    dataSource={recoData.key_drivers}
                    renderItem={(item: string) => (
                      <List.Item>
                        <Typography.Text type="success">{item}</Typography.Text>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card title="风险因素" size="small" style={{ marginBottom: 16 }}>
                  <List
                    size="small"
                    dataSource={recoData.risk_factors}
                    renderItem={(item: string) => (
                      <List.Item>
                        <Typography.Text type="warning">{item}</Typography.Text>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
            </Row>

            <Card title="策略建议" size="small">
              <List
                size="small"
                dataSource={recoData.strategy}
                renderItem={(item: string, index: number) => (
                  <List.Item>
                    <Typography.Text strong>{index + 1}. </Typography.Text>
                    {item}
                  </List.Item>
                )}
              />
            </Card>
          </div>
        ) : (
          <Result status="warning" title="暂无推荐数据" />
        )}
      </Modal>
    </div>
  );
}
